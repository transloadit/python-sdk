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
        - name (str)
        - options (Optional[dict])
    """
    def __init__(self, transloadit, name, options=None):
        super(Template, self).__init__(options)
        self.transloadit = transloadit
        self.name = name

    def save(self):
        """
        Save/Submit the template to the Transloadit server.
        """
        data = self.get_options()
        data.update({'name': self.name})
        return self.transloadit.request.post('/templates', data=data)
