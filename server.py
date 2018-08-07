import socketio
import eventlet
import eventlet.wsgi
from flask import Flask


sio = socketio.Server()
app = Flask(__name__)

@sio.on('connect')
def connect(sid, environ):
    print('connect ', sid)


@sio.on('disconnect')
def disconnect(sid, environ):
    print('disconnect', sid)


@sio.on('message')
def message(sid, data):
    print('message', data)
    sio.emit('reply', room=sid)



if __name__ == '__main__':
    app = socketio.Middleware(sio, app)
    eventlet.wsgi.server(eventlet.listen(('',8000)), app)