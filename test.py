import time
import asyncio

import gi
from gi.repository import GLib
gi.require_version('GstWebRTC', '1.0')
from gi.repository import GstWebRTC

from peerconnection import WebRTC


async def test():

    pc = WebRTC()

    @pc.on('offer')
    def on_offer(offer):
        print(offer)
        print(offer.sdp.as_text())

    @pc.on('answer')
    def on_answer(answer):
        print(answer)

    pc.add_transceiver(GstWebRTC.WebRTCRTPTransceiverDirection.RECVONLY, 'H264')
    pc.add_transceiver(GstWebRTC.WebRTCRTPTransceiverDirection.RECVONLY, 'OPUS')


    offer = await pc.create_offer()
    
    print(offer)
    

if __name__ == '__main__':
   
    asyncio.get_event_loop().run_until_complete(test())