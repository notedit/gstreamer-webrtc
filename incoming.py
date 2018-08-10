import gi
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import GLib, GObject, Gst, GstPbutils

Gst.init(None)


class MediaStream(Gst.Bin):

    def __init__(self,filename):
        Gst.Bin.__init__(self)
        self.filename = filename
        self.filesrc.set_property('location', self.filename)

        self.dbin = Gst.ElementFactory.make('decodebin')
        self.audioconvert = Gst.ElementFactory.make('audioconvert')
        self.videoconvert = Gst.ElementFactory.make('videoconvert')
        self.audioident = Gst.ElementFactory.make('identity')
        self.videoident = Gst.ElementFactory.make('identity')

        self.volume = Gst.ElementFactory.make('volume')
        self.volume.set_property('volume', volume)

        self.add(self.filesrc)
        self.add(self.dbin)
        self.add(self.audioconvert)
        self.add(self.videoconvert)
        self.add(self.volume)
        self.add(self.audioident)
        self.add(self.videoident)

        self.filesrc.link(self.dbin)
        self.audioconvert.link(self.volume)
        self.volume.link(self.audioident)
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

    def _new_decoded_pad(self, dbin, pad):
        caps = pad.get_current_caps()
        structure_name = caps.to_string()

        if structure_name.startswith('audio'):
            if not pad.is_linked():
                pad.link(self.audioconvert.get_static_pad('sink'))

        if structure_name.startswith('video'):
            if not pad.is_linked():
                pad.link(self.videoconvert.get_static_pad('sink'))



