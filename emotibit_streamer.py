from pythonosc import dispatcher, osc_server
from threading import Thread, Event, Timer
import socket
import numpy as np
import atexit
import time
import copy
from datetime import datetime
"""
This class manages the OSC server that receives data from the EmotiBit.
All OSC addresses must be included in the oscOutputSettings.xml file. Some
settings may not be present in the file, but the addresses can be included.
A full list of type tags can be found here: 
https://github.com/EmotiBit/EmotiBit_Docs/blob/master/Working_with_emotibit_data.md/#EmotiBit-data-types

"""
class EmotiBitStreamer:
    def __init__(self, port):
        self._ip = "127.0.0.1"
        self._port = port

        self._data = {
             "EDA": [],
            "HR": [],
            "BI": []
        }
        
        self._baseline_data = {
            "EDA": [],
            "HR": [],
            "BI": []
        }

        # Structure for tracking the last time data was received from the EmotiBit
        self.last_received = {
            "EDA": None,
            "HR": None,
            "BI": None
        }

        self.dispatcher = dispatcher.Dispatcher()
        # self.dispatcher.map("/EmotiBit/0/EDA", self.print_osc_message)
        # self.dispatcher.map("/EmotiBit/0/BI", self.print_osc_message)
        # self.dispatcher.map("/EmotiBit/0/HR", self.print_osc_message)
        # self.dispatcher.map("/EmotiBit/0/TEMP", self.print_osc_message)
        # self.dispatcher.map("/EmotiBit/0/ACC:Z", self.print_osc_message)

        self.dispatcher.map("/EmotiBit/0/*", self.generic_handler)

        self.server_thread = None
        self.shutdown_event = Event()
        self.server = osc_server.ThreadingOSCUDPServer((self.ip, self.port), self.dispatcher)
        self.server.allow_reuse_address = True  
        self.server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
        atexit.register(self.stop)

        # Poll for null values
        self.last_received = {key: time.time() for key in self.data.keys()}
        self.null_record_interval = 5  
        self.default_value = 0

    ###########################################
    # Methods
    ###########################################
    def start(self):
        if self.server_thread is not None and self.server_thread.is_alive():
            print("Server is already running.")
            return
        
        print(f"Starting server at {self.ip}:{self.port}")
        
        self.shutdown_event.clear()  
        self.server_thread = Thread(target=self.server.serve_forever)
        self.server_thread.start()
        
    def stop(self):
        if self.server_thread is not None:
            print(f"Stopping server at {self.ip}:{self.port}")
            self.shutdown_event.set()  
            self.server.shutdown()
            self.server.server_close() 
            self.server_thread.join()  
            self.server_thread = None  
            print("Server stopped successfully.")
        else:
            return None

    def calculate_hrv_from_bi(self, bi_values):
        # HRV metrics directly from BI (beat interval) values
        sdnn = np.std(bi_values)
        rmssd = np.sqrt(np.mean(np.square(np.diff(bi_values))))
        return {"SDNN": sdnn, "RMSSD": rmssd}
    
    def calculate_hrv_from_hr(self, hr_values):
        # Convert HR to IBI
        ibi_values = 60000 / np.array(hr_values)  # Converts HR (bpm) to IBI (ms)
        return self.calculate_hrv_from_bi(ibi_values)  # Use BI-based HRV calculation
    
    def print_osc_message(address, *args):
        """This function is for debugging the incoming messages"""
        print(f"Received OSC message on {address}: {args}")
    
    def get_current_iso_time(self):
        """Returns the current time in ISO 8601 format."""
        return datetime.now().isoformat()
    
    def record_null_values(self):
        """Records null values for each stream type if no values are incoming from the EmotiBit."""
        current_time = time.time()

        for stream_type in self.data.keys():
            if self.last_received[stream_type] is None or current_time - self.last_received[stream_type] >= self.null_record_interval:
                timestamp = self.get_current_iso_time()
                self.data[stream_type].append((timestamp, self.default_value))
                print(f"Appended null value for {stream_type}")

            self.last_received[stream_type] = current_time

    ###########################################
    # Handlers
    ###########################################
    def add_handler(self, address, handler):
        self.dispatcher.map(address, handler)
        
    def remove_handler(self, address):
        self.dispatcher.unmap(address)
    
    def generic_handler(self, address, *args):
        """Generic handler for all incoming OSC messages."""
        print(f"Received data at {address}: {args}")

        # Extract the type of data from the address
        stream_type = address.split('/')[-1]

        if stream_type in self.data and len(args) == 1:
            value = args[0]
            timestamp = self.get_current_iso_time()
            self.data[stream_type].append((timestamp, value))
            self.last_received[stream_type] = time.time()
        else:
            print(f"Unrecognized stream or invalid data format: {stream_type}")

        self.record_null_values()

    ###########################################
    # Getters 
    ###########################################
    @property
    def data(self):
        return self._data
    
    @property
    def baseline_data(self):
        if all(len(v) == 0 for v in self._baseline_data.values()):
            print("All baseline data arrays are empty")
            return {}
        else:
            return self._baseline_data

    @property   
    def ip(self):
        return self._ip
    
    @property
    def port(self):
        return self._port
    
    def get_biometric_baseline(self):
        self.set_biometric_baseline()
        return self.baseline_data
    
    ############################################
    # Deleters
    ############################################
    @data.deleter
    def data(self):
        for key in self._data.keys():
            self._data[key] = []

    @baseline_data.deleter
    def baseline_data(self):
        for key in self._baseline_data.keys():
            self._baseline_data[key] = []

    ############################################
    # Setters
    ############################################
    @data.setter
    def data(self, data):
        self._data = data
    
    @baseline_data.setter
    def baseline_data(self):
        self._baseline_data = copy.deepcopy(self._data)

    @ip.setter
    def ip(self, ip):
        self._ip = ip
    
    @port.setter
    def port(self, port):
        self._port = port

    def set_biometric_baseline(self):
        del self.baseline_data

        if all(len(v) == 0 for v in self.data.values()):
            print("No data to set as baseline.")
            return
        else:
            print("Setting baseline data...")
            self.baseline_data = self.data

        del self.data

        print("Baseline set and primary data cleared.")
