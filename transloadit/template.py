from . import optionbuilder


class Template(optionbuilder.OptionBuilder):
    """
    Object representation of a new Template to be created.

    :Attributes:
        - transloadit (<translaodit.client.Transloadit>):
            An instance of the Transloadit class.
        - name (str):
            The name of the template to be created.

    :Constructor Args:
        - transloadit (<translaodit.client.Transloadit>)
        - name (str): The name of the template.
        - options (Optional[dict]):
            Params to send along with the template. Please see
            https://transloadit.com/docs/api-docs/#4-templates for available options.
    """
    def __init__(self, transloadit, name, options=None):
        super(Template, self).__init__(options)
        self.transloadit = transloadit
        self.name = name

    def create(self):
        """
        Save/Submit the template to the Transloadit server.
        """
        data = self.get_options()
        data.update({'name': self.name})
        return self.transloadit.request.post('/templates', data=data)
