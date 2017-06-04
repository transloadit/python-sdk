from . import optionbuilder


class Template(optionbuilder.OptionBuilder):
    def __init__(self, client, name, options=None):
        super(Template, self).__init__(options)
        self.client = client
        self.name = name

    def save(self):
        data = self.get_options()
        data.update({'name': self.name})
        return self.client.request.post('/assemblies', data=data)
