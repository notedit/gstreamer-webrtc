

import asyncio
import os
import sys

import attr
from pyee import EventEmitter

import gi
gi.require_version('GObject', '2.0')
from gi.repository import GObject
gi.require_version('Gst', '1.0')
from gi.repository import Gst
gi.require_version('GstWebRTC', '1.0')
from gi.repository import GstWebRTC
gi.require_version('GstSdp', '1.0')
from gi.repository import GstSdp
from gi.repository import GLib

Gst.init(None)

PIPELINE_DESC = '''
webrtcbin name=webrtc
 videotestsrc ! videoconvert ! queue ! vp8enc deadline=1 ! rtpvp8pay !
 queue ! application/x-rtp,media=video,encoding-name=VP8,payload=97 ! webrtc.
 audiotestsrc wave=red-noise ! audioconvert ! audioresample ! queue ! opusenc ! rtpopuspay !
 queue ! application/x-rtp,media=audio,encoding-name=OPUS,payload=96 ! webrtc.
'''


PIPELINE_DESC2 = '''
webrtcbin name=webrtc
 videotestsrc pattern=ball ! videoconvert ! queue ! vp8enc deadline=1 ! rtpvp8pay !
 queue ! application/x-rtp,media=video,encoding-name=VP8,payload=97 ! webrtc.'''


VP8_CAPS = Gst.Caps.from_string('application/x-rtp,media=video,encoding-name=VP8,payload=97,clock-rate=90000')
H264_CAPS = Gst.Caps.from_string('application/x-rtp,media=video,encoding-name=H264,payload=98,clock-rate=90000')
OPUS_CAPS = Gst.Caps.from_string('application/x-rtp,media=audio,encoding-name=OPUS,payload=100,clock-rate=48000')


class WebRTC(EventEmitter):

    def __init__(self,stun_server=None, turn_server=None):
        super().__init__()

        self.stun_server = stun_server
        self.turn_server = turn_server
        self.pipe = Gst.parse_launch(PIPELINE_DESC)
        self.webrtc = self.pipe.get_by_name('webrtc')

        self.srs_pads = []
        self.sink_pads = []

        self.webrtc.connect('on-negotiation-needed', self.on_negotiation_needed)
        self.webrtc.connect('on-ice-candidate', self.on_ice_candidate)
        self.webrtc.connect('pad-added', self.on_add_stream)
        self.webrtc.connect('pad-removed', self.on_remove_stream)

        if self.stun_server:
            self.webrtc.set_property('stun-server', self.stun_server)

        if self.turn_server:
            self.webrtc.set_property('turn-server', self.turn_server)
            
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

        self.emit('candidate', {
            'sdpMLineIndex': mlineindex,
            'candidate': candidate
        })


    def add_transceiver(self, direction, codec):
        upcodec = codec.upper()
        caps = None
        if upcodec == 'H264':
            caps = H264_CAPS
        elif upcodec == 'VP8':
            caps = VP8_CAPS
        elif upcodec == 'OPUS':
            caps = OPUS_CAPS
        self.webrtc.emit('add-transceiver', direction, caps)


    async def create_offer(self):
        future = asyncio.Future()
        promise = Gst.Promise.new_with_change_func(self.on_offer_created, self.webrtc, future)
        self.webrtc.emit('create-offer', None, promise)
        print(asyncio.get_event_loop())
        offer = await asyncio.wait_for(future,100)
        return offer
        #asyncio.get_event_loop().run_until_complete(future)

    def on_offer_created(self, promise, element, future):
        print('1111111')
        promise.wait()
        reply = promise.get_reply()
        offer = reply.get_value('offer')
        future.set_result(offer)
        print('22222222')
        print(asyncio.get_event_loop())
        #future.cancel()


    def get_transceivers(self):
        return self.webrtc.emit('get-transceivers')

    def create_answer(self):
        promise = Gst.Promise.new_with_change_func(self.on_answer_created, self.webrtc, None)
        self.webrtc.emit('create-answer', None, promise)


    def on_answer_created(self, promise, element, _):
        ret = promise.wait()
        if ret != Gst.PromiseResult.REPLIED:
            return
        reply = promise.get_reply()
        answer = reply.get_value('answer')
        if answer:
            self.emit('answer', answer)


    def add_ice_candidate(self, ice):
        sdpMLineIndex = ice['sdpMLineIndex']
        candidate = ice['candidate']
        self.webrtc.emit('add-ice-candidate', sdpMLineIndex, candidate)


    def set_local_description(self, sdp):
        #promise = Gst.Promise.new_with_change_func(self.set_description_result, self.webrtc, None)
        promise = Gst.Promise.new()
        self.webrtc.emit('set-local-description', sdp, promise)
        promise.interrupt()

    def set_remote_description(self, sdp):
        #promise = Gst.Promise.new_with_change_func(self.set_description_result, self.webrtc, None)
        promise = Gst.Promise.new()
        self.webrtc.emit('set-remote-description', sdp, promise)
        promise.interrupt()


    def get_stats(self):
        pass

    def set_description_result(self, promise, element, _):
        ret = promise.wait()
        if ret != Gst.PromiseResult.REPLIED:
            return
        print('set description error')
        reply = promise.get_reply()
        print(reply)


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

    def on_remove_stream(self, element, pad):
        # local stream
        if pad.direction == Gst.PadDirection.SINK:
            print('remove sink ========')
            return

        print('remove src =======')

    def on_incoming_decodebin_stream(self, element, pad):

        if not pad.has_current_caps():
            print(pad, 'has no caps, ignoring')
            return

        caps = pad.get_current_caps()
        name = caps.to_string()
        print(caps)
        if name.startswith('video'):
            q = Gst.ElementFactory.make('queue')
            conv = Gst.ElementFactory.make('videoconvert')
            sink = Gst.ElementFactory.make('fakesink')
            self.pipe.add(q)
            self.pipe.add(conv)
            self.pipe.add(sink)
            self.pipe.sync_children_states()
            pad.link(q.get_static_pad('sink'))
            q.link(conv)
            conv.link(sink)
        elif name.startswith('audio'):
            q = Gst.ElementFactory.make('queue')
            conv = Gst.ElementFactory.make('audioconvert')
            resample = Gst.ElementFactory.make('audioresample')
            sink = Gst.ElementFactory.make('autoaudiosink')
            self.pipe.add(q)
            self.pipe.add(conv)
            self.pipe.add(resample)
            self.pipe.add(sink)
            self.pipe.sync_children_states()
            pad.link(q.get_static_pad('sink'))
            q.link(conv)
            conv.link(resample)
            resample.link(sink)





