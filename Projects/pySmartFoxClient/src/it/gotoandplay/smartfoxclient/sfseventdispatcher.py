# -*- coding:utf-8 -*-
'''
Created on 2010-11-13

@author: leenjewel
'''

class SFSEventDispatcher(object):
    def __init__(self):
        self.listeners = {}
    
    def addEventListener(self, event_name, event_obj):
        if event_name not in self.listeners:
            self.listeners[event_name] = []
        self.listeners[event_name].append(event_obj)
        return
    
    def removeEventListener(self, event_name):
        if event_name in self.listeners:
            del self.listeners[event_name]
        return
    
    def dispatchEvent(self, event_obj):
        event_name = event_obj.getName()
        if event_name in self.listeners:
            listeners = self.listeners[event_name]
            for listener in listeners:
                listener.handleEvent(event_obj)
        return