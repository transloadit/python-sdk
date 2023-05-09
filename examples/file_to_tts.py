### A simple Transloadit Assembly that converts a .doc file to a .txt file. It then generates a .mp3 based on the .txt file using a text-to-speech Robot.

'''
Template:

{
  "steps": {
    ":original": {
      "robot": "/upload/handle"
    },
    "convert": {
      "use": ":original",
      "robot": "/document/convert",
      "format": "txt"
    },
    "speech": {
      "use": "convert",
      "robot": "/text/speak",
      "result": true,
      "provider": "gcp",
      "target_language": "en-US",
      "voice": "female-1"
    }
  }
}
'''

from transloadit import client

tl = client.Transloadit('TRANSLOADIT_KEY', 'TRANSLOADIT_SECRET')

def useTemplate(templateID, file_path='', result_name='', get_url=True, fields=''):
    assembly = tl.new_assembly({'template_id': templateID, 'fields': fields})

    if file_path != '':
        assembly.add_file(open(file_path, 'rb'))

    assembly_response = assembly.create(retries=5, wait=True)
    if get_url:
        assembly_url = assembly_response.data.get('results').get(result_name)[0].get('ssl_url')
        print(assembly_url)
        return assembly_url
    
useTemplate ('TEMPLATE_ID', file_path='fixtures/document.doc', result_name='speech', get_url=True)