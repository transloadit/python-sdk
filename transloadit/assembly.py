import os
from time import sleep

from tusclient import client as tus

from . import optionbuilder


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
        super(Assembly, self).__init__(options)
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

    def _do_tus_upload(self, assembly_url, tus_url, retries):
        tus_client = tus.TusClient(tus_url)
        metadata = {'assembly_url': assembly_url}
        for key in self.files:
            metadata['fieldname'] = key
            metadata['filename'] = os.path.basename(self.files[key].name)
            tus_client.uploader(file_stream=self.files[key],
                                metadata=metadata,
                                retries=retries).upload()

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
        if resumable:
            extra_data = {'tus_num_expected_upload_files': len(self.files)}
            response = self.transloadit.request.post(
                '/assemblies', extra_data=extra_data, data=data)
            self._do_tus_upload(response.data.get('assembly_ssl_url'),
                                response.data.get('tus_url'),
                                retries)
        else:
            response = self.transloadit.request.post(
                '/assemblies', data=data, files=self.files)

        if wait:
            while not self._assembly_finished(response):
                response = self.transloadit.get_assembly(
                    assembly_url=response.data.get('assembly_ssl_url'))

        if self._rate_limit_reached(response) and retries:
            # wait till rate limit is expired
            sleep(response.data.get('info', {}).get('retryIn', 0))
            self.create(wait, resumable, retries - 1)

        return response

    def _assembly_finished(self, response):
        status = response.data.get('ok')
        is_aborted = status == 'REQUEST_ABORTED'
        is_canceled = status == 'ASSEMBLY_CANCELED'
        is_completed = status == 'ASSEMBLY_COMPLETED'
        is_failed = response.data.get('error') is not None
        return is_aborted or is_canceled or is_completed or is_failed

    def _rate_limit_reached(self, response):
        return response.data.get('error') == 'RATE_LIMIT_REACHED'
