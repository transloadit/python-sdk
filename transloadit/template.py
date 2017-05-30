from transloadit import optionbuilder


class Template(optionbuilder.OptionBuilder):
    def __init__(self, client, options=None):
        super(Template, self).__init__()
        self.client = client

    def save(self):
        return self.client.request.post('/assemblies', data=self.get_options())
