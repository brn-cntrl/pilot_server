import csv
import h5py
import os
from pythonosc import dispatcher, osc_server
from threading import Thread, Event
import threading
import numpy as np
from scipy.signal import butter, filtfilt, hilbert
import time
import atexit
from datetime import datetime, timezone, timedelta
from collections import deque
from timestamp_manager import TimestampManager
import pandas as pd

# TODO: Look into Neurokit 2 and EmotiBit tools for analysis
"""
This class manages the OSC server that receives data from the EmotiBit.
All OSC addresses must be included in the oscOutputSettings.xml file. Some
settings may not be present in the file, but the addresses can be included.
A full list of type tags can be found here: 
https://github.com/EmotiBit/EmotiBit_Docs/blob/master/Working_with_emotibit_data.md/#EmotiBit-data-types
"""
class EmotiBitStreamer:
    def __init__(self, port: int) -> None:
        self._ip = "127.0.0.1"
        self._port = port
        self.timestamp_manager = TimestampManager()
        self.is_streaming = False
        self.current_row = {key: None for key in ["timestamp_unix", "timestamp", "EDA", "HR", "BI", "HRV", "PG", "RR", "event_marker", "condition"]}
        self.data_buffer = deque(maxlen=3000)
        self._event_marker = 'startup'
        self._condition = 'None'
        self.dispatcher = dispatcher.Dispatcher()
        self.dispatcher.map("/EmotiBit/0/*", self.generic_handler)
        self.server = osc_server.ThreadingOSCUDPServer((self._ip, self._port), self.dispatcher)
        self.server_thread = None
        self.shutdown_event = Event()
        self.default_value = 0
        self._data_folder = None
        self.csv_filename = None
        self.csv_writer = None
        self.lock = threading.Lock()
        self.hdf5_filename = None
        self.hdf5_file = None
        self.dataset = None
        self._time_started = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        atexit.register(self.stop)
        print("Emotibit Initialized... ")
        print("EmotiBit data folder, .hdf5 and .csv files will be set when experiment/trial and subject information is submitted.")

    @property
    def time_started(self):
        return self._time_started
    
    @time_started.setter
    def time_started(self, value):
        self._time_started = value

    @property
    def data_folder(self) -> str:
        return self._data_folder
    
    @data_folder.setter
    def data_folder(self, data_folder: str) -> None:
        self._data_folder = data_folder
    
    @property
    def condition(self) -> str:
        return self._condition
    
    @condition.setter
    def condition(self, value: str) -> None:
        self._condition = value

    @property 
    def event_marker(self) -> str:
        return self._event_marker

    @event_marker.setter
    def event_marker(self, value: str) -> None:
        self._event_marker = value

    def set_data_folder(self, subject_folder):
        self.data_folder = os.path.join(subject_folder, "emotibit_data")
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)

        # DEBUG
        print("Data folder set for emotibit streamer: ", self.data_folder)

    def set_filenames(self, subject_id):
        if self.data_folder is None:
            raise ValueError("Data folder must be set before setting filenames.")
        
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.hdf5_filename = os.path.join(self.data_folder, f"{current_date}_{subject_id}_biometrics.h5")
        self.csv_filename = os.path.join(self.data_folder, f"{current_date}_{subject_id}_biometrics.csv")

    def initialize_hdf5_file(self):
        """
        Initializes the HDF5 file and dataset if not already created.
        Called once the test and subject information are both posted from the front end.
        """
        try:
            self.hdf5_file = h5py.File(self.hdf5_filename, 'a')  
            if 'data' not in self.hdf5_file:  
                dtype = np.dtype([
                    ('timestamp_unix', 'f8'),  # Unix timestamp in milliseconds
                    ('timestamp', h5py.string_dtype(encoding='utf-8')),
                    ('EDA', 'f4'),
                    ('HR', 'f4'),
                    ('BI', 'f4'),
                    ('PG', 'f4'),
                    ('event_marker', h5py.string_dtype(encoding='utf-8')),
                    ('condition', h5py.string_dtype(encoding='utf-8'))
                ])
                self.dataset = self.hdf5_file.create_dataset(
                    'data', shape=(0,), maxshape=(None,), dtype=dtype
                )
            else:
                self.dataset = self.hdf5_file['data']  

            if "data" in self.hdf5_file:
                print("Dataset 'data' found in the HDF5 file.")
            else:
                print("Dataset 'data' not found in the HDF5 file.")

            # DEBUG
            print("HDF5 file created for emotibit data: ", self.hdf5_filename)
            print("CSV file created for emotibit data: ", self.csv_filename)

        except Exception as e:
            print(f"Error initializing HDF5 file: {e}")

    def start(self) -> None:
        if self.server_thread and self.server_thread.is_alive():
            print("Server is already running.")
            return

        self.time_started = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Debug statement
        print(f"Starting server at {self._ip}:{self._port}")

        self.shutdown_event.clear()

        self.server_thread = Thread(target=self.server.serve_forever)
        self.server_thread.start()
        self.is_streaming = True

    def close_h5_file(self):
        if self.hdf5_file:
            self.hdf5_file.flush()
            self.hdf5_file.close()
            self.hdf5_file = None  
            self.dataset = None    

            return "HDF5 file closed."
        else:
            return "No HDF5 file to close."

    def stop(self) -> None:
        if self.server_thread:
            print(f"Stopping server at {self._ip}:{self._port}")
            self.shutdown_event.set()
            self.server.shutdown()
            self.server.server_close()
            self.server_thread.join(timeout=3.0)
            self.server_thread = None
            self.is_streaming = False
            print("EmotiBit OSC server stopped successfully.")
            print("Closing EmotiBit H5 file...")

            with self.lock:  # Ensure thread-safe access to the HDF5 file
                self.close_h5_file()
                print("EmotiBit H5 file closed.")

            print("Converting EmotiBit H5 to CSV...")
            self.hdf5_to_csv()
            print("EmotiBit H5 file converted to CSV.")
            
        else:
            print("Server is not running.")

    ###########################################
    # Data Handlers
    ###########################################
    def generic_handler(self, address: str, *args) -> None:
        """Generic handler for all incoming OSC messages."""
        if not self.is_streaming:
            # Bail out if stopping
            print("EmotiBitStreamer is not currently streaming. Please start the server first.")
            return
        
        if not hasattr(self, 'current_timestamp') or self.current_timestamp != self.timestamp_manager.get_timestamp("iso"):
            self.current_timestamp = self.timestamp_manager.get_timestamp("iso")

        if not hasattr(self, 'timestamp_unix') or self.timestamp_unix != self.timestamp_manager.get_timestamp("unix"):
            self.timestamp_unix = self.timestamp_manager.get_timestamp('unix')

        if not hasattr(self, 'current_row') or self.current_row["timestamp"] != self.current_timestamp:
            self.current_row = {key: None for key in ["timestamp_unix", "timestamp", "EDA", "HR", "BI", "PG", "event_marker", "condition"]}
        
        stream_type = address.split('/')[-1]
        timestamp = self.current_timestamp
        timestamp_unix = self.timestamp_unix
        value = args[0]
        self.current_row["timestamp_unix"] = timestamp_unix
        self.current_row["timestamp"] = timestamp
        self.current_row["event_marker"] = self.event_marker
        self.current_row["condition"] = self.condition

        if stream_type == "EDA":
            self.current_row["EDA"] = value
        elif stream_type == "HR":
            self.current_row["HR"] = value
        elif stream_type == "BI":
            self.current_row["BI"] = value
        elif stream_type == "PPG:GRN":
            self.current_row["PG"] = value

        if any(self.current_row[key] is not None for key in ["EDA", "HR", "BI", "PG"]):
            self.write_to_hdf5(self.current_row)

    ###########################################
    # Utility Methods
    ###########################################

    def write_to_hdf5(self, row: dict) -> None:
        """Write the incoming dictionary to the HDF5 dataset as a single row."""
        with self.lock:  # Ensure thread-safe access to the dataset
            try:
                if self.hdf5_file is None or self.dataset is None:
                    print("HDF5 file or dataset is not initialized.")
                    return

                new_data = np.zeros(1, dtype=self.dataset.dtype)  
                new_data[0]['timestamp_unix'] = row.get('timestamp_unix', '')
                new_data[0]['timestamp'] = row.get('timestamp', '')  
                new_data[0]['EDA'] = row.get('EDA', np.nan)
                new_data[0]['HR'] = row.get('HR', np.nan)
                new_data[0]['BI'] = row.get('BI', np.nan)
                new_data[0]['PG'] = row.get('PG', np.nan)
                new_data[0]['event_marker'] = row.get('event_marker', '')
                new_data[0]['condition'] = row.get('condition', '')

                new_size = self.dataset.shape[0] + 1
                self._resize_dataset(new_size)  
                self.dataset[-1] = new_data[0]

            except Exception as e:
                print(f"Error writing to HDF5: {e}")

    def _resize_dataset(self, new_size):
        """Resize the HDF5 dataset while ensuring thread synchronization."""
        try:
            current_size = self.dataset.shape[0]
            if new_size > current_size:
                self.dataset.resize(new_size, axis=0)

        except Exception as e:
            print(f"Error resizing dataset: {e}")

    def hdf5_to_csv(self):
        """
        Convert an HDF5 file to a CSV file.
        Dependencies:
            h5_filename (str): The path to the HDF5 file.
            csv_filename (str): The path to the CSV file to be created.
        """
        try:
            chunk_size = 1000
            with h5py.File(self.hdf5_filename, 'r') as h5_file:
                if 'data' not in h5_file:
                    print(f"Dataset 'data' not found in the file {self.hdf5_filename}.")
                    return
                
                dataset = h5_file['data']
                field_names = dataset.dtype.names
                first_chunk = True

                for start in range(0, dataset.shape[0], chunk_size):
                    end = min(start + chunk_size, dataset.shape[0])
                    chunk = dataset[start:end]

                    chunk_dict = {
                        field: np.char.decode(chunk[field], 'utf-8') if chunk[field].dtype.kind == 'S' 
                            else [x.decode('utf-8') if isinstance(x, bytes) else x for x in chunk[field]]
                        for field in field_names
                    }

                    chunk_df = pd.DataFrame(chunk_dict)

                    if first_chunk:
                        chunk_df.to_csv(self.csv_filename, mode='w', index=False, header=True)
                        first_chunk = False
                    else:
                        chunk_df.to_csv(self.csv_filename, mode='a', header=False, index=False)
            
            print(f"HDF5 file '{self.hdf5_filename}' successfully converted to CSV file '{self.csv_filename}'.")
        
        except FileNotFoundError:
            print(f"Error: The HDF5 file '{self.hdf5_filename}' was not found.")
            
        except Exception as e:
            print(f"Error converting HDF5 to CSV: {e}")