from setuptools import setup, find_packages

setup(
    name='webrtc',
    version='0.1',
    keywords=('webrtc','gstreamer'),
    description='gstreamer webrtc wrapper for python',
    license='MIT Licence',
    url='https://github.com/RTCEngine',
    author='notedit',
    author_email='leeoxiang@gmail.com',
    packages = find_packages(),
    install_requires=[
        'PyGObject>=3.28.3',
    ]
)
