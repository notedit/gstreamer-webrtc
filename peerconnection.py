

import asyncio
import os
import sys

import attr
from pyee import EventEmitter

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
gi.require_version('GObject', '2.0')
from gi.repository import GObject
gi.require_version('GstWebRTC', '1.0')
from gi.repository import GstWebRTC
gi.require_version('GstSdp', '1.0')
from gi.repository import GstSdp

Gst.init(None)
GObject.threads_init()

PIPELINE_DESC = '''
webrtcbin name=webrtc
 videotestsrc pattern=ball ! videoconvert ! queue ! vp8enc deadline=1 ! rtpvp8pay !
 queue ! application/x-rtp,media=video,encoding-name=VP8,payload=97 ! webrtc.
 audiotestsrc wave=red-noise ! audioconvert ! audioresample ! queue ! opusenc ! rtpopuspay !
 queue ! application/x-rtp,media=audio,encoding-name=OPUS,payload=96 ! webrtc.
'''

class WebRTC(EventEmitter):

    def __init__(self,config=None):
        super().__init__()

        self.config = config
        self.pipe = Gst.parse_launch(PIPELINE_DESC)
        self.webrtc = self.pipe.get_by_name('webrtc')

        self.webrtc.connect('on-negotiation-needed', self.on_negotiation_needed)
        self.webrtc.connect('on-ice-candidate', self.on_ice_candidate)
        self.webrtc.connect('pad-added', self.on_add_stream)
        self.pipe.set_state(Gst.State.PLAYING)

    @property
    def connection_state(self):
        return self.webrtc.get_property('connection-state')

    @property
    def ice_connection_state(self):
        return self.webrtc.get_property('ice-connection-state')

    @property
    def local_description(self):
        return self.webrtc.get_property('local-description')

    @property
    def remote_description(self):
        return self.webrtc.get_property('remote-description')


    def on_negotiation_needed(self, element):
        self.emit('negotiation-needed', element)

    def on_ice_candidate(self, element, mlineindex, candidate):
        self.emit('ice-candidate', {
            'sdpMLineIndex': mlineindex,
            'candidate': candidate
        })

    
    def add_transceiver(self, direction, caps):
        pass


    def create_offer(self, options=None):
        promise = Gst.Promise.new_with_change_func(self.on_offer_created, self.webrtc, None)
        self.webrtc.emit('create-offer', None, promise)

    def on_offer_created(self, promise, element, _):
        ret = promise.wait()
        if ret != Gst.PromiseResult.REPLIED:
            return
        offer = promise.get_reply().get_value('offer')
        if offer:
            self.emit('offer', offer)

        # offer.sdp.as_text()

    def create_answer(self, options=None):
        promise = Gst.Promise.new_with_change_func(self.on_answer_created, self.webrtc, None)
        self.webrtc.emit('create-answer', None, promise)
    
    def on_answer_created(self, promise, element, _):
        ret = promise.wait()
        if ret != Gst.PromiseResult.REPLIED:
            return
        answer = promise.get_reply().get_value('answer')
        if answer:
            self.emit('answer', answer)

    def add_ice_candidate(self, candidate,sdpMLineIndex):
        self.webrtc.emit('add-ice-candidate', sdpmlineindex, candidate)

    def set_local_description(self, sdp, sdptype):
        _, sdpmsg = GstSdp.SDPMessage.new()
        GstSdp.sdp_message_parse_buffer(bytes(sdp), sdpmsg)
        sdptype = GstWebRTC.WebRTCSDPType.ANSWE if sdptype == 'answer' else GstWebRTC.WebRTCSDPType.OFFER
        sdp = GstWebRTC.WebRTCSessionDescription.new(sdptype, sdpmsg)
        promise = Gst.Promise.new_with_change_func(self.set_description_result, self.webrtc, None)
        self.webrtc.emit('set-local-description', sdp, promise)


    def set_remote_description(self, sdp, sdptype):
        _, sdpmsg = GstSdp.SDPMessage.new()
        GstSdp.sdp_message_parse_buffer(bytes(sdp), sdpmsg)
        sdptype = GstWebRTC.WebRTCSDPType.ANSWE if sdptype == 'answer' else GstWebRTC.WebRTCSDPType.OFFER
        sdp = GstWebRTC.WebRTCSessionDescription.new(sdptype, sdpmsg)
        promise = Gst.Promise.new_with_change_func(self.set_description_result, self.webrtc, None)
        self.webrtc.emit('set-remote-description', sdp, promise)

    def set_description_result(self, promise, element, _):
        ret = promise.wait()
        if ret != Gst.PromiseResult.REPLIED:
            return
        print('set description error')
        

    def on_add_stream(self,element, pad):
        # local stream
        if pad.direction == Gst.PadDirection.SINK:
            print('add sink ========')
            return

        # remote stream 
        decodebin = Gst.ElementFactory.make('decodebin')
        decodebin.connect('pad-added', self.on_incoming_decodebin_stream)
        self.pipe.add(decodebin)
        decodebin.sync_state_with_parent()
        self.webrtc.link(decodebin)


    def on_incoming_decodebin_stream(self, element, pad):
        
        if not pad.has_current_caps():
            print(pad, 'has no caps, ignoring')
            return

        caps = pad.get_current_caps()
        assert (len(caps))
        s = caps[0]
        print('on_incoming_decodebin_stream', caps)
        name = s.get_name()
        if name.startswith('video'):
            q = Gst.ElementFactory.make('queue')
            conv = Gst.ElementFactory.make('videoconvert')
            sink = Gst.ElementFactory.make('autovideosink')
            self.pipe.add(q, conv, sink)
            self.pipe.sync_children_states()
            pad.link(q.get_static_pad('sink'))
            q.link(conv)
            conv.link(sink)
        elif name.startswith('audio'):
            q = Gst.ElementFactory.make('queue')
            conv = Gst.ElementFactory.make('audioconvert')
            resample = Gst.ElementFactory.make('audioresample')
            sink = Gst.ElementFactory.make('autoaudiosink')
            self.pipe.add(q, conv, resample, sink)
            self.pipe.sync_children_states()
            pad.link(q.get_static_pad('sink'))
            q.link(conv)
            conv.link(resample)
            resample.link(sink)


if __name__ == '__main__':
    loop = GObject.MainLoop()
    pc = WebRTC()
    @pc.on('offer')
    def on_offer(offer):
        print(offer)

    @pc.on('answer')
    def on_answer(answer):
        print(answer)

    pc.create_offer()
    
    loop.run()
    
    
    