from pythonosc import dispatcher, osc_server
from threading import Thread
import socket

class EmotiBitStreamer:
    def __init__(self, port):
        self.ip = self._get_local_ip()
        self.port = port
        self.data = []
        self.dispatcher = dispatcher.Dispatcher()
        self.dispatcher.map("/EmotiBit/0/EDA", self.eda_handler)
        self.server = osc_server.ThreadingOSCUDPServer((self.ip, self.port), self.dispatcher)

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
    
        except Exception as e:
            print(f"Error getting local IP: {str(e)}")
            return "127.0.0.1"  # Fallback to localhost
    
    def get_latest_data(self):
        if self.data:
            return self.data[-1]
        else:
            return None
    
    def eda_handler(self, address, *args):
            self.data.append(args)
    
    def get_data(self):
        return self.data
    
    def start(self):
        print(f"Starting server at {self.ip}:{self.port}")
        self.server.serve_forever()
        
    def stop(self):
        print(f"Stopping server at {self.ip}:{self.port}")
        self.server.shutdown()
        # self.server.server_close()
        
    def add_handler(self, address, handler):
        self.dispatcher.map(address, handler)
        
    def remove_handler(self, address):
        self.dispatcher.unmap(address)
        
    def get_ip(self):
        return self.ip
    
    def get_port(self):
        return self.port