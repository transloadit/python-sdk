# transloadit-python-sdk
Python integration for Transloadit

## Usage

```python
from transloadit import client

tl = client.Transloadit('KEY', 'SECRET')
assembly = tl.new_assembly()
assembly.add_file(open('lol_cat.jpg', 'rb'))
assembly.add_step('resize', '/image/resize', {'width': 70, 'height': 70})
assembly_response = assembly.save(retries=5, wait=True)

print assembly_response.data.get('assembly_id')

# or
print assembly_response.data['assembly_id']
```