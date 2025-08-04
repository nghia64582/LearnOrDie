# -*- coding:utf-8 -*-
'''
Created on 2010-11-12

@author: leenjewel
'''

from it.gotoandplay.utils.twistedsocket import build_connect

class XMLSocket(object):
    
    def __init__(self):
        self.event_obj = None
        self.socket_client = None
    
    def connect(self, server_host, server_port):
        build_connect(self, server_host, server_port)
        return
    
    def send(self, data):
        self.socket_client.transport.write(data)
        return
    
    def sendXMLObj(self, xml_obj):
        try:
            xml_string = xml_obj.decode('utf-8')
            self.send((xml_string + "\0").encode('utf-8'))
        except Exception as e:
            print(f"Error sending XML object: {e}")
        return
    
    def onConnection(self, socket_client):
        self.socket_client = socket_client
        self.event_obj.onConnection()
        return
    
    def onDataReceived(self, data):
        self.event_obj.onDataReceived(data)
        return
    
    def addEventListener(self, event_obj):
        self.event_obj = event_obj
        return
