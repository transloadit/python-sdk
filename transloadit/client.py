from transloadit import request
from transloadit import assembly


class Client(object):
    def __init__(self, key, secret, host='https://api2.transloadit.com', duration=300):
        self.key = key
        self.secret = secret
        self.host = host
        self.duration = duration
        self.request = request.Request(self)

    def new_assembly(self, params=None):
        return assembly.Assembly(self, options=params)

    def get_assembly(self, id=None, url=None, params=None):
        if id is None and url is None:
            pass # throw error here

        url = url if url else '/assemblies/{}'.format(id)
        return self.request.get(url, params=params)

    def list_assemblies(self, params=None):
        return self.request.get('/assemblies', params=params)

    def cancel_assembly(self, id=None, url=None, data=None):
        if id is None and url is None:
            pass # throw error here

        url = url if url else '/assemblies/{}'.format(id)
        return self.request.delete(url, data=data)

    def get_template(self, id, params=None):
        return self.request.get('/templates/{}'.format(id), params=params)

    def list_templates(self, params=None):
        return self.request.get('/templates', params=params)

    def new_template(self, params=None):
        return assembly.Assembly(self, options=params)

    def update_template(self, id, data):
        return self.request.put('/templates/{}'.format(id), data=data)

    def delete_tempalte(self, id):
        return self.request.delete('/templates/{}'.format(id))

    def get_bill(self, day, year, params=None):
        return self.request.get('/bill/{}-{}'.format(day, year), params=params)
