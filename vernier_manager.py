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
import asyncio
import logging
from timestamp_manager import TimestampManager
from threading import Thread
from collections import deque
import os
import csv
from datetime import datetime
import time
import h5py
import numpy as np
import scipy.signal as signal

class VernierManager:
    def __init__(self):
        self._device = None
        self._sensors = None
        self.timestamp_manager = TimestampManager()
        self._event_marker = "start_up"
        self._condition = 'None'
        self.hdf5_file = None
        self.hdf5_filename = None
        self.csv_filename = None
        self.data_folder = None
        self.thread = None
        self._running = False
        self._current_row = {"timestamp": None, "force": None, "event_marker": self._event_marker, "condition": self._condition}
        self._device_started = False

        # self._fs = 10
        # self._window_seconds = 30   
        # self._force_values = deque(maxlen=self._fs * self._window_seconds)

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
        asyncio.set_event_loop(asyncio.new_event_loop())
        self._godirect = GoDirect(use_ble=True, use_usb=True)
        print("GoDirect v"+str(self._godirect.get_version()))
        print("\nSearching...", flush=True, end ="")
        self._device = self._godirect.get_device(threshold=-100)

        if self._device != None and self._device.open(auto_start=False):
            self._device.start(period=100) 
            print("Connecting to Vernier device...")
            print("Connected to " + self._device.name)
            self._sensors = self._device.get_enabled_sensors()
            self._device_started = True

    # def calculate_respiratory_rate(self, force_values, fs=10, window_seconds=30):
    #     """
    #     Calculate the respiratory rate from force values.
    #     This function calculates the respiratory rate based on the provided force values.
    #     It uses peak detection to count the number of breaths within a specified window of time.
    #     Parameters:
    #         force_values (list or array-like): The force values from which to calculate the respiratory rate.
    #         fs (int, optional): The sampling frequency of the force values in Hz. Default is 10 Hz.
    #         window_seconds (int, optional): The time window in seconds over which to calculate the respiratory rate. Default is 30 seconds.
    #         NOTE: A moving average can be applied to the force values before peak detection to smooth the signal. This has been added and commented
    #         out for future use.
    #     Returns:
    #         float or None: The calculated respiratory rate in breaths per minute, or None if there are not enough data points.
    #     """
    #     if len(force_values) < fs * window_seconds:
    #         return None  
        
    #     force_array = np.array(force_values)

        # Apply a moving average to the force values
        # window_size = fs * 3 # 3-second window
        # baseline = np.convolve(force_array, np.ones(window_size)/window_size, mode='same')
        # Subtract baseline to normalize signal
        # corrected_signal = force_array - baseline

        # replace force_array with corrected_signal if moving average is applied
        # peaks, _ = signal.find_peaks(force_array, distance = fs/2)

        # num_breaths = len(peaks)
        # respiratory_rate = (num_breaths / window_seconds) * 60 

        # return respiratory_rate
    
    def collect_data(self):
        if not self.running:
            print("Go Direct device stopped.")
            return
        
        while self.running:
            if self._device.read():
                for sensor in self._sensors:
                    if sensor.sensor_description == "Force":
                        ts = self.timestamp_manager.get_timestamp("iso")
                        force_value = sensor.values[0] if sensor.values else None
                        # self._force_values.append(sensor.values[0])
                        # rr_values = self.calculate_respiratory_rate(self._force_values, self._fs, self._window_seconds)

                        if force_value is not None:
                            self._current_row["timestamp"] = ts
                            self._current_row["force"] = force_value
                            # self._current_row["RR"] = rr_values
                            self._current_row["event_marker"] = self.event_marker
                            self._current_row["condition"] = self.condition

                            self.write_to_hdf5(self._current_row)
                        else:
                            print("Error reading force sensor.")

                    sensor.clear()
            else:
                print("Error reading from sensor.")
                break

            time.sleep(.11)

    def run(self):
        if self.thread is None or not self.thread.is_alive():
            if self._device_started:
                self.running = True
                self.thread = Thread(target=self.collect_data, daemon=True)
                self.thread.start()
                print("Vernier manager running...")
            else:
                print("Device has not started yet.")
        else:
            print("Thread is already running.")
            
    def stop(self):
        try:
            if hasattr(self, 'thread') and self.thread.is_alive():
                self.running = False
                self.thread.join()
                print("Thread stopped.")

            if self._device_started:
                self._device.stop()
                self._device.close()
                self._device_started = False

                print("\nDisconnected from "+self._device.name)
                print("Quitting GoDirect...")
                self.quit()
                
                print("Closing HDF5 file...")
                self.close_h5_file()

        except Exception as e:
            print(f"An error occurred: {e}")

    def quit(self):
        self._godirect.quit()

    # def collect_baseline(self):
    #     if self._collecting_baseline:
    #         print("Already collecting baseline data.")
    #     else:
    #         self.event_marker = "respiratory_baseline"
    #         self._collecting_baseline = True

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
            # new_data[0]['RR'] = row.get('RR', np.nan)
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