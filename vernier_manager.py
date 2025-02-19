""" This example automatically connects to a Go Direct device via USB (if USB 
is not connected, then it searches for the nearest GoDirect device via Bluetooth)
and starts reading measurements from the default sensor at a period of 
1000ms (1 sample/second). Unlike the 'gdx_getting_started' examples that use the gdx module,
this example works directly with the godirect module. This example might
be important for troubleshooting, or if you do not want to use the gdx module.

If you want to enable specific sensors, you will need to know the sensor numbers.
Run the example called 'gdx_getting_started_device_info.py' to get that information.

Installation of the godirect package is required using 'pip3 install godirect'
"""

from godirect import GoDirect
import logging
from timestamp_manager import TimestampManager
from threading import Thread
from collections import deque
import os
import csv
import datetime
import time
import h5py
import numpy as np

class VernierManager:
    def __init__(self):
        self._device = None
        self._sensors = None
        self.timestamp_manager = TimestampManager()
        self._data_window = deque(maxlen=30)
        self._collecting_baseline = False
        self._baseline_data = []
        self._event_marker = "start_up"
        self._condition = 'None'
        self.hdf5_file = None
        self.hdf5_filename = None
        self.csv_filename = None
        self.data_folder = None
        self.thread = None
        self._running = False
        self._current_row = {"timestamp": None, "force": None, "RR": None, "event_marker": self._event_marker, "condition": self._condition}
        self._device_started = False

    @property 
    def running(self):
        return self._running
    
    @running.setter
    def running(self, value):
        self._running = value

    @property
    def event_marker(self):
        return self._event_marker
    
    @event_marker.setter
    def event_marker(self, value):
        self._event_marker = value

    @property
    def condition(self):
        return self._condition
    
    @condition.setter
    def condition(self, value):
        self._condition = value

    def set_data_folder(self, subject_folder):
        self.data_folder = os.path.join(subject_folder, "respiratory_data")
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)

    def initialize_hdf5_file(self, subject_id):
        current_date = datetime.now().strftime("%Y-%m-%d")
        self.hdf5_filename = os.path.join(self.data_folder, f"{current_date}_{subject_id}_respiratory_data.h5")
        self.csv_filename = os.path.join(self.data_folder, f"{current_date}_{subject_id}_respiratory_data.csv")

        try:
            self.hdf5_file = h5py.File(self.hdf5_filename, 'a')  
            if 'data' not in self.hdf5_file:  
                dtype = np.dtype([
                    ('timestamp', h5py.string_dtype(encoding='utf-8')),
                    ('force', 'f4'),
                    ('RR', 'f4'),
                    ('event_marker', h5py.string_dtype(encoding='utf-8')),
                    ('condition', h5py.string_dtype(encoding='utf-8'))
                ])
                self.dataset = self.hdf5_file.create_dataset(
                    'data', shape=(0,), maxshape=(None,), dtype=dtype
                )
            else:
                self.dataset = self.hdf5_file['data']  

            print("HDF5 file created for emotibit data: ", self.hdf5_filename)

        except Exception as e:
            print(f"Error initializing HDF5 file: {e}")

    def start(self):
        self._godirect = GoDirect(use_ble=True, use_usb=True)
        print("GoDirect v"+str(self._godirect.get_version()))
        print("\nSearching...", flush=True, end ="")
        self._device = self._godirect.get_device(threshold=-100)

        if self._device != None and self._device.open(auto_start=False):
            self._device.start(period=1000) 
            print("Connecting to Vernier device...")
            print("Connected to "+self._device.name)
            self._sensors = self._device.get_enabled_sensors()
            self._device_started = True

    def collect_data(self):
        if not self.running:
            print("Go Direct device not started.")
            return
        
        while self.running:
            if self._device.read():
                for sensor in self._sensors:
                    if sensor.sensor_description == "Force":
                        ts = self.timestamp_manager.get_timestamp("iso")
                        self._data_window.append(sensor.values[0])
                        
                        if len(self._data_window) == self._data_window.maxlen:
                            # Perform RR calculation and add to the current row
                            pass

                        self._current_row["timestamp"] = ts
                        self._current_row["force"] = sensor.values[0]
                        self._current_row["RR"] = None 
                        self._current_row["event_marker"] = self.event_marker
                        self._current_row["condition"] = self.condition
                        
                        # TODO: Add RR calculation

                        if self._collecting_baseline:
                            self._baseline_data.append(self._current_row)
                            sensor.clear()
                        else:
                            self._data_window.append(sensor.values[0])
                        # TODO: Add functionality for writing to h5 and calculating RR
                    
            time.sleep(1)

    def run(self):
        if not hasattr(self, 'thread') or not self.thread.is_alive():
            if self._device_started:
                self.thread = Thread(target=self.collect_data, daemon=True)
                self.thread.start()
                self.running = True
        else:
            print("Thread is already running.")
            
    def stop(self):
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join()
            print("Thread stopped.")

        self._device.stop()
        self._device.close()
        self.running = False
        self._device_started = False
        print("\nDisconnected from "+self._device.name)   

    def quit(self):
        self._godirect.quit()

    def collect_baseline(self):
        if self._collecting_baseline:
            print("Already collecting baseline data.")
        else:
            self.event_marker = "respiratory_baseline"
            self._collecting_baseline = True

    def _resize_dataset(self, new_size):
        """Resize the HDF5 dataset while ensuring thread synchronization."""
        try:
            current_size = self.dataset.shape[0]
            if new_size > current_size:
                self.dataset.resize(new_size, axis=0)

        except Exception as e:
            print(f"Error resizing dataset: {e}")

    def write_to_hdf5(self, row: dict) -> None:
        """Write the incoming dictionary to the HDF5 dataset as a single row."""
        try:
            if self.hdf5_file is None or self.dataset is None:
                print("HDF5 file or dataset is not initialized.")
                return

            new_data = np.zeros(1, dtype=self.dataset.dtype)  
            new_data[0]['timestamp'] = row.get('timestamp', '')  
            new_data[0]['force'] = row.get('force', np.nan)
            new_data[0]['RR'] = row.get('RR', np.nan)
            new_data[0]['event_marker'] = row.get('event_marker', '')
            new_data[0]['condition'] = row.get('condition', '')

            new_size = self.dataset.shape[0] + 1
            self._resize_dataset(new_size)  
            self.dataset[-1] = new_data[0]

        except Exception as e:
            print(f"Error writing to HDF5: {e}")

    def close_h5_file(self):
        if self.hdf5_file:
            self.hdf5_file.flush()
            self.hdf5_file.close()
            return "HDF5 file closed."
        else:
            return "No HDF5 file to close."  