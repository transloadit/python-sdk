import copy
import os

from tusclient import client as tus

from . import optionbuilder


class Assembly(optionbuilder.OptionBuilder):
    def __init__(self, transloadit, options=None):
        super(Assembly, self).__init__(options)
        self.transloadit = transloadit
        self.files = {}

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
        name = 'file'
        if name not in self.files:
            return name

        counter = 1
        while '{}_{}'.format(name, counter) in self.files:
            counter += 1
        return '{}_{}'.format(name, counter)

    def remove_file(self, field_name):
        """
        Remove the file with the specified field name from the set of files to be submitted.

        :Args:
            - field_name (str): The field name assigned to the file when it was added.
        """
        self.files.pop(field_name)

    def _do_tus_upload(self, assembly_url, tus_url):
        tus_client = tus.TusClient(tus_url)
        metadata = {'assembly_url': assembly_url}
        for key in self.files:
            metadata['fieldname'] = key
            metadata['filename'] = os.path.basename(self.files[key].name)
            tus_client.uploader(
                file_stream=self.files[key], metadata=metadata).upload()

    def save(self, resumable=True, wait=False):
        """
        Save/Submit the assembly for processing.

        :Args:
            - resumable (Optional[bool]): A flag indicating if the upload should be resumable.
                This is good for cases of network failures. Defaults to True if not specified.
            - wait (Optional[bool]): If set to True, the method will wait till the assembly
                processing is complete before returning a response.
        """
        data = self.get_options()
        if resumable:
            extra_data = {'tus_num_expected_upload_files': len(self.files)}
            response = self.transloadit.request.post(
                '/assemblies', extra_data=extra_data, data=data)
            self._do_tus_upload(response.data.get(
                'assembly_ssl_url'), response.data.get('tus_url'))
        else:
            response = self.transloadit.request.post(
                '/assemblies', data=data, files=self.files)

        if wait:
            while not self._assembly_finished(response):
                response = self.transloadit.get_assembly(
                    url=response.data.get('assembly_ssl_url'))
        return response

    def _assembly_finished(self, response):
        status = response.data.get('ok')
        is_aborted = status == 'REQUEST_ABORTED'
        is_canceled = status == 'ASSEMBLY_CANCELED'
        is_completed = status == 'ASSEMBLY_COMPLETED'
        return is_aborted or is_canceled or is_completed
