# -*- coding: utf-8 -*-

# To install this package, run:
#   pip install websocket-client
# Support unify speech services
import websocket
import wave
from pyaudio import PyAudio,paInt16
import threading
import time
import json
import argparse
import requests
import utils
import numpy as np 
import struct

import platform


startTime = time.time()
endTime = startTime
sendTime = startTime

# **********************************************
# *** Update or verify the following values. ***
# **********************************************

# Replace the subscriptionKey string value with your valid subscription key.
BING_KEY = '7c28d953d7c74e9f826cad89a492fbe8'
api_key = '26849cac57244c70aa3342b8c0cf6e52'
api_key_asia = '62b94f594bdd4680b3c4649611975d33'

# Token请求地址
AUTH_URL = 'https://westus.api.cognitive.microsoft.com/sts/v1.0/issueToken'
ASIA_AUTH_URL = 'https://eastasia.api.cognitive.microsoft.com/sts/v1.0/issuetoken'
BING_AUTH_URL = 'https://api.cognitive.microsoft.com/sts/v1.0/issueToken'

#end point
#host = 'wss://speech.platform.bing.com'
api_host = 'wss://westus.stt.speech.microsoft.com'
bing_host = 'wss://speech.platform.bing.com'
asia_host = 'wss://eastasia.stt.speech.microsoft.com'
rest_host = 'https://westus.stt.speech.microsoft.com'
#conversation 适合做交互回话
#interactive 适合实现Rest API，单次应答
path = '/speech/recognition/conversation/cognitiveservices/v1'
params = '?language=zh-CN'

#bing URL
#url = bing_host+path+params
#key = BING_KEY
#auth_url = BING_AUTH_URL

#asia URL
url = asia_host+path+params
key = api_key_asia
auth_url = ASIA_AUTH_URL

#uri = host + path + params

# UUID
connection_id = utils.generate_id()
request_id = utils.generate_id()

TIME= 20  #控制录音时间
#chunk_size=8192
chunk_size=2048

framerate=16000         #取样频率
NUM_SAMPLES = chunk_size      #pyaudio内置缓冲大小
LEVEL = 100         #声音保存的阈值

channels=1
sampwidth=2
INPUT_DEVICE_INDEX = 1



debug = False
def log(str):
    if debug :
        print(str)

def send_speech_config_msg(client):
    # assemble the payload for the speech.config message
    context = {
        'system': {
            'version': '5.4'
        },
        'os': {
            'platform': platform.system(),
            'name': platform.system() + ' ' + platform.version(),
            'version': platform.version()
        },
        'device': {
            'manufacturer': 'SpeechSample',
            'model': 'SpeechSample',
            'version': '1.0.00000'
        }
    }
    payload = {'context': context}

    # assemble the header for the speech.config message
    msg = 'Path: speech.config\r\n'
    msg += 'Content-Type: application/json; charset=utf-8\r\n'
    msg += 'X-Timestamp: ' + utils.generate_timestamp() + '\r\n'
    # append the body of the message
    msg += '\r\n' + json.dumps(payload, indent=2)

    # DEBUG PRINT
    # print('>>', msg)

    client.send(msg,websocket.ABNF.OPCODE_TEXT)

def build_chunk(audio_chunk):
    # assemble the header for the binary audio message
    msg = b'Path: audio\r\n'
    msg += b'Content-Type: audio/x-wav\r\n'
    msg += b'X-RequestId: ' + bytearray(request_id, 'ascii') + b'\r\n'
    msg += b'X-Timestamp: ' + bytearray(utils.generate_timestamp(), 'ascii') + b'\r\n'
    # prepend the length of the header in 2-byte big-endian format
    msg = len(msg).to_bytes(2, byteorder='big') + msg
    # append the body of the message
    msg += b'\r\n' + audio_chunk
    return msg

def send_audio_stream(client,buf):
    msg = build_chunk(buf)
    client.send(msg,websocket.ABNF.OPCODE_BINARY)

def send_audio_msg(client,audio_file_path):
    # open the binary audio file
    with open(audio_file_path, 'rb') as f_audio:
        num_chunks = 0
        while True:
            # read the audio file in small consecutive chunks
            audio_chunk = f_audio.read(chunk_size)
            #audio_chunk = f_audio.read()
            if not audio_chunk:
                break
            num_chunks += 1

            # assemble the header for the binary audio message
            msg = build_chunk(audio_chunk)

            client.send(msg,websocket.ABNF.OPCODE_BINARY)
            #print(num_chunks,end=' ')
            #slow down send speed, 模拟实时音频 sleep 0.02
            time.sleep(0.015)



def get_wave_header(frame_rate):
    """
    Generate WAV header that precedes actual audio data sent to the speech translation service.
    :param frame_rate: Sampling frequency (8000 for 8kHz or 16000 for 16kHz).
    :return: binary string
    """

    if frame_rate not in [8000, 16000]:

        raise ValueError("Sampling frequency, frame_rate, should be 8000 or 16000.")

    nchannels = channels
    bytes_per_sample = sampwidth

    data = b'RIFF'
    data += struct.pack('<L', 0)
    data += b'WAVE'
    data += b'fmt '
    data += struct.pack('<L', 16)
    data += struct.pack('<H', 0x0001)
    data += struct.pack('<H', nchannels)
    data += struct.pack('<L', frame_rate)
    data += struct.pack('<L', frame_rate * nchannels * bytes_per_sample)
    data += struct.pack('<H', nchannels * bytes_per_sample)
    data += struct.pack('<H', bytes_per_sample * 8)
    #data += struct.pack('<H', 0)
    data += b'data'
    data += struct.pack('<L', 0)

    return data


