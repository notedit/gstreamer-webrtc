import socketio
import eventlet
import eventlet.wsgi
from flask import Flask

from peerconnection import WebRTC

sio = socketio.Server()
app = Flask(__name__)


rtcs = {}


@sio.on('connect')
def connect(sid, environ):
    print('connect ', sid)

    rtc = WebRTC()
    rtcs[sid] = rtc

@sio.on('disconnect')
def disconnect(sid, environ):
    print('disconnect', sid)


@sio.on('message')
def message(sid, data):
    print('message', data)
    sio.emit('reply', room=sid)


@sio.on('offer')
def offer(sid,data):
    print('offer',data)
    sdp = data['offer']
    _,sdpmsg = GstSdp.SDPMessage.new()
    GstSdp.sdp_message_parse_buffer(bytes(sdp), sdpmsg)
    offer = GstWebRTC.WebRTCSessionDescription.new(GstWebRTC.WebRTCSDPType.OFFER, sdpmsg)

    rtc = rtcs[sid]

    @rtc.on('answer')
    def on_answer(answer):
        print(answer)


@sio.on('candidate')
def candidate(sid,data):

    rtc = rtcs[sid]

    @rtc.on('candidate')
    def on_candidate(mline, candidate):
        print('candidate')

    # todo 



if __name__ == '__main__':
    app = socketio.Middleware(sio, app)
    eventlet.wsgi.server(eventlet.listen(('',8000)), app)