import time

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Gst,GstPbutils

from .utils  import make_element,add_many,link_many

Gst.init(None)

class Sink(Gst.Bin):

    def __init__(self):
        Gst.Bin.__init__(self)

    @property
    def audio_pad(self):
        raise 'need have audio src pad'

    @property
    def video_pad(self):
        raise 'need have video src pad'

class FakeSink(Sink):

    def __init__(self):
        Sink.__init__(self)

        audio_fakesink = make_element('fakesink')
        video_fakesink = make_element('fakesink')

        self.add(audio_fakesink)
        self.add(video_fakesink)

        self.audio_sinkpad = Gst.GhostPad.new('audio_sink', audio_fakesink.get_static_pad('sink'))
        self.add_pad(self.audio_sinkpad)

        self.video_sinkpad = Gst.GhostPad.new('video_sink', video_fakesink.get_static_pad('sink'))
        self.add_pad(self.video_sinkpad)

    @property
    def audio_pad(self):
        return self.audio_sinkpad

    @property
    def video_pad(self):
        return self.video_sinkpad

class FileSink(Sink):

    def __init__(self, filename):
        Sink.__init__(self)

        mux = make_element('matroskamux',{'streamable':False})
        filesink = make_element('filesink', {'location':str(time.time()) + '.mkv'})

        self.add(mux)
        self.add(filesink)
        mux.link(filesink)


        self.audio_sinkpad = Gst.GhostPad.new('audio_sink', mux.get_request_pad('audio_%u'))
        self.add_pad(self.audio_sinkpad)

        self.video_sinkpad = Gst.GhostPad.new('video_sink', mux.get_request_pad('video_%u'))
        self.add_pad(self.video_sinkpad)

    @property
    def audio_pad(self):
        return self.audio_sinkpad


    @property
    def video_pad(self):
        return self.video_sinkpad



class RTMPSink(Sink):

    def __init__(self,rtmpURL, transcode=True):
        Sink.__init__(self)

        self.rtmpURL = rtmpURL
        self.transcode = transcode

        audiodecode = make_element('decodebin')
        videodecode = make_element('decodebin')
        audiodecode.connect('pad-added', self.on_decodebin_pad)
        videodecode.connect('pad-added', self.on_decodebin_pad)

        self.add(audiodecode)
        self.add(videodecode)

        encodebin = make_element('encodebin', {'avoid-reencoding':True})
        profile = self._create_encoding_profile()
        encodebin.set_property('profile', profile)

        self.add(encodebin)

        location = rtmpURL + ' live=1'
        rtmpsink = make_element('rtmpsink', {'location':location})

        self.add(rtmpsink)

        encodebin.link(rtmpsink)

        self.encodebin = encodebin

        self.audio_sinkpad = Gst.GhostPad.new('audio_sink', audiodecode.get_static_pad('sink'))
        self.add_pad(self.audio_sinkpad)

        self.video_sinkpad = Gst.GhostPad.new('video_sink', videodecode.get_static_pad('sink'))
        self.add_pad(self.video_sinkpad)


    @property
    def audio_pad(self):
        return self.audio_sinkpad

    @property
    def video_pad(self):
        return self.video_sinkpad


    def _create_encoding_profile(self):
        container = GstPbutils.EncodingContainerProfile.new('flv', None,
                            Gst.Caps.new_empty_simple('video/x-flv'), None)
        # h264
        video = GstPbutils.EncodingVideoProfile.new(
                        Gst.Caps.new_empty_simple('video/x-h264'),
                        None, None, 0)
        # aac
        audio = GstPbutils.EncodingAudioProfile.new(
                        Gst.Caps.from_string('audio/mpeg, mpegversion=4'),
                        None, None, 0)

        container.add_profile(video)
        container.add_profile(audio)
        return container


    def on_decodebin_pad(self, element, pad):

        if not pad.has_current_caps():
            print(pad, 'has no caps, ignoring')
            return

        caps = pad.get_current_caps()
        name = caps.to_string()
        print(name)

        if name.startswith('video'):
            q = make_element('queue')
            conv = make_element('videoconvert')
            self.add(q)
            self.add(conv)
            self.sync_children_states()
            pad.link(q.get_static_pad('sink'))
            q.link(conv)
            conv.link(self.encodebin)
        elif name.startswith('audio'):
            q = make_element('queue')
            conv = make_element('audioconvert')
            self.add(q)
            self.add(conv)
            self.sync_children_states()
            pad.link(q.get_static_pad('sink'))
            q.link(conv)
            conv.link(self.encodebin)



