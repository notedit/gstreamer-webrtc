

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


VP8_CAPS = Gst.Caps.from_string('application/x-rtp,media=video,encoding-name=VP8,payload=97,clock-rate=90000')
H264_CAPS = Gst.Caps.from_string('application/x-rtp,media=video,encoding-name=H264,payload=98,clock-rate=90000')
OPUS_CAPS = Gst.Caps.from_string('application/x-rtp,media=audio,encoding-name=OPUS,payload=100,clock-rate=48000')



class WebRTC(EventEmitter):

    INACTIVE = GstWebRTC.WebRTCRTPTransceiverDirection.INACTIVE
    SENDONLY = GstWebRTC.WebRTCRTPTransceiverDirection.SENDONLY
    RECVONLY = GstWebRTC.WebRTCRTPTransceiverDirection.RECVONLY
    SENDRECV = GstWebRTC.WebRTCRTPTransceiverDirection.SENDRECV

    def __init__(self,stun_server=None, turn_server=None):
        super().__init__()

        self.stun_server = stun_server
        self.turn_server = turn_server
        self.streams = []

        self.pipe = Gst.Pipeline.new('webrtc')
        self.webrtc = Gst.ElementFactory.make('webrtcbin')
        self.pipe.add(self.webrtc)


        self.webrtc.connect('on-negotiation-needed', self.on_negotiation_needed)
        self.webrtc.connect('on-ice-candidate', self.on_ice_candidate)
        self.webrtc.connect('pad-added', self.on_add_stream)
        self.webrtc.connect('pad-removed', self.on_remove_stream)

        if self.stun_server:
            self.webrtc.set_property('stun-server', self.stun_server)

        if self.turn_server:
            self.webrtc.set_property('turn-server', self.turn_server)

        bus = self.pipe.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self._bus_call, None)

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
        return self.webrtc.emit('add-transceiver', direction, caps)


    def create_offer(self):
        promise = Gst.Promise.new_with_change_func(self.on_offer_created, self.webrtc, None)
        self.webrtc.emit('create-offer', None, promise)


    def on_offer_created(self, promise, element, _):
        promise.wait()
        reply = promise.get_reply()
        offer = reply.get_value('offer')
        if offer:
            self.emit('offer', offer)

    def add_stream(self, stream):
        self.pipe.add(stream)

        if stream.audio_pad:
            audio_sink_pad = self.webrtc.get_request_pad('sink_%u')
            stream.audio_pad.link(audio_sink_pad)

        if stream.video_pad:
            video_sink_pad = self.webrtc.get_request_pad('sink_%u')
            stream.video_pad.link(video_sink_pad)

        stream.sync_state_with_parent()
        self.streams.append(stream)

    def remove_stream(self, stream):
        if not stream in self.streams:
            return

        stream.set_state(Gst.State.NULL)
        
        if stream.audio_pad:
            sink_pad = stream.audio_pad.get_peer()
            stream.audio_pad.unlik(sink_pad)
            self.webrtc.release_request_pad(sink_pad)

        if stream.video_pad:
            sink_pad = stream.video_pad.get_peer()
            stream.video_pad.unlink(sink_pad)
            self.webrtc.release_request_pad(sink_pad)

        self.webrtc.remove(stream)
        self.streams.remove(stream)

        
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


    def _bus_call(self, bus, message, _):
        t = message.type
        if t == Gst.MessageType.EOS:
            print('End-of-stream')
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print('Error: %s: %s\n' % (err, debug))
        return True


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





