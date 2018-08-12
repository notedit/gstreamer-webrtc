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


class MediaStreamBase(Gst.Bin):

    def __init__(self):
        Gst.Bin.__init__(self)

    @property
    def audio_pad(self):
        raise 'need have audio src pad'

    @property
    def video_pad(self):
        raise 'need have video src pad'


class TestMediaStream(MediaStreamBase):

    def __init__(self,video_caps=None,audio_caps=None):
        MediaStreamBase.__init__(self)

        if video_caps is None:
            self.video_caps = Gst.caps_from_string('application/x-rtp,media=video,encoding-name=VP8,payload=97,clock-rate=90000')
        else:
            self.video_caps = video_caps

        if audio_caps is None:
            self.audio_caps = Gst.caps_from_string('application/x-rtp,media=audio,encoding-name=OPUS,payload=100,clock-rate=48000')
        else:
            self.audio_caps = audio_caps

        self.setup_bin()


    @property
    def audio_pad(self):
        return self.audio_srcpad

    @property
    def video_pad(self):
        return self.video_srcpad

    def setup_bin(self):

        # todo  add capsfilter 

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



class FileMediaStream(MediaStreamBase):

    def __init__(self,filename):
        MediaStreamBase.__init__(self)

        self.filename = filename
        self.filesrc = Gst.ElementFactory.make('filesrc')
        self.filesrc.set_property('location', self.filename)

        self.dbin = Gst.ElementFactory.make('decodebin')
        self.audioconvert = Gst.ElementFactory.make('audioconvert')
        self.videoconvert = Gst.ElementFactory.make('videoconvert')
        self.audioident = Gst.ElementFactory.make('identity')
        self.videoident = Gst.ElementFactory.make('identity')

        self.add(self.filesrc)
        self.add(self.dbin)
        self.add(self.audioconvert)
        self.add(self.videoconvert)
        self.add(self.audioident)
        self.add(self.videoident)

        self.filesrc.link(self.dbin)
        self.audioconvert.link(self.audioident)
        self.videoconvert.link(self.videoident)

        self.audio_srcpad = Gst.GhostPad.new('audio_src', self.audioident.get_static_pad('src'))
        self.add_pad(self.audio_srcpad)

        self.video_srcpad = Gst.GhostPad.new('video_src', self.videoident.get_static_pad('src'))
        self.add_pad(self.video_srcpad)
        self.dbin.connect('pad-added', self._new_decoded_pad)

    @property
    def video_pad(self):
        return self.video_srcpad

    @property
    def audio_pad(self):
        return self.audio_srcpad

    def setup_bin(self):
        pass

    def _new_decoded_pad(self, dbin, pad):
        caps = pad.get_current_caps()
        structure_name = caps.to_string()

        if structure_name.startswith('audio'):
            if not pad.is_linked():
                pad.link(self.audioconvert.get_static_pad('sink'))

        if structure_name.startswith('video'):
            if not pad.is_linked():
                pad.link(self.videoconvert.get_static_pad('sink'))



