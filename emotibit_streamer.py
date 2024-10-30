from pythonosc import dispatcher, osc_server
from threading import Thread, Event
import socket
import numpy as np
import atexit
import time
"""
This class manages the OSC server that receives data from the EmotiBit.
All OSC addresses must be included in the oscOutputSettings.xml file. Some
settings may not be present in the file, but the addresses can be included.
A full list of type tags can be found here: 
https://github.com/EmotiBit/EmotiBit_Docs/blob/master/Working_with_emotibit_data.md/#EmotiBit-data-types

"""
class EmotiBitStreamer:
    def __init__(self, port):
        self.ip = "127.0.0.1"
        self.port = port
        print(self.port)
        self.data = {
             "EDA": [],
            "HR": [],
            "BI": []
        }
        
        self.baseline_data = {
            "EDA": [],
            "HR": [],
            "BI": []
        }

        self.dispatcher = dispatcher.Dispatcher()
        self.dispatcher.map("/EmotiBit/0/EDA", self.generic_handler, "EDA")
        self.dispatcher.map("/EmotiBit/0/BI", self.generic_handler, "BI")
        self.dispatcher.map("/EmotiBit/0/HR", self.generic_handler, "HR")
        self.server_thread = None
        self.shutdown_event = Event()
        self.server = osc_server.ThreadingOSCUDPServer((self.ip, self.port), self.dispatcher)
        self.server.allow_reuse_address = True  # Call this before binding
        self.server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Corrected to SO_REUSEADDR
        atexit.register(self.stop)

        print(f"IP: {self.ip}, Port: {self.port}")
    ###########################################
    # Methods
    ###########################################
    def start(self):
        # if self.server:
        #     print("Server is already running.")
        #     return
        
        # print(f"Starting server at {self.ip}:{self.port}")
        # self.server.serve_forever()
        if self.server_thread is not None and self.server_thread.is_alive():
            print("Server is already running.")
            return
        
        print(f"Starting server at {self.ip}:{self.port}")
        
        # Start the server in a new thread
        self.shutdown_event.clear()  # Clear the shutdown event before starting
        self.server_thread = Thread(target=self.server.serve_forever)
        self.server_thread.start()
        
    def stop(self):
        # if self.server:
        #     print(f"Stopping server at {self.ip}:{self.port}")
        #     self.server.shutdown()
        #     time.sleep(1)  # Wait for the server to stop    
        #     self.server.server_close()
        #     self.server = None  # Reset to allow future start
        #     print("Server stopped successfully.")
        # else:
        #     print("Server was not running.")
        if self.server_thread is not None:
            print(f"Stopping server at {self.ip}:{self.port}")
            self.shutdown_event.set()  # Signal the server to stop
            self.server.shutdown()  # Shutdown the server
            self.server.server_close()  # Close the server socket
            self.server_thread.join()  # Wait for the server thread to finish
            self.server_thread = None  # Reset the server thread
            print("Server stopped successfully.")
        else:
            print("OSC Server was not running.")

    # def run_server(self):
    #     """ Run the OSC server until shutdown is signaled. """
    #     while not self.shutdown_event.is_set():
    #         self.server.handle_request()  # Handle a single request

    def clear_data(self):
        self.data = {
            "EDA": [],
            "HR": [],
            "BI": []
        }

        self.eda_data = []
        self.temp_data = []
        self.hr_data = []

    def calculate_hrv_from_bi(self, bi_values):
        # HRV metrics directly from BI (beat interval) values
        sdnn = np.std(bi_values)
        rmssd = np.sqrt(np.mean(np.square(np.diff(bi_values))))
        return {"SDNN": sdnn, "RMSSD": rmssd}
    
    def calculate_hrv_from_hr(self, hr_values):
        # Convert HR to IBI
        ibi_values = 60000 / np.array(hr_values)  # Converts HR (bpm) to IBI (ms)
        return self.calculate_hrv_from_bi(ibi_values)  # Use BI-based HRV calculation
    
    ###########################################
    # Handlers
    ###########################################
    def add_handler(self, address, handler):
        self.dispatcher.map(address, handler)
        
    def remove_handler(self, address):
        self.dispatcher.unmap(address)
    
    def generic_handler(self, address, stream_name, *args):
            if stream_name in self.data:
                self.data[stream_name].append(args)
            else:
                print(f"Stream name {stream_name} not found in data")

    ###########################################
    # Getters
    ###########################################
    def get_data(self):
        return self.data
    
    def get_baseline_data(self):
        if all(len(v) == 0 for v in self.baseline_data.values()):
            print("All baseline data arrays are empty")
            return {}
        else:
            return self.baseline_data
    
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
        
    def get_ip(self):
        return self.ip
    
    def get_port(self):
        return self.port
    
    ############################################
    # Setters
    ############################################
    def set_emotibit_baseline(self):
        # Clear the baseline data file first
        self.baseline_data = {
            "EDA": [],
            "HR": [],
            "BI": []
        }

        self.baseline_data = self.data.copy()

        # Clear the data after setting the baseline
        self.clear_data()
        print("Baseline set and primary data cleared.")