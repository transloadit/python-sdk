import asyncio

from tusclient import client as tus

from . import optionbuilder
from .async_request import _get_upload_filename


class AsyncAssembly(optionbuilder.OptionBuilder):
    """
    Object representation of a new Assembly to be created asynchronously.
    """

    def __init__(self, transloadit, files=None, options=None):
        super().__init__(options)
        self.transloadit = transloadit
        self.files = files or {}

    def add_file(self, file_stream, field_name=None):
        """
        Add a file to be uploaded along with the Assembly.
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
        """
        self.files.pop(field_name)

    def _snapshot_file_positions(self):
        positions = {}
        for key, file_stream in self.files.items():
            try:
                positions[key] = file_stream.tell()
            except (AttributeError, OSError, ValueError):
                continue
        return positions

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
            filename = _get_upload_filename(file_stream, key)
            metadata = {
                "assembly_url": assembly_url,
                "fieldname": key,
                "filename": filename,
            }
            tus_client.uploader(
                file_stream=file_stream,
                chunk_size=5 * 1024 * 1024,
                metadata=metadata,
                retries=retries,
            ).upload()

    async def _do_tus_upload_async(self, assembly_url, tus_url, retries):
        await asyncio.to_thread(self._do_tus_upload, assembly_url, tus_url, retries)

    async def create(self, wait=False, resumable=True, retries=3):
        """
        Save/Submit the assembly for processing.
        """
        data = self.get_options()
        file_positions = self._snapshot_file_positions()
        tus_retries = retries
        poll_retries = retries

        while True:
            if resumable:
                extra_data = {"tus_num_expected_upload_files": len(self.files)} if self.files else None
                response = await self.transloadit.request.post(
                    "/assemblies", extra_data=extra_data, data=data
                )
            else:
                response = await self.transloadit.request.post(
                    "/assemblies", data=data, files=self.files
                )

            response_data = self._response_data(response)
            if response_data is None:
                return response

            if self._rate_limit_reached(response_data):
                if retries:
                    await asyncio.sleep(response_data.get("info", {}).get("retryIn", 1))
                    if not resumable:
                        self._rewind_files(file_positions)
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
                    return response
                await self._do_tus_upload_async(assembly_url, tus_url, tus_retries)

            if wait:
                if not assembly_url:
                    return response

                poll_response = response
                poll_data = response_data
                remaining_polls = poll_retries
                while not self._assembly_finished(poll_data):
                    if remaining_polls <= 0:
                        return poll_response
                    sleep_time = poll_data.get("info", {}).get("retryIn", 1)
                    await asyncio.sleep(sleep_time)
                    poll_response = await self.transloadit.get_assembly(
                        assembly_url=assembly_url or poll_data.get("assembly_ssl_url")
                    )
                    poll_data = self._response_data(poll_response)
                    if poll_data is None:
                        return poll_response
                    assembly_url = poll_data.get("assembly_ssl_url") or assembly_url
                    remaining_polls -= 1

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
        return is_aborted or is_canceled or is_completed or (is_failed and not (is_fetch_rate_limit or is_submit_rate_limit))

    def _rate_limit_reached(self, response_data):
        return response_data.get("error") == "RATE_LIMIT_REACHED"
