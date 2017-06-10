from . import request
from . import assembly
from . import template


class Transloadit(object):
    """
    This class serves as a client interface to the Transloadit API.

    :Attributes:
        - key (str): Transloadit auth key.
        - secret (str): Transloadit auth secret.
        - host (Optional[str]): Host URL of the Transloadit API.
        - duration (int): How long in seconds for which a Transloadit should be valid.
        - request (transloadit.request.Request): An instance of the Transloadit HTTP Request object.

    :Constructor Args:
        - key (str): Transloadit auth key.
        - secret (str): Transloadit aut secret.
        - host (Optional[str]):
            Host url of the Transloadit API. Defaults to 'https://api2.transloadit.com'
            if not specified.
        - duration (Optional[int]):
            How long in seconds for which a Transloadit should be valid. Defaults to 300
            if not specified.
    """
    def __init__(self, key, secret, host='https://api2.transloadit.com', duration=300):
        self.key = key
        self.secret = secret
        self.host = host
        self.duration = duration
        self.request = request.Request(self)

    def new_assembly(self, params=None):
        return assembly.Assembly(self, options=params)

    def get_assembly(self, assembly_id=None, url=None, params=None):
        if not (assembly_id or url):
            raise ValueError("Either 'assembly_id' or 'url' cannot be None.")

        url = url if url else '/assemblies/{}'.format(assembly_id)
        return self.request.get(url, params=params)

    def list_assemblies(self, params=None):
        return self.request.get('/assemblies', params=params)

    def cancel_assembly(self, assembly_id=None, url=None, data=None):
        if not (assembly_id or url):
            raise ValueError("Either 'assembly_id' or 'url' cannot be None.")

        url = url if url else '/assemblies/{}'.format(assembly_id)
        return self.request.delete(url, data=data)

    def get_template(self, template_id, params=None):
        return self.request.get('/templates/{}'.format(template_id), params=params)

    def list_templates(self, params=None):
        return self.request.get('/templates', params=params)

    def new_template(self, name, params=None):
        return template.Template(self, name, options=params)

    def update_template(self, template_id, data):
        return self.request.put('/templates/{}'.format(template_id), data=data)

    def delete_tempalte(self, template_id):
        return self.request.delete('/templates/{}'.format(template_id))

    def get_bill(self, month, year, params=None):
        return self.request.get('/bill/{}-{}'.format(year, month), params=params)
