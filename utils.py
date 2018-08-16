import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

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