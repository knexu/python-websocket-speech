# Python Speech-to-Text Client use websocket API

Python client library for the cloud-based Speech API to transcribe a spoken utterance to text. The asynchronous communication with the service uses the WebSocket protocol enabling real-time and stream speech recognition.

## Prerequisites

The client is implemented in Python 3, and it requires the following packages to be installed before use:

- websocket-client
- pyaudio
- threading

# get key 
# Replace the subscriptionKey string value with your valid subscription key.
Only api_key_asia used in the application
BING_KEY = 'you bing speech key'
api_key = 'you azure west US key'
api_key_asia = 'your azure asia key'
## How to Use It

python websocketSpeechRealTime.py

use new unify speech websocket interface, implement realtime stream.
Stream formate use WAVE header and PCM encode.