# for H264/OPUS, only do audio transcode
class RTMPSink2(Sink):

    def __init__(self, rtmpURL):
        Sink.__init__(self)
        self.rtmpURL = rtmpURL

        audiodecode = make_element('decodebin')
        audiodecode.connect('pad-added', self.on_decodebin_pad)

        videoparse = make_element('parsebin')
        videoparse.connect('pad-added', self.on_parsebin_pad)

        self.add(audiodecode)
        self.add(videoparse)

        encodebin = make_element('encodebin', {'avoid-reencoding':True})
        profile = self._create_encoding_profile()
        encodebin.set_property('profile', profile)

        self.add(encodebin)

        location = rtmpURL + ' live=1'
        rtmpsink = make_element('rtmpsink', {'location':location})

        self.add(rtmpsink)

        encodebin.link(rtmpsink)

        self.encodebin = encodebin

        self.audio_sinkpad = Gst.GhostPad.new('audio_sink', audiodecode.get_static_pad('sink'))
        self.add_pad(self.audio_sinkpad)

        self.video_sinkpad = Gst.GhostPad.new('video_sink', videoparse.get_static_pad('sink'))
        self.add_pad(self.video_sinkpad)


    @property
    def audio_pad(self):
        return self.audio_sinkpad

    @property
    def video_pad(self):
        return self.video_sinkpad


    def on_decodebin_pad(self, element, pad):

        if not pad.has_current_caps():
            print(pad, 'has no caps, ignoring')
            return

        caps = pad.get_current_caps()
        name = caps.to_string()
        print(name)

        if name.startswith('audio'):
            q = make_element('queue')
            conv = make_element('audioconvert')
            self.add(q)
            self.add(conv)
            self.sync_children_states()
            pad.link(q.get_static_pad('sink'))
            q.link(conv)
            conv.link(self.encodebin)


    def on_parsebin_pad(self, element, pad):

        if not pad.has_current_caps():
            print(pad, 'has no caps, ignoring')
            return

        caps = pad.get_current_caps()
        name = caps.to_string()
        print(name)

        if name.startswith('video'):
            q = make_element('queue')
            self.add(q)
            self.sync_children_states()
            pad.link(q.get_static_pad('sink'))
            q.link(self.encodebin)


    def _create_encoding_profile(self):
        container = GstPbutils.EncodingContainerProfile.new('flv', None,
                            Gst.Caps.new_empty_simple('video/x-flv'), None)
        # h264
        video = GstPbutils.EncodingVideoProfile.new(
                        Gst.Caps.new_empty_simple('video/x-h264'),
                        None, None, 0)
        # aac
        audio = GstPbutils.EncodingAudioProfile.new(
                        Gst.Caps.from_string('audio/mpeg, mpegversion=4'),
                        None, None, 0)

        container.add_profile(video)
        container.add_profile(audio)
        return container



# for H264/OPUS, only do audio transcode
# rtspclientsink
class RTSPSink(Sink):

    def __init__(self,rtspURL):
        Sink.__init__(self)

        audiodecode = make_element('decodebin')
        audiodecode.connect('pad-added', self.on_decodebin_pad)

        videoparse = make_element('parsebin')
        videoparse.connect('pad-added', self.on_parsebin_pad)

        self.add(audiodecode)
        self.add(videoparse)

        self.rtspURL = rtspURL

        location = rtspURL
        rtspsink = make_element('rtspclientsink', {'location':location,'latency':0})

        self.add(rtspsink)

        self.rtspsink = rtspsink

        self.audio_sinkpad = Gst.GhostPad.new('audio_sink', audiodecode.get_static_pad('sink'))
        self.add_pad(self.audio_sinkpad)

        self.video_sinkpad = Gst.GhostPad.new('video_sink', videoparse.get_static_pad('sink'))
        self.add_pad(self.video_sinkpad)

    @property
    def audio_pad(self):
        return self.audio_sinkpad

    @property
    def video_pad(self):
        return self.video_sinkpad


    def on_decodebin_pad(self, element, pad):

        if not pad.has_current_caps():
            print(pad, 'has no caps, ignoring')
            return

        caps = pad.get_current_caps()
        name = caps.to_string()
        print(name)

        if name.startswith('audio'):
            q = make_element('queue')
            conv = make_element('audioconvert')
            encode = make_element('faac')
            self.add(q)
            self.add(conv)
            self.add(encode)
            self.sync_children_states()
            pad.link(q.get_static_pad('sink'))
            q.link(conv)
            conv.link(encode)
            encode.link(self.rtspsink)

    def on_parsebin_pad(self, element, pad):

        if not pad.has_current_caps():
            print(pad, 'has no caps, ignoring')
            return

        caps = pad.get_current_caps()
        name = caps.to_string()
        print(name)

        if name.startswith('video'):
            q = make_element('queue')
            self.add(q)
            self.sync_children_states()
            pad.link(q.get_static_pad('sink'))
            q.link(self.rtspsink)
