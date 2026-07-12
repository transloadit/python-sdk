from . import optionbuilder


class AsyncTemplate(optionbuilder.OptionBuilder):
    """
    Object representation of a new Template to be created asynchronously.
    """

    def __init__(self, transloadit, name, options=None):
        super().__init__(options)
        self.transloadit = transloadit
        self.name = name

    async def create(self):
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
        return await self.transloadit.request.post("/templates", data=data)
