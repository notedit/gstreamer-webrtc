import gi
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import GLib, GObject, Gst, GstPbutils

Gst.init(None)


def make_element(name,propertys={}):
    element = Gst.ElementFactory.make(name)
    for (k,v) in propertys.items():
        element.set_property(k,v)
    return element

def add_many(element,*args):
    for ele in args:
        element.add(ele)

def link_many(*args):
    for i in range(len(args) - 1):
        args[i].link(args[i+1])



VP8_CAPS = Gst.Caps.from_string('application/x-rtp,media=video,encoding-name=VP8,payload=97,clock-rate=90000')
H264_CAPS = Gst.Caps.from_string('application/x-rtp,media=video,encoding-name=H264,payload=98,clock-rate=90000')
OPUS_CAPS = Gst.Caps.from_string('application/x-rtp,media=audio,encoding-name=OPUS,payload=100,clock-rate=48000')


def raw2rtpbin(encodeing,playload,clock_rate):
    pass


class Source(Gst.Bin):

    def __init__(self):
        Gst.Bin.__init__(self)

    @property
    def audio_pad(self):
        raise 'need have audio src pad'

    @property
    def video_pad(self):
        raise 'need have video src pad'


TEST_VIDEO_BIN_STR = '''
videotestsrc ! videoconvert ! queue ! vp8enc deadline=1 ! rtpvp8pay ! 
application/x-rtp,media=video,encoding-name=VP8,payload=97,clock-rate=90000 ! queue
'''

TEST_AUDIO_BIN_STR = '''
audiotestsrc wave=red-noise ! audioconvert ! audioresample ! queue ! opusenc ! rtpopuspay ! 
application/x-rtp,media=audio,encoding-name=OPUS,payload=100,clock-rate=48000 ! queue 
'''


class TestSource(Source):

    def __init__(self):
        Source.__init__(self)

        # self.video_caps = Gst.caps_from_string('application/x-rtp,media=video,encoding-name=VP8,payload=97,clock-rate=90000')
        # self.audio_caps = Gst.caps_from_string('application/x-rtp,media=audio,encoding-name=OPUS,payload=100,clock-rate=48000')
        # self.setup_bin()

        audiobin = Gst.parse_bin_from_description(TEST_AUDIO_BIN_STR, True)
        videobin = Gst.parse_bin_from_description(TEST_VIDEO_BIN_STR, True)

        self.add(audiobin)
        self.add(videobin)

        self.audio_srcpad = Gst.GhostPad.new('audio_src', audiobin.get_static_pad('src'))
        self.add_pad(self.audio_srcpad)

        self.video_srcpad = Gst.GhostPad.new('video_src', videobin.get_static_pad('src'))
        self.add_pad(self.video_srcpad)


    @property
    def audio_pad(self):
        return self.audio_srcpad

    @property
    def video_pad(self):
        return self.video_srcpad

    def setup_bin(self):

        """
        videotestsrc ! videoconvert ! queue ! vp8enc deadline=1 ! rtpvp8pay ! queue
        """
        videosrc = make_element('videotestsrc')
        videoconvert = make_element('videoconvert')
        videoenc = make_element('vp8enc')
        videoenc.set_property('deadline',1)
        videortppay = make_element('rtpvp8pay')
        videocapsfilter = make_element('capsfilter')
        videocapsfilter.set_property('caps', self.video_caps)
        videoqueue = make_element('queue')
        self.add(videosrc)
        self.add(videoconvert)
        self.add(videoenc)
        self.add(videortppay)
        self.add(videocapsfilter)
        self.add(videoqueue)
        videosrc.link(videoconvert)
        videoconvert.link(videoenc)
        videoenc.link(videortppay)
        videortppay.link(videocapsfilter)
        videocapsfilter.link(videoqueue)

        self.video_srcpad = Gst.GhostPad.new('video_src', videoqueue.get_static_pad('src'))
        self.add_pad(self.video_srcpad)
        
        """
        audiotestsrc wave=red-noise ! audioconvert ! audioresample ! queue ! opusenc ! rtpopuspay ! queue 
        """

        audiosrc = make_element('audiotestsrc')
        audiosrc.set_property('wave','red-noise')
        audioconvert = make_element('audioconvert')
        audioresample = make_element('audioresample')
        audioenc = make_element('opusenc')
        audiortppay = make_element('rtpopuspay')
        audiocapsfilter = make_element('capsfilter')
        audiocapsfilter.set_property('caps', self.audio_caps)
        audioqueue = make_element('queue')

        self.add(audiosrc)
        self.add(audioconvert)
        self.add(audioresample)
        self.add(audioenc)
        self.add(audiortppay)
        self.add(audiocapsfilter)
        self.add(audioqueue)
        audiosrc.link(audioconvert)
        audioconvert.link(audioresample)
        audioresample.link(audioenc)
        audioenc.link(audiortppay)
        audiortppay.link(audiocapsfilter)
        audiocapsfilter.link(audioqueue)

        self.audio_srcpad = Gst.GhostPad.new('audio_src', audioqueue.get_static_pad('src'))
        self.add_pad(self.audio_srcpad)


