### A Transloadit Assembly that adds a translated TTS-voice (english to dutch) to an input video of hermit crabs.

'''
Template 1:

{
  "steps": {
    "transcribe_json": {
      "use": ":original",
      "robot": "/speech/transcribe",
      "provider": "aws",
      "source_language": "${fields.language}",
      "format": "json",
      "result": true
    }
  }
}
'''

'''
Template 2:

{
  "steps": {
    ":original": {
      "robot": "/upload/handle"
    },
    "import_video": {
      "robot": "/http/import",
      "url": "${fields.video}"
    },
    "translate": {
      "use": ":original",
      "robot": "/text/translate",
      "provider": "gcp",
      "target_language": "${fields.target_language}",
      "source_language": "${fields.source_language}",
      "result": true
    },
    "speech": {
      "use": "translate",
      "robot": "/text/speak",
      "provider": "gcp",
      "target_language": "${fields.target_language}",
      "voice": "female-1",
      "ssml": true,
      "result": true
    },
    "extract_audio": {
      "use": "import_video",
      "robot": "/video/encode",
      "result": true,
      "preset": "mp3",
      "ffmpeg": {
        "af": "${fields.ffmpeg}"
      },
      "ffmpeg_stack": "v3.3.3"
    },
    "merged_audio": {
      "robot": "/audio/merge",
      "preset": "mp3",
      "result": "true",
      "ffmpeg_stack": "v4.3.1",
      "use": {
        "steps": [
          {
            "name": "extract_audio",
            "as": "audio"
          },
          {
            "name": "speech",
            "as": "audio"
          }
        ],
        "volume": "sum",
        "bundle_steps": true
      }
    },
    "merged_video": {
      "robot": "/video/merge",
      "preset": "hls-720p",
      "ffmpeg_stack": "v4.3.1",
      "use": {
        "steps": [
          {
            "name": "merged_audio",
            "as": "audio"
          },
          {
            "name": "import_video",
            "as": "video"
          }
        ],
        "bundle_steps": true
      }
    }
  }
}
'''

from transloadit import client
import urllib.request
import json

tl = client.Transloadit('TRANSLOADIT_KEY', 'TRANSLOADIT_SECRET')

source_language = 'en-GB'
target_language = 'nl-NL'

def useTemplate(templateID, file_path='', result_name='', get_url=True, fields=''):
    assembly = tl.new_assembly({'template_id': templateID, 'fields': fields})

    if file_path != '':
        assembly.add_file(open(file_path, 'rb'))

    assembly_response = assembly.create(retries=5, wait=True)
    if get_url:
        result_url = assembly_response.data.get('results').get(result_name)[0].get('ssl_url')
        print(result_url)
        return result_url
    else:
        return assembly_response
    
response = useTemplate ('TEMPLATE_1_ID', file_path='medium_crab.mp4', get_url=False, fields={"language":source_language})
transcription_result_url = response.data.get('results').get('transcribe_json')[0].get('ssl_url')
video_url = response.data.get('uploads')[0].get('ssl_url')

urllib.request.urlretrieve(transcription_result_url, 'transcribe_json')

with open('transcribe_json') as f:
    data = json.load(f)

ffmpeg = "volume=enable:volume=1"

startTimes = []
endTimes = []
sentences = []
currentSentence = ''

startTimes.append(data['words'][0]['startTime'])

for x in range(len(data['words'])):  
    if (data['words'][x]['text'] == '.') and (x != len(data['words']) - 1):
        time = data['words'][x+1]['startTime']
        startTimes.append(time)
    if (data['words'][x]['text'] != '.'):
        currentSentence = currentSentence + ' ' + data['words'][x]['text']
    else:
        sentences.append(currentSentence + '.')
        time = data['words'][x-1]['endTime']
        endTimes.append(time)
        currentSentence = ''
        
print('startTimes: ' + str(startTimes))
print('endTimes: ' + str(startTimes))
print(sentences)

f = open("words/text.txt", "w")
f.write("<speak><par>")

for x in range(len(sentences)):
    f.write('<media begin="{start}"><speak>{text}</speak></media>'.format(start=startTimes[x], text=sentences[x]))
    ffmpeg += ", volume=enable='between(t,{start},{end})':volume=0.2".format(start=startTimes[x], end=endTimes[x])

f.write("</par></speak>")
f.close()

final_result_url = useTemplate ('TEMPLATE_2_ID', file_path='words/text.txt', result_name='merged_video', get_url=True, fields={"target_language":target_language, "source_language":source_language, "video":video_url, "ffmpeg":ffmpeg})