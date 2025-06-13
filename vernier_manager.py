""" When started, the class connects to a Go Direct device via USB (if USB 
is not connected, then it searches for the nearest GoDirect device via Bluetooth)
and starts reading measurements from the default sensor at a period of 
1000ms (1 sample/second). 

If you want to enable specific sensors, you will need to know the sensor numbers.
Run the example called 'gdx_getting_started_device_info.py' to get that information.

Installation of the godirect package is required using 'pip3 install godirect'
"""

from godirect import GoDirect
from gdx import gdx
import asyncio
import logging
from timestamp_manager import TimestampManager
from threading import Thread
from collections import deque
import os
import pandas as pd
from datetime import datetime, timezone
import time
import h5py
import numpy as np
import scipy.signal as signal
from bleak import BleakClient, BleakError

class VernierManager:
    def __init__(self):
        self._device = None
        self._sensors = None
        self.timestamp_manager = TimestampManager()
        self._event_marker = "start_up"
        self._condition = 'None'
        self._subject_id = None
        self.hdf5_file = None
        self.hdf5_filename = None
        self.csv_filename = None
        self.data_folder = None
        self.thread = None
        self._running = False
        self._streaming = False
        self._current_row = {"timestamp_unix": None, "timestamp": None, "force": None, "RR": None, "event_marker": self._event_marker, "condition": self._condition}
        self._device_started = False
        self._event_loop = None
        self._crashed = False
        self._num_crashes = 0
        self._godirect = None
        self._dataset = None
        self._file_opened = False

    @property
    def device_started(self):
        return self._device_started
    
    @device_started.setter
    def device_started(self, value):
        self._device_started = value

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

    def set_filenames(self, subject_id):
        self._subject_id = subject_id
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.hdf5_filename = os.path.join(self.data_folder, f"{current_date}_{subject_id}_respiratory_data_{self._num_crashes}.h5")
        self.csv_filename = os.path.join(self.data_folder, f"{current_date}_{subject_id}_respiratory_data_{self._num_crashes}.csv")

    def initialize_hdf5_file(self):
        # current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # current_date = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        # self.hdf5_filename = os.path.join(self.data_folder, f"{current_date}_{subject_id}_respiratory_data.h5")
        # self.csv_filename = os.path.join(self.data_folder, f"{current_date}_{subject_id}_respiratory_data.csv")

        try:
            if not self.hdf5_filename:
                print("HDF5 filename not set.")
                return

            if self._crashed:
                # Rename the file
                current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")  
                self.hdf5_filename = os.path.join(self.data_folder, f"{current_date}_{self._subject_id}_respiratory_data_{self._num_crashes}.h5")
                self.csv_filename = os.path.join(self.data_folder, f"{current_date}_{self._subject_id}_respiratory_data_{self._num_crashes}.csv")

            self.hdf5_file = h5py.File(self.hdf5_filename, 'a')  

            if 'data' not in self.hdf5_file:  
                dtype = np.dtype([
                    ('timestamp_unix', 'f8'),
                    ('timestamp', h5py.string_dtype(encoding='utf-8')),
                    ('force', 'f4'),
                    ('RR', 'f4'),
                    ('event_marker', h5py.string_dtype(encoding='utf-8')),
                    ('condition', h5py.string_dtype(encoding='utf-8'))
                ])
                self._dataset = self.hdf5_file.create_dataset(
                    'data', shape=(0,), maxshape=(None,), dtype=dtype
                )
            else:
                self._dataset = self.hdf5_file['data']  

            self._file_opened = True
            print("HDF5 file created for emotibit data: ", self.hdf5_filename)

        except Exception as e:
            print(f"Error initializing HDF5 file: {e}")

    def reset(self) -> None:
        # Immediately close the HDF5 file and convert it to CSV
        try:
            print("Reset is closing HDF5 file...")
            self.close_h5_file()
            self._file_opened = False

            try:
                print("Reset is converting HDF5 to CSV...")
                self.hdf5_to_csv()
            except Exception as inner_e:
                print(f"Error converting HDF5 to CSV: {inner_e}")
        except Exception as e:
            print(f"Error closing HDF5 file: {e}")
            
        # Quit the GoDirect instance and close the event loop
        try:
            if self._godirect is not None:
                self._godirect.quit()
                print("GoDirect has quit.")
            else:
                print("No GoDirect instance to quit.")
        except Exception as e:
            print(f"Error quitting GoDirect: {e}")

        try:
            if self._event_loop and not self._event_loop.is_closed():
                self._event_loop.close()
                print("Event loop closed.")
        except Exception as e:
            print(f"Error closing event loop: {e}")

        # Reset all variables except for _device_started, subject_id, and data_folder
        self._device_started = False
        self._event_loop = None
        self._device = None
        self._dataset = None
        self._sensors = None
        self._godirect = None
        self._current_row = {"timestamp_unix": None, "timestamp": None, "force": None, "RR": None, "event_marker": self._event_marker, "condition": self._condition}
        self._streaming = False
        self.running = False
        self.hdf5_file = None

    def start(self) -> str:
        try:
            loop = asyncio.get_event_loop()
            if hasattr(loop, "is_closed") and loop.is_closed():
                raise RuntimeError("Event loop is closed.")

        except RuntimeError as e:
            print(f"Error getting event loop: {e}")
            print("Creating a new event loop...")
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            except Exception as inner_e:
                print(f"Error creating new event loop: {inner_e}")
                return "Error"
            
        self._event_loop = loop
        
        try:
            self._godirect = GoDirect(use_ble=True, use_usb=True)
            print("GoDirect v"+str(self._godirect.get_version()))
            print("\nSearching...", flush=True, end ="")
            self._device = self._godirect.get_device(threshold=-100)

            if self._device != None and self._device.open(auto_start=False):
                sensor_list = self._device.list_sensors()
                print("Sensors found: "+ str(sensor_list))
                self._device.enable_sensors([1,2])
                self._device.start(period=100) 
                print("Connecting to Vernier device...")
                print("Connected to " + self._device.name)
                self._sensors = self._device.get_enabled_sensors()
                self._device_started = True

        except Exception as e:
            print(f"Error starting GoDirect device: {e}")
            self._device = None
            self._sensors = None
            self._device_started = False
            return "Error"

        return "Vernier device started."
    
    def collect_data(self):
        if not self.running:
            print("Go Direct device stopped.")
            return
        
        while self._streaming and self.running:
            try:
                if self._device.read():
                    ts = self.timestamp_manager.get_timestamp("iso")
                    tsu = self.timestamp_manager.get_timestamp("unix")
                    self._current_row["timestamp_unix"] = tsu
                    self._current_row["timestamp"] = ts
                    self._current_row["event_marker"] = self.event_marker
                    self._current_row["condition"] = self.condition

                    for sensor in self._sensors:
                        if sensor.sensor_description == "Force":
                            force_value = sensor.values[0] if sensor.values else None
                            if force_value is not None:
                                self._current_row["force"] = force_value
                            else:
                                print("Error reading force sensor.")

                        elif sensor.sensor_description == "Respiration Rate":
                            rr_value = sensor.values[0] if sensor.values else None

                            if rr_value is not None:
                                self._current_row["RR"] = rr_value
                            else:
                                print("Error reading respiration rate sensor.")

                        sensor.clear()

                    self.write_to_hdf5(self._current_row)

                else:
                    print("DEVICE HAS DISCONNECTED - RESTART VERNIER MANAGER.")
                    
                    # TODO close the hdf5 file and create csv file
                    self._crashed = True
                    self._num_crashes += 1
                    self.reset()
                    return
            
            except Exception as e:
                print(f"An error occurred: {e}")
                print("DEVICE HAS CRASHED - RESTART VERNIER MANAGER.")
                self._crashed = True
                self._num_crashes += 1
                self.reset()
                return

    def run(self):
        try:
            # Check if the thread exists and is alive
            # If it is, stop the existing thread
            if self.thread is not None and self.thread.is_alive():
                print("Stopping existing thread...")
                self.running = False
                self._streaming = False
                self.thread.join()
                print("Thread stopped.")
            
            # If the device has started, start a new thread
            if self._device_started:
                self.running = True
                self._streaming = True
                self.thread = Thread(target=self.collect_data, daemon=True)
                self.thread.start()
                print("Vernier manager running...")

            else:
                print("Device has not started yet.")

        except Exception as e:
            print(f"An error occurred while starting the thread: {e}")
                 
    def stop(self) -> str:
        try:
            self.running = False
            self._streaming = False
            print("Stopping Vernier manager...")
            if self._device_started:
                if self.thread is not None and self.thread.is_alive():
                    self.thread.join()
                    print("Thread stopped.")

                try:
                    self._device.stop()
                    self._device.close()

                except Exception as e:
                    print(f"Error stopping or closing device. Device is likely disconnected: {e}")

                try:
                    print("\nDisconnected from "+self._device.name)
                    print("Quitting GoDirect...")
                    self._godirect.quit()
                
                except Exception as e:
                    print(f"Error quitting GoDirect. Device already disconnected: {e}")

                if self._file_opened:
                    print("Stop is closing HDF5 file...")
                    self.close_h5_file()
                    print("Stop is converting HDF5 to CSV...")
                    self.hdf5_to_csv()
                
                self._device_started = False
                print("Vernier manager stopped.")
                return "Vernier manager stopped."
            else:
                print("Device has not started. If device has crashed or lost connection, please restart the manager.")
                return "Device has not started. If device has crashed or lost connection, please restart the manager."
                
        except Exception as e:
            print(f"An error occurred: {e}")
            return f"An error occurred: {e}"
        
    def _resize_dataset(self, new_size):
        """Resize the HDF5 dataset while ensuring thread synchronization."""
        try:
            current_size = self._dataset.shape[0]
            if new_size > current_size:
                self._dataset.resize(new_size, axis=0)

        except Exception as e:
            print(f"Error resizing dataset: {e}")

    def write_to_hdf5(self, row: dict) -> None:
        """Write the incoming dictionary to the HDF5 dataset as a single row."""
        try:
            if self.hdf5_file is None or self._dataset is None:
                print("HDF5 file or dataset is not initialized.")
                return

            new_data = np.zeros(1, dtype=self._dataset.dtype)  
            new_data[0]['timestamp_unix'] = row.get('timestamp_unix', np.nan)
            new_data[0]['timestamp'] = row.get('timestamp', '')  
            new_data[0]['force'] = row.get('force', np.nan)
            new_data[0]['RR'] = row.get('RR', np.nan)
            new_data[0]['event_marker'] = row.get('event_marker', '')
            new_data[0]['condition'] = row.get('condition', '')

            new_size = self._dataset.shape[0] + 1
            self._resize_dataset(new_size)  
            self._dataset[-1] = new_data[0]

        except Exception as e:
            print(f"Error writing to HDF5: {e}")

    def close_h5_file(self):
        if self.hdf5_file:
            self.hdf5_file.flush()
            self.hdf5_file.close()
            print(f"HDF5 file '{self.hdf5_filename}' closed.")
            return 
        else:
            print("HDF5 file is already closed or isn't initialized.")
            return  
        
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
            
            print("CSV file created successfully.")
            print(f"HDF5 file '{self.hdf5_filename}' successfully converted to CSV file '{self.csv_filename}'.")
            return 
        
        except FileNotFoundError:
            print(f"Error: The HDF5 file '{self.hdf5_filename}' was not found.")
            return 
        except Exception as e:
            print(f"Error converting HDF5 to CSV: {e}")
            return 