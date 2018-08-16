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


class TestSource(Source):

    def __init__(self):
        Source.__init__(self)

        self.video_caps = Gst.caps_from_string('application/x-rtp,media=video,encoding-name=VP8,payload=97,clock-rate=90000')
        self.audio_caps = Gst.caps_from_string('application/x-rtp,media=audio,encoding-name=OPUS,payload=100,clock-rate=48000')
        self.setup_bin()

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


class FileSource(Source):

    def __init__(self,filename):
        Source.__init__(self)

        self.filename = filename
        filesrc = make_element('filesrc', {'location':self.filename})
        
        decodebin = make_element('decodebin')
        audioconvert = make_element('audioconvert')
        videoconvert = make_element('videoconvert')

        video_caps = Gst.caps_from_string('application/x-rtp,media=video,encoding-name=VP8,payload=97,clock-rate=90000')
        videoenc = make_element('vp8enc')
        videoenc.set_property('deadline',1)
        videortppay = make_element('rtpvp8pay')
        videocapsfilter = make_element('capsfilter')
        videocapsfilter.set_property('caps', video_caps)
        videoqueue = make_element('queue')

        audio_caps = Gst.caps_from_string('application/x-rtp,media=audio,encoding-name=OPUS,payload=100,clock-rate=48000')
        audioresample = make_element('audioresample')
        audioenc = make_element('opusenc')
        audiortppay = make_element('rtpopuspay')
        audiocapsfilter = make_element('capsfilter')
        audiocapsfilter.set_property('caps', self.audio_caps)
        audioqueue = make_element('queue')

        self.add(filesrc)
        self.add(decodebin)
        self.add(audioconvert)
        self.add(videoconvert)
        self.add(videoenc)
        self.add(videortppay)
        self.add(videocapsfilter)
        self.add(videoqueue)

        self.add(audioresample)
        self.add(audioenc)
        self.add(audiortppay)
        self.add(audiocapsfilter)
        self.add(audioqueue)

        filesrc.link(decodebin)

        videoconvert.link(videoenc)
        videoenc.link(videortppay)
        videortppay.link(videocapsfilter)
        videocapsfilter.link(videoqueue)


        audioconvert.link(audioresample)
        audioresample.link(audioenc)
        audioenc.link(audiortppay)
        audiortppay.link(audiocapsfilter)
        audiocapsfilter.link(audioqueue)


        self.videoconvert = videoconvert
        self.audioconvert = audioconvert

        decodebin.connect('pad-added', self._new_decoded_pad)

        self.audio_srcpad = Gst.GhostPad.new('audio_src', self.audioqueue.get_static_pad('src'))
        self.add_pad(self.audio_srcpad)

        self.video_srcpad = Gst.GhostPad.new('video_src', self.videoqueue.get_static_pad('src'))
        self.add_pad(self.video_srcpad)
        

    @property
    def video_pad(self):
        return self.video_srcpad

    @property
    def audio_pad(self):
        return self.audio_srcpad

    def setup_bin(self):
        pass


    def _new_decoded_pad(self, element, pad):
        caps = pad.get_current_caps()
        name = caps.to_string()

        if name.startswith('audio'):
            if not pad.is_linked():
                pad.link(self.audioconvert.get_static_pad('sink'))

        if name.startswith('video'):
            if not pad.is_linked():
                pad.link(self.videoconvert.get_static_pad('sink'))



