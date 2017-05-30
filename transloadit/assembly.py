import copy

from tusclient import client as tus

from transloadit import optionbuilder


class Assembly(optionbuilder.OptionBuilder):
    def __init__(self, client, options=None):
        super(Assembly, self).__init__()
        self.client = client
        self.files = {}

    def add_file(self, fs, name=None):
        self.files[name] = fs

    def remove_file(self, name):
        self.files.pop(name)

    def _do_tus_upload(self, url):
        tus_client = tus.TusClient(self.client.host + '/resumable/files/')
        for key in self.files:
            tus_client.uploader(self.files[key]).upload()

    def save(self, use_tus=True, wait=False):
        data = self.get_options()
        if use_tus:
            data['tus_num_expected_upload_files'] = len(self.files)
            response = self.client.request('/assemblies', data=data)
            self._do_tus_upload(response.url)
        else:
            response = self.client.request.post('/assemblies', data=data, files=self.files)
        return response
