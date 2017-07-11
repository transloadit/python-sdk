from . import request
from . import assembly
from . import template


class Transloadit(object):
    """
    This class serves as a client interface to the Transloadit API.

    :Attributes:
        - auth_key (str): Transloadit auth key.
        - auth_secret (str): Transloadit auth secret.
        - service (Optional[str]): URL of the Transloadit API.
        - duration (int): How long in seconds for which a Transloadit request should be valid.
        - request (transloadit.request.Request): An instance of the Transloadit HTTP Request object.

    :Constructor Args:
        - auth_key (str): Transloadit auth key.
        - auth_secret (str): Transloadit aut secret.
        - service (Optional[str]):
            Url of the Transloadit API. Defaults to 'https://api2.transloadit.com'
            if not specified.
        - duration (Optional[int]):
            How long in seconds for which a Transloadit request should be valid. Defaults to 300
            if not specified.
    """
    def __init__(self, auth_key, auth_secret, service='https://api2.transloadit.com', duration=300):
        if not service.startswith(('http://', 'https://')):
            service = 'https://' + service

        self.service = service
        self.auth_key = auth_key
        self.auth_secret = auth_secret
        self.duration = duration
        self.request = request.Request(self)

    def new_assembly(self, params=None):
        """
        Return an instance of <transloadit.assembly.Assembly> which would be used to create
        a new assembly.
        """
        return assembly.Assembly(self, options=params)

    def get_assembly(self, assembly_id=None, assembly_url=None):
        """
        Get the assembly specified by the 'assembly_id' or the 'assembly_url'
        Either the assembly_id or the assembly_url must be specified

        :Args:
            - assembly_id (Optional[str])
            - assembly_url (Optional[str])
        
        Return an instance of <transloadit.response.Response>
        """
        if not (assembly_id or assembly_url):
            raise ValueError("Either 'assembly_id' or 'assembly_url' cannot be None.")

        url = assembly_url if assembly_url else '/assemblies/{}'.format(assembly_id)
        return self.request.get(url)

    def list_assemblies(self, params=None):
        """
        Get the list of assemblies.

        :Args:
            - options (Optional[dict]):
                params to send along with the request. Please see
                https://transloadit.com/docs/api-docs/#25-retrieve-assembly-list for available options.
        
        Return an instance of <transloadit.response.Response>
        """
        return self.request.get('/assemblies', params=params)

    def cancel_assembly(self, assembly_id=None, assembly_url=None):
        """
        Cancel the assembly specified by the 'assembly_id' or the 'assembly_url'
        Either the assembly_id or the assembly_url must be specified

        :Args:
            - assembly_id (Optional[str])
            - assembly_url (Optional[str])
        
        Return an instance of <transloadit.response.Response>
        """
        if not (assembly_id or assembly_url):
            raise ValueError("Either 'assembly_id' or 'assembly_url' cannot be None.")

        url = assembly_url if assembly_url else '/assemblies/{}'.format(assembly_id)
        return self.request.delete(url)

    def get_template(self, template_id):
        """
        Get the template specified by the 'template_id'.

        :Args:
            - template_id (str)
        
        Return an instance of <transloadit.response.Response>
        """
        return self.request.get('/templates/{}'.format(template_id))

    def list_templates(self, params=None):
        """
        Get the list of templates.

        :Args:
            - options (Optional[dict]):
                params to send along with the request. Please see
                https://transloadit.com/docs/api-docs/#45-retrieve-template-list for available options.
        
        Return an instance of <transloadit.response.Response>
        """
        return self.request.get('/templates', params=params)

    def new_template(self, name, params=None):
        """
        Return an instance of <transloadit.template.Template> which would be used to create
        a new template.

        :Args:
            - name (str): Name of the template.
        """
        return template.Template(self, name, options=params)

    def update_template(self, template_id, data):
        """
        Update the template specified by the 'template_id'.

        :Args:
            - template_id (str)
            - data (dict): key, value pair of fields and their new values.

        Return an instance of <transloadit.response.Response>
        """
        return self.request.put('/templates/{}'.format(template_id), data=data)

    def delete_template(self, template_id):
        """
        Delete the template specified by the 'template_id'.

        :Args:
            - template_id (str)

        Return an instance of <transloadit.response.Response>
        """
        return self.request.delete('/templates/{}'.format(template_id))

    def get_bill(self, month, year):
        """
        Get the bill for the specified month and year.

        :Args:
            - month (int): e.g 1 for January
            - year (int)
        
        Return an instance of <transloadit.response.Response>
        """
        return self.request.get('/bill/{}-{:02d}'.format(year, month))