def on_open (client):
    global startTime
    global sendTime
    endTime = time.time()
    print ("Connected. time",endTime - startTime)
    send_speech_config_msg(client)
    endTime = time.time()
    print ("Config msg sended. time",endTime - startTime)

    # send audio thread
    startTime = time.time()


    def sendThread():

        #inintial microphone
        pa = PyAudio() 
        '''
        #microphone choice
        info = pa.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        for i in range(0, numdevices):
            if (pa.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                print( "Input Device id ", i, " - ", pa.get_device_info_by_host_api_device_index(0, i).get('name'))
        '''
        stream = pa.open(format=paInt16, channels=1, rate=framerate, input=True, 
            frames_per_buffer=NUM_SAMPLES,input_device_index= INPUT_DEVICE_INDEX) 

        # Stream audio one chunk at a time
        data = get_wave_header(framerate)
        send_audio_stream(client,data)

        print("try to recognition...")
        count = 0
        #while count<TIME:#控制录音时间
        while True:
            '''
            # 读入NUM_SAMPLES个取样
            string_audio_data = stream.read(NUM_SAMPLES) 
            # 将读入的数据转换为数组
            audio_data = np.fromstring(string_audio_data, dtype=np.short)
            # 计算大于LEVEL的取样的个数
            large_sample_count = np.sum( audio_data > LEVEL )
            print(np.max(audio_data))

            send_audio_stream(client,np.array(audio_data).tostring())
            '''  
            print('.',end='')
            audio_data = stream.read(NUM_SAMPLES)
            send_audio_stream(client, audio_data)

            #print ("Sending silence.")
            #Audio source generating silence matching WAV 16bit PCM 16kHz - 320 bytes / 10ms
            #client.send (bytearray (64000), websocket.ABNF.OPCODE_BINARY)
            count+=1

        sendTime = time.time()
        client.close()
        print('Audio file sended. Send Time:',sendTime-startTime)

    t = threading.Thread(target=sendThread)
    t.setDaemon(True)
    t.start()

def on_data (client, message, message_type, is_last):
    global endTime
    endTime = time.time()
    #print ("Received text data. ",message)
    #print("Receive time = ", endTime - startTime)
    if (websocket.ABNF.OPCODE_TEXT == message_type):
        #print ("Received text. time = {0:0.2f} Real Time ={1:0.2f}".format(endTime - startTime, endTime -sendTime))
        #log (message)
        # decode response, is not a json file
        
        response_path = utils.parse_header_value(message, 'Path')
        if response_path is None:
            print('Error: invalid response header.')
            return


        parsed = utils.parse_body_json(message)
        Duration = parsed["Duration"]

        # Finally result use DisplayText as result
        # partial result use Text as result
        if response_path == 'speech.phrase':
            text = parsed["DisplayText"]
            print ("Received Result. time = {0:.2f} Real Time = {1:.2f}".format( endTime - startTime,endTime -sendTime))
            print("Path:{2}\t time:{1} STT Result:{0}".format(text,Duration/100000000,response_path) )

        else:
            #parsed = json.loads(message)
            text = parsed["Text"]
            #print(text)
 
        if text == '结束会话。':
            client.close()
    else:
        print ("Received data of type: " + str (message_type))

def on_error (client, error):
    print ("Connection error: " + str (error))
    #client.close()

def on_close (client):
    print ("Connection closed.")


def obtain_auth_token(api_key):
    headers = {
        'Content-type': 'application/x-www-form-urlencoded',
        'Content-Length': '0',
        'Ocp-Apim-Subscription-Key': api_key
    }

    response = requests.post(auth_url, headers=headers)

    # DEBUG PRINT
    # print(r.headers['content-type'])
    # print(r.text)

    data = None
    if response.status_code == 200:
        data = response.text
    elif response.status_code == 403 or response.status_code == 401:
        print('Error: access denied. Please, make sure you provided a valid API key.')
        exit()
    else:
        response.raise_for_status()

    return data


if __name__ == '__main__':

    # Parse input arguments
    parser = argparse.ArgumentParser(description='Speech Translator Demo script. use language.py to list support language')
    parser.add_argument("--source","-s", default = "zh-CN", help="recognition speech language.default is zh_CN")
    parser.add_argument("--to","-t", default = "en", help="translate language. default is en")
    parser.add_argument("--voice","-v", default = "en-US-BenjaminRUS", help="translate language. default is en-US-BenjaminRUS")


    parser.add_argument("--debug","-d", action="store_true", default =False,help="debug True/Flase")
    
    args = parser.parse_args()
    debug = args.debug
    debug = True
    log(url)

    startTime = time.time()
    authToken = obtain_auth_token(key)
    endTime = time.time()
    print("Auth time:",endTime - startTime)
    print('X-ConnectionId: ' + connection_id)



    # recalcuate startTime, sentTime
    startTime = time.time()
    sendTime = startTime
    client = websocket.WebSocketApp(
        url,
        header=[
            'X-ConnectionId: ' + connection_id,
            'Authorization: ' +'Bearer '+authToken
        ],
        on_open=on_open,
        on_data=on_data,
        on_error=on_error,
        on_close=on_close
    )

    print ("Connecting...")
    client.run_forever()