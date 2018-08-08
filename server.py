import socketio
import eventlet
import eventlet.wsgi
from flask import Flask
from flask import render_template

from peerconnection import WebRTC

import gi
gi.require_version('GstSdp', '1.0')
from gi.repository import GstSdp
gi.require_version('GstWebRTC', '1.0')
from gi.repository import GstWebRTC

sio = socketio.Server()
app = Flask(__name__,template_folder='./')


rtcs = {}


@app.route('/')
def index():
    return render_template('test.html')
    

@sio.on('connect')
def connect(sid, environ):
    print('connect ', sid)

    rtc = WebRTC()
    rtcs[sid] = rtc

@sio.on('disconnect')
def disconnect(sid):
    print('disconnect', sid)


@sio.on('message')
def message(sid, data):
    print('message', data)
    sio.emit('reply', room=sid)


@sio.on('offer')
def offer(sid,data):
    sdp = data['sdp']
    _,sdpmsg = GstSdp.SDPMessage.new()
    GstSdp.sdp_message_parse_buffer(bytes(sdp.encode()), sdpmsg)
    offer = GstWebRTC.WebRTCSessionDescription.new(GstWebRTC.WebRTCSDPType.OFFER, sdpmsg)

    print(offer)

    rtc = rtcs[sid]

    @rtc.on('answer')
    def on_answer(answer):
        sio.emit('answer', {'sdp':answer.sdp.as_text()}, room=sid)
        print(answer.sdp.as_text())
        rtc.set_local_description(answer)
        print('aaaaa')
        sio.emit('aaaaaaaaaa',room=sid)

    @rtc.on('candidate')
    def on_candidate(candidate):
        sio.emit('candidate', candidate, room=sid)

    rtc.set_remote_description(offer)
    
    rtc.create_answer()

    

@sio.on('candidate')
def candidate(sid,data):

    rtc = rtcs[sid]

    candidate = data['candidate']
    if candidate is None:
        return


    print('socketio receive candidate', data)
    rtc.add_ice_candidate(candidate)


if __name__ == '__main__':
    app = socketio.Middleware(sio, app)
    eventlet.wsgi.server(eventlet.listen(('',8000)), app)