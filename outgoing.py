import gi
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import GLib, GObject, Gst, GstPbutils

from utils  import make_element,add_many,link_many


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

        
        
        
    
