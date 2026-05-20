import asyncio
import os

from tusclient import client as tus

from . import optionbuilder


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
            except (AttributeError, OSError, ValueError):
                continue

    def _do_tus_upload(self, assembly_url, tus_url, retries):
        tus_client = tus.TusClient(tus_url)
        for key, file_stream in self.files.items():
            filename = getattr(file_stream, "name", key)
            metadata = {
                "assembly_url": assembly_url,
                "fieldname": key,
                "filename": os.path.basename(filename) or key,
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
        if resumable:
            extra_data = {"tus_num_expected_upload_files": len(self.files)}
            response = await self.transloadit.request.post(
                "/assemblies", extra_data=extra_data, data=data
            )
            if self._rate_limit_reached(response) and retries:
                await asyncio.sleep(response.data.get("info", {}).get("retryIn", 1))
                self._rewind_files(file_positions)
                return await self.create(wait, resumable, retries - 1)
            await self._do_tus_upload_async(
                response.data.get("assembly_ssl_url"),
                response.data.get("tus_url"),
                retries,
            )
        else:
            response = await self.transloadit.request.post(
                "/assemblies", data=data, files=self.files
            )
            if self._rate_limit_reached(response) and retries:
                await asyncio.sleep(response.data.get("info", {}).get("retryIn", 1))
                self._rewind_files(file_positions)
                return await self.create(wait, resumable, retries - 1)

        if wait:
            assembly_url = response.data.get("assembly_ssl_url")
            while not self._assembly_finished(response):
                sleep_time = response.data.get("info", {}).get("retryIn", 1)
                await asyncio.sleep(sleep_time)
                response = await self.transloadit.get_assembly(
                    assembly_url=assembly_url or response.data.get("assembly_ssl_url")
                )
                assembly_url = response.data.get("assembly_ssl_url") or assembly_url

        if self._rate_limit_reached(response) and retries:
            await asyncio.sleep(response.data.get("info", {}).get("retryIn", 1))
            self._rewind_files(file_positions)
            return await self.create(wait, resumable, retries - 1)

        return response

    def _assembly_finished(self, response):
        status = response.data.get("ok")
        is_aborted = status == "REQUEST_ABORTED"
        is_canceled = status == "ASSEMBLY_CANCELED"
        is_completed = status == "ASSEMBLY_COMPLETED"
        error = response.data.get("error")
        is_failed = error is not None
        is_fetch_rate_limit = error == "ASSEMBLY_STATUS_FETCHING_RATE_LIMIT_REACHED"
        return is_aborted or is_canceled or is_completed or (is_failed and not is_fetch_rate_limit)

    def _rate_limit_reached(self, response):
        return response.data.get("error") == "RATE_LIMIT_REACHED"
