



import time

import gi
from gi.repository import GLib
gi.require_version('GstWebRTC', '1.0')
from gi.repository import GstWebRTC

from peerconnection import WebRTC

loop = GLib.MainLoop()


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

time.sleep(1)

pc.create_offer()

loop.run()