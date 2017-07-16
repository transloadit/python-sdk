from __future__ import print_function

from transloadit.client import Transloadit

tl = Transloadit('TRANSLOADIT_KEY', 'TRANSLOADIT_SECRET')
ass = tl.new_assembly()
ass.add_file(open('fixtures/lol_cat.jpg', 'rb'))
ass.add_step('resize', '/image/resize', {'width': 70, 'height': 70})
response = ass.create(wait=True)

result_url = response.data.get('results').get('resize')[0].get('ssl_url')
print('Your result:', result_url)