FILE_VIDEO_BIN_STR = '''
videoconvert ! vp8enc deadline=1 ! rtpvp8pay ! 
application/x-rtp,media=video,encoding-name=VP8,payload=97,clock-rate=90000 ! queue
'''

FILE_AUDIO_BIN_STR = '''
audioconvert ! audioresample ! opusenc ! rtpopuspay ! 
application/x-rtp,media=audio,encoding-name=OPUS,payload=100,clock-rate=48000 ! queue 
'''

class FileSource(Source):


    def __init__(self,filename):
        Source.__init__(self)

        self.filename = filename
        filesrc = make_element('filesrc', {'location':self.filename})
        decodebin = make_element('decodebin')

        self.add(filesrc)
        self.add(decodebin)
        filesrc.link(decodebin)

        audiobin = Gst.parse_bin_from_description(FILE_AUDIO_BIN_STR, True)
        videobin = Gst.parse_bin_from_description(FILE_VIDEO_BIN_STR, True)

        self.add(audiobin)
        self.add(videobin)

        self.audio_srcpad = Gst.GhostPad.new('audio_src', audiobin.get_static_pad('src'))
        self.add_pad(self.audio_srcpad)

        self.video_srcpad = Gst.GhostPad.new('video_src', videobin.get_static_pad('src'))
        self.add_pad(self.video_srcpad)

        self.audiobin = audiobin
        self.videobin = videobin

        decodebin.connect('pad-added', self._new_decoded_pad)

    @property
    def video_pad(self):
        return self.video_srcpad

    @property
    def audio_pad(self):
        return self.audio_srcpad

    def _new_decoded_pad(self, element, pad):

        caps = pad.get_current_caps()
        name = caps.to_string()
        if name.startswith('audio'):
            if not pad.is_linked():
                pad.link(self.audiobin.get_static_pad('sink'))

        if name.startswith('video'):
            if not pad.is_linked():
                pad.link(self.videobin.get_static_pad('sink'))




RTMP_AUDIO_BIN_STR = '''
faad ! audioconvert ! audioresample ! opusenc ! rtpopuspay ! 
application/x-rtp,media=audio,encoding-name=OPUS,payload=100,clock-rate=48000 ! queue
'''

RTMP_VIDEO_BIN_STR = '''
rtph264pay config-interval=-1 ! application/x-rtp,media=video,encoding-name=H264,payload=98,clock-rate=90000 ! queue
'''

class RTMPSource(Source):

    def __init__(self,rtmpURL):
        Source.__init__(self)

        self.rtmpURL = rtmpURL
        rtmpsrc = make_element('rtmpsrc', {'location':self.rtmpURL})
        parsebin = make_element('parsebin')

        self.add(rtmpsrc)
        self.add(parsebin)

        self.video_srcpad = None
        self.audio_srcpad = None

        rtmpsrc.link(parsebin)
        parsebin.connect('pad-added', self._new_parsed_pad)

        self.audiobin = Gst.parse_bin_from_description(RTMP_AUDIO_BIN_STR,True)
        self.videobin = Gst.parse_bin_from_description(RTMP_VIDEO_BIN_STR,True)


    @property
    def audio_pad(self):
        return self.audio_srcpad

    @property
    def video_pad(self):
        return self.video_srcpad


    def _new_parsed_pad(self, element, pad):
        
        caps = pad.get_current_caps()
        name = caps.to_string()

        if name.startswith('audio'):
            if pad.is_linked():
                return
            self.add(self.audiobin)
            self.sync_children_states()
            sinkpad = self.audiobin.get_static_pad('sink')
            pad.link(sinkpad)
            self.audio_srcpad = self.audiobin.get_static_pad('src')

        elif name.startswith('video'):
            if pad.is_linked():
                return
            self.add(self.videobin)
            self.sync_children_states()
            sinkpad = self.videobin.get_static_pad('sink')
            pad.link(sinkpad)
            self.video_srcpad = self.videobin.get_static_pad('src')


class RTSPSource(Source):

    def __init__():
        Source.__init__(self)
        pass