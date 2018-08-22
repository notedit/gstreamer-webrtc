
import time
import json
import asyncio
import websockets


from webrtc import WebRTC
from webrtc import TestSource
from webrtc import FileSink,RTMPSink

import gi
gi.require_version('GstSdp', '1.0')
from gi.repository import GstSdp
gi.require_version('GstWebRTC', '1.0')
from gi.repository import GstWebRTC




rtcs = {}

async def hello(websocket, path):

    filesink = FileSink(str(time.time()) + '.mkv')
    #rtmpsink = RTMPSink('rtmp://localhost/live/live')

    rtc = WebRTC(outsink=filesink)
    rtcs[websocket] = rtc

    @rtc.on('candidate')
    def on_candidate(candidate):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(websocket.send(json.dumps({
            'candidate':candidate
        })))
        print('send candidate', candidate)

    @rtc.on('answer')
    def on_answer(answer):
        rtc.set_local_description(answer)
        loop = asyncio.new_event_loop()
        loop.run_until_complete(websocket.send(json.dumps({
            'answer':answer.sdp.as_text()
        })))
        print('send answer', answer.sdp.as_text())

    @rtc.on('offer')
    def on_offer(offer):
        rtc.set_local_description(offer)
        loop = asyncio.new_event_loop()
        loop.run_until_complete(websocket.send(json.dumps({
            'offer':offer.sdp.as_text()
        })))
        print('send offer', offer.sdp.as_text())


    @rtc.on('negotiation-needed')
    def on_negotiation_needed(element):
        print('negotiation-needed', element)

    source  = TestSource()

    rtc.add_stream(source)

    try:
        async for message in websocket:
            print(message)
            msg = json.loads(message)

            if msg.get('join'):
                rtc.create_offer()

            if msg.get('answer'):
                sdp = msg['answer']
                _,sdpmsg = GstSdp.SDPMessage.new()
                GstSdp.sdp_message_parse_buffer(bytes(sdp.encode()), sdpmsg)
                answer = GstWebRTC.WebRTCSessionDescription.new(GstWebRTC.WebRTCSDPType.ANSWER, sdpmsg)
                rtc.set_remote_description(answer)

            if msg.get('candidate') and msg['candidate'].get('candidate'):
                print('add_ice_candidate')
                rtc.add_ice_candidate(msg['candidate'])

    finally:
        print('leave===========')



start_server = websockets.serve(hello, '0.0.0.0', 8000)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
