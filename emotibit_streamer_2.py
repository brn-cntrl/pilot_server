import csv
import h5py
import os
from pythonosc import dispatcher, osc_server
from threading import Thread, Event
import numpy as np
from scipy.signal import butter, filtfilt, hilbert
import time
import atexit
from datetime import datetime, timedelta
from collections import deque
from timestamp_manager import TimestampManager

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
        self.current_row = {key: None for key in ["timestamp", "EDA", "HR", "BI", "HRV", "PG", "RR", "event_marker"]}
        self.last_received = {key: None for key in ["EDA", "HR", "BI", "HRV", "PG", "RR"]}
        self.data_window = {key: deque(maxlen=500) for key in ["BI", "PG"]}  # Sliding window for derived metrics
        self._event_marker = 'subject_idle'
        self.collecting_baseline = False
        self.dispatcher = dispatcher.Dispatcher()
        self.dispatcher.map("/EmotiBit/0/*", self.generic_handler)
        self.server = osc_server.ThreadingOSCUDPServer((self._ip, self._port), self.dispatcher)
        self.server_thread = None
        self.shutdown_event = Event()
        self.default_value = 0
        self._data_folder = None
        self.csv_filename = None
        self.csv_writer = None

        # Variables for h5 file
        self.hdf5_filename = None
        self.hdf5_file = None
        self.dataset = None
            
        atexit.register(self.stop)
        print("Emotibit Initialized... ")
        print("EmotiBit data folder, .hdf5 and .csv files will be set when experiment/trial and subject information is submitted.")

    @property
    def data_folder(self) -> str:
        return self._data_folder
    
    @data_folder.setter
    def data_folder(self, data_folder: str) -> None:
        self._data_folder = data_folder
    
    @property 
    def event_marker(self) -> str:
        return self._event_marker

    @event_marker.setter
    def event_marker(self, value: str) -> None:
        self._event_marker = value

    def set_data_folder(self, experiment_name, trial_name, subject_folder):
        self.data_folder = os.path.join("subject_data", experiment_name, trial_name, subject_folder, "emotibit_data")
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)

        # DEBUG
        print("Data folder set for emotibit streamer: ", self.data_folder)

    def initialize_hdf5_file(self, subject_id):
        """
        Initializes the HDF5 file and dataset if not already created.
        Called once the test and subject information are both posted from the front end.
        """
        current_date = datetime.now().strftime("%Y-%m-%d")
        self.hdf5_filename = os.path.join(self.data_folder, f"{current_date}_{subject_id}_biometrics.h5")
        self.csv_filename = os.path.join(self.data_folder, f"{current_date}_{subject_id}_biometrics.csv")

        try:
            self.hdf5_file = h5py.File(self.hdf5_filename, 'a')  
            if 'data' not in self.hdf5_file:  
                dtype = np.dtype([
                    ('timestamp', h5py.string_dtype(encoding='utf-8')),
                    ('EDA', 'f8'),
                    ('HR', 'f8'),
                    ('BI', 'f8'),
                    ('HRV', 'f8'),
                    ('PG', 'f8'),
                    ('RR', 'f8'),
                    ('event_marker', h5py.string_dtype(encoding='utf-8'))
                ])
                self.dataset = self.hdf5_file.create_dataset(
                    'data', shape=(0,), maxshape=(None,), dtype=dtype
                )
            else:
                self.dataset = self.hdf5_file['data']  

            # DEBUG
            print("HDF5 file created for emotibit data: ", self.hdf5_filename)
            print("CSV file created for emotibit data: ", self.csv_filename)

        except Exception as e:
            print(f"Error initializing HDF5 file: {e}")

    def start_baseline_collection(self) -> None:
        if self.collecting_baseline:
            print("Already collecting baseline data.")
            return
        
        self.collecting_baseline = True
        print("Collecting EmotiBit Baseline... ")

    def stop_baseline_collection(self) -> None:
        if not self.collecting_baseline:
            print("Not currently collecting baseline data.")
            return
        
        self.collecting_baseline = False
        print("Stopping Baseline Collection... ")

    def start(self) -> None:
        if self.server_thread and self.server_thread.is_alive():
            print("Server is already running.")
            return

        # Debug statement
        print(f"Starting server at {self._ip}:{self._port}")

        self.shutdown_event.clear()

        self.csv_file = open(self.csv_filename, mode="w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(["timestamp", "EDA", "HR", "BI", "HRV", "PG", "RR", "baseline_status"])

        self.server_thread = Thread(target=self.server.serve_forever)
        self.server_thread.start()
        
    def stop(self) -> None:
        if self.server_thread:
            print(f"Stopping server at {self._ip}:{self._port}")
            self.shutdown_event.set()
            self.server.shutdown()
            self.server.server_close()
            self.server_thread.join()
            self.server_thread = None

            if self.hdf5_file:
                self.hdf5_file.close()

            print("Server stopped successfully.")
        else:
            print("Server is not running.")

    ###########################################
    # Data Handlers
    ###########################################
    def generic_handler(self, address: str, *args) -> None:
        """Generic handler for all incoming OSC messages."""

        # Debug statement
        print(f"Received data at {address}: {args}")

        if not hasattr(self, 'current_timestamp') or self.current_timestamp != self.timestamp_manager.get_timestamp("iso"):
            self.current_timestamp = self.timestamp_manager.get_timestamp("iso")

        if not hasattr(self, 'current_row') or self.current_row["timestamp"] != self.current_timestamp:
            self.current_row = {key: None for key in ["timestamp", "EDA", "HR", "BI", "HRV", "PG", "RR", "event_marker"]}
        
        stream_type = address.split('/')[-1]
        timestamp = self.current_timestamp
        value = args[0]
        self.last_received[stream_type] = time.time()
        derived_value = None

        self.current_row["timestamp"] = timestamp
        self.current_row["event_marker"] = self.event_marker

        if stream_type in self.data_window:
            self.data_window[stream_type].append(value)
            if stream_type == "BI" and len(self.data_window["BI"]) > 30:  
                derived_value = self.calculate_hrv()
                self.current_row['HRV'] = derived_value if derived_value is not None else None
            elif stream_type == "PG" and len(self.data_window["PG"]) > 100:  
                derived_value = self.calculate_rr()
                self.current_row['RR'] = derived_value if derived_value is not None else None

        if stream_type == "EDA":
            self.current_row["EDA"] = value
        elif stream_type == "HR":
            self.current_row["HR"] = value
        elif stream_type == "BI":
            self.current_row["BI"] = value
        elif stream_type == "PG":
            self.current_row["PG"] = value

        # self.write_to_csv(self.current_row)
        self.write_to_hdf5(self.current_row)

    ###########################################
    # Derived Metrics
    ###########################################
    def calculate_hrv(self) -> float:
        """Calculate HRV (RMSSD) from BI values."""
        bi_values = np.array(self.data_window["BI"])
        if len(bi_values) < 30: # 30 beat interval values
            return None  

        intervals = np.diff(bi_values) / 1000.0  
        rmssd = np.sqrt(np.mean(np.square(np.diff(intervals))))
        return rmssd

    def calculate_rr(self) -> float:
        """Calculate RR from PG values."""
        ppg_values = np.array(self.data_window["PG"])
        if len(ppg_values) < 100:
            return None  

        # Bandpass filter
        filtered_signal = self.bandpass_filter(ppg_values, 0.1, 0.5, 25)  # Assuming 25 Hz sampling rate
        envelope = np.abs(hilbert(filtered_signal))

        # FFT for respiratory frequency
        fft_result = np.fft.rfft(envelope)
        freqs = np.fft.rfftfreq(len(envelope), 1 / 25)  # 25 Hz sampling rate
        resp_freq = freqs[np.argmax(np.abs(fft_result))]
        return resp_freq * 60  # Convert to breaths per minute

    def bandpass_filter(self, data, lowcut, highcut, fs, order=4):
        #TODO CHECK COEFFICIENT VALUES
        nyquist = 0.5 * fs
        low = lowcut / nyquist
        high = highcut / nyquist
        b, a = butter(order, [low, high], btype="band")
        return filtfilt(b, a, data)

    ###########################################
    # Utility Methods
    ###########################################

    def write_to_hdf5(self, row: dict) -> None:
        """Write the incoming dictionary to the HDF5 dataset as a single row."""
        try:
            # Create a structured array for the new row
            new_data = np.zeros(1, dtype=self.dataset.dtype)  
            new_data[0]['timestamp'] = row.get('timestamp', '')  
            new_data[0]['EDA'] = row.get('EDA', np.nan)
            new_data[0]['HR'] = row.get('HR', np.nan)
            new_data[0]['BI'] = row.get('BI', np.nan)
            new_data[0]['HRV'] = row.get('HRV', np.nan)
            new_data[0]['PG'] = row.get('PG', np.nan)
            new_data[0]['RR'] = row.get('RR', np.nan)
            new_data[0]['event_marker'] = row.get('event_marker', '')

            current_size = self.dataset.shape[0]
            self.dataset.resize((current_size + 1,))  

            self.dataset[current_size] = new_data[0]  

        except Exception as e:
            print(f"Error writing to HDF5: {e}")

    def get_baseline_entries(self) -> list:
        """Check the HDF5 file for rows with 'baseline' under 'baseline_status' and return as a list of dictionaries."""
        baseline_entries = []

        try:
            with h5py.File(self.hdf5_filename, 'r') as f:
                dataset = f['data']

                event_marker = dataset['event_marker'].asstr()
                baseline_status = np.where(event_marker == 'baseline')[0]
                
                for idx in baseline_status:
                    entry = {
                        field: dataset[field][idx].decode('utf-8') if dataset[field].dtype.kind == 'S' else dataset[field][idx]
                        for field in dataset.dtype.names
                    }

                    baseline_entries.append(entry)

            return baseline_entries

        except FileNotFoundError:
            print(f"Error: The file {self.h5_filename} was not found.")
            return []
        except Exception as e:
            print(f"Error reading the HDF5 file: {e}")
            return []

    def get_live_entries(self, lookback_minutes: int = 2) -> list:
        """Retrieve non-baseline entries (live data) from the last 'lookback_minutes' minutes.

        Args:
            lookback_minutes (int): The number of minutes to look back for live data.
        
        Returns:
            list: A list of dictionaries containing live data from the HDF5 file.
        """
        non_baseline_entries = []

        try:
            # Open the HDF5 file
            with h5py.File(self.hdf5_filename, 'r') as f:
                dataset = f['data']
                
                current_time = datetime.now()
                time_threshold = current_time - timedelta(minutes=lookback_minutes)
                
                for idx in range(dataset.shape[0]):
                    event_marker = dataset['event_marker'][idx].decode('utf-8')  
                    timestamp = dataset['timestamp'][idx].decode('utf-8')  
                    
                    if event_marker != 'baseline' and timestamp:
                        row_time = datetime.fromisoformat(timestamp)  
                        if row_time >= time_threshold and row_time <= current_time:
                            entry = {
                                        field: dataset[field][idx] if dataset[field].dtype.kind != 'S' 
                                        else dataset[field][idx].decode('utf-8') 
                                        for field in dataset.dtype.names
                                    }
                            non_baseline_entries.append(entry)

            return non_baseline_entries

        except FileNotFoundError:
            print(f"Error: The file {self.hdf5_filename} was not found.")
            return []


    def get_averages(self, data) -> dict:
        """
        Calculate the averages of the given data.
        Args:
            data (list): A list of dictionaries containing data to calculate averages from.

        Returns:
            dict: A dictionary containing the averages of the given data.
        """
        averages = {}
        for entry in data:
            for key in ["EDA", "HR", "BI", "HRV", "PG", "RR"]:
                if key not in averages:
                    averages[key] = []
                if entry.get(key) not in [None, 'N/A']:
                    averages[key].append(float(entry.get(key)))
        
        averages = {key: sum(values) / len(values) if values else None for key, values in averages.items()}
        return averages
    
    def compare_baseline(self) -> dict:
        """
        Compare the averages of the baseline data with a specified window of live data
        from the CSV file. If there is not enough data, return a message indicating so.

        Returns:
            dict or str: A dictionary with comparison results or a string message if
                         not enough data has been collected.
        """
        live_data = self.get_live_entries()
        baseline_data = self.get_baseline_entries()

        baseline_averages = self.get_averages(baseline_data)
        live_averages = self.get_averages(live_data)

        comparison_results = {}
        for key in ["EDA", "HR", "BI", "HRV", "PG", "RR"]:
            baseline_avg = baseline_averages.get(key)
            live_avg = live_averages.get(key)
            
            # Calculate the difference and check if the non-baseline average is elevated
            if baseline_avg is not None and live_avg is not None:
                if live_avg > baseline_avg:
                    higher = "Live data"
                elif live_avg < baseline_avg:
                    higher = "Baseline data"
                else:
                    higher = "Equal"
            else:
                higher = None
            
            comparison_results[key] = {
                "baseline_avg": baseline_avg,
                "live_avg": live_avg,
                "elevated": higher
            }
    
        return comparison_results

    def hdf5_to_csv(self) -> None:
        """
        Convert an HDF5 file to a CSV file.

        Dependencies:
            h5_filename (str): The path to the HDF5 file.
            csv_filename (str): The path to the CSV file to be created.
        """
        try:
            # Open the HDF5 file in read mode
            with h5py.File(self.hdf5_filename, 'r') as h5_file:
                # Check if the 'data' dataset exists
                if 'data' not in h5_file:
                    print(f"Dataset 'data' not found in the file {self.hdf5_filename}.")
                    return
                
                dataset = h5_file['data']
                
                # Get the field names (column names) from the dataset
                field_names = dataset.dtype.names
                
                # Open the CSV file for writing
                with open(self.csv_filename, 'w', newline='', encoding='utf-8') as csv_file:
                    writer = csv.DictWriter(csv_file, fieldnames=field_names)
                    
                    writer.writeheader()
                    
                    for idx in range(dataset.shape[0]):
                        row = {
                            field: dataset[field][idx].decode('utf-8') if dataset[field].dtype.kind == 'S' 
                                else dataset[field][idx]
                            for field in field_names
                        }
                        writer.writerow(row)
            
            print(f"HDF5 file '{self.hdf5_filename}' successfully converted to CSV file '{self.csv_filename}'.")

        except FileNotFoundError:
            print(f"Error: The HDF5 file '{self.hdf5_filename}' was not found.")
        except Exception as e:
            print(f"Error converting HDF5 to CSV: {e}")
