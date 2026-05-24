import math
from time import sleep

from tusclient import client as tus

from . import optionbuilder
from .upload import get_upload_filename


class Assembly(optionbuilder.OptionBuilder):
    """
    Object representation of a new Assembly to be created.

    :Attributes:
        - transloadit (<transloadit.client.Transloadit>):
            An instance of the Transloadit class.
        - files (dict):
            Storage of files to be uploaded. Each file is stored with a key corresponding
            to its field name when it is being uploaded.

    :Constructor Args:
        - transloadit (<transloadit.client.Transloadit>)
        - files (Optional[dict]):
            Key, value pair of the file's field name and the file stream respectively.
        - options (Optional[dict]):
            Params to send along with the assembly. Please see
            https://transloadit.com/docs/api-docs/#21-create-a-new-assembly for available options.
    """

    def __init__(self, transloadit, files=None, options=None):
        super().__init__(options)
        self.transloadit = transloadit
        self.files = files or {}

    def add_file(self, file_stream, field_name=None):
        """
        Add a file to be uploaded along with the Assembly.

        :Args:
            - file_stream (file): File stream object of the file to upload.
            - field_name (Optional[str]): The field name assigned to the file.
                If not specified, a field name is auto-generated.
        """
        if field_name is None:
            field_name = self._get_field_name()

        self.files[field_name] = file_stream

    def _get_field_name(self):
        name = "file"
        if name not in self.files:
            return name

        counter = 1
        while f"{name}_{counter}" in self.files:
            counter += 1
        return f"{name}_{counter}"

    def remove_file(self, field_name):
        """
        Remove the file with the specified field name from the set of files to be submitted.

        :Args:
            - field_name (str): The field name assigned to the file when it was added.
        """
        self.files.pop(field_name)

    def _snapshot_file_positions(self):
        positions = {}
        missing = []
        for key, file_stream in self.files.items():
            try:
                positions[key] = file_stream.tell()
            except (AttributeError, OSError, ValueError):
                missing.append(key)
        return positions, missing

    def _rewind_files(self, positions):
        for key, position in positions.items():
            file_stream = self.files.get(key)
            if file_stream is None:
                continue
            try:
                file_stream.seek(position)
            except (AttributeError, OSError, ValueError) as exc:
                raise RuntimeError(f"Unable to rewind file stream {key!r}.") from exc

    def _do_tus_upload(self, assembly_url, tus_url, retries):
        tus_client = tus.TusClient(tus_url)
        for key, file_stream in self.files.items():
            metadata = {
                "assembly_url": assembly_url,
                "fieldname": key,
                "filename": get_upload_filename(file_stream, key),
            }
            tus_client.uploader(
                file_stream=file_stream,
                chunk_size=5 * 1024 * 1024,
                metadata=metadata,
                retries=retries,
            ).upload()

    def create(self, wait=False, resumable=True, retries=3):
        """
        Save/Submit the assembly for processing.

        :Args:
            - wait (Optional[bool]): If set to True, the method will wait till the assembly
                processing is complete before returning a response.
            - resumable (Optional[bool]): A flag indicating if the upload should be resumable.
                This is good for cases of network failures. Defaults to True if not specified.
            - retries (Optional[int]): In the event of an upload failure, this specifies how many
                more times the upload should be retried before crying for help. This option is only
                available if 'resumable' is set to 'True'. Defaults to 3 if not specified.
        """
        data = self.get_options()
        file_positions, missing_file_positions = self._snapshot_file_positions()
        tus_retries = retries
        poll_retries = retries

        while True:
            if resumable:
                extra_data = {"tus_num_expected_upload_files": len(self.files)}
                response = self.transloadit.request.post(
                    "/assemblies", extra_data=extra_data, data=data
                )
            else:
                response = self.transloadit.request.post(
                    "/assemblies", data=data, files=self.files
                )

            response_data = self._response_data(response)
            if response_data is None:
                if response.status_code >= 400 or wait or (resumable and self.files):
                    raise RuntimeError(f"Unexpected non-JSON response ({response.status_code}).")
                return response

            if self._rate_limit_reached(response_data):
                if retries:
                    if not resumable and missing_file_positions:
                        missing = ", ".join(repr(key) for key in missing_file_positions)
                        raise RuntimeError(
                            "Cannot retry non-resumable upload because these file streams are not seekable: "
                            f"{missing}"
                        )
                    if not resumable:
                        self._rewind_files(file_positions)
                    sleep(self._retry_delay(response_data))
                    retries -= 1
                    continue
                return response

            error = response_data.get("error")
            assembly_url = response_data.get("assembly_ssl_url")
            tus_url = response_data.get("tus_url")

            if error is not None:
                return response

            if resumable and self.files:
                if not assembly_url or not tus_url:
                    raise RuntimeError(
                        f"Resumable assembly response is missing upload URLs: {response_data!r}"
                    )
                self._do_tus_upload(assembly_url, tus_url, tus_retries)

            if wait:
                if not assembly_url:
                    return response

                poll_response = response
                poll_data = response_data
                remaining_rate_limit_retries = poll_retries
                while not self._assembly_finished(poll_data):
                    if self._rate_limit_reached(poll_data):
                        if remaining_rate_limit_retries <= 0:
                            return poll_response
                        remaining_rate_limit_retries -= 1
                    else:
                        remaining_rate_limit_retries = poll_retries
                    sleep(self._retry_delay(poll_data))
                    poll_response = self.transloadit.get_assembly(assembly_url=assembly_url)
                    poll_data = self._response_data(poll_response)
                    if poll_data is None:
                        raise RuntimeError(
                            f"Unexpected non-JSON response ({poll_response.status_code})."
                        )

                return poll_response

            return response

    def _response_data(self, response):
        data = response.data
        return data if isinstance(data, dict) else None

    def _assembly_finished(self, response_data):
        status = response_data.get("ok")
        is_aborted = status == "REQUEST_ABORTED"
        is_canceled = status == "ASSEMBLY_CANCELED"
        is_completed = status == "ASSEMBLY_COMPLETED"
        error = response_data.get("error")
        is_failed = error is not None
        is_fetch_rate_limit = error == "ASSEMBLY_STATUS_FETCHING_RATE_LIMIT_REACHED"
        is_submit_rate_limit = error == "RATE_LIMIT_REACHED"
        return (
            is_aborted
            or is_canceled
            or is_completed
            or (is_failed and not (is_fetch_rate_limit or is_submit_rate_limit))
        )

    def _rate_limit_reached(self, response_data):
        error = response_data.get("error")
        return isinstance(error, str) and error in {
            "RATE_LIMIT_REACHED",
            "ASSEMBLY_STATUS_FETCHING_RATE_LIMIT_REACHED",
        }

    def _retry_delay(self, response_data):
        info = response_data.get("info")
        if not isinstance(info, dict):
            return 1
        try:
            delay = float(info.get("retryIn", 1))
        except (TypeError, ValueError):
            return 1
        if not math.isfinite(delay):
            return 1
        return max(delay, 0)
