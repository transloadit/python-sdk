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
        super().__init__(options)
        self.transloadit = transloadit
        self.name = name

    def create(self):
        """
        Save/Submit the template to the Transloadit server.
        """
        data = self.get_options()
        steps = data.pop("steps")
        template = data.pop("template", None)
        template_content = dict(template) if isinstance(template, dict) else template or {}
        if steps:
            if not isinstance(template_content, dict):
                raise ValueError("template must be an object when steps are supplied.")
            template_content["steps"] = steps
        data.update({"name": self.name, "template": template_content})
        return self.transloadit.request.post("/templates", data=data)
