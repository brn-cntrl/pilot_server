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
from datetime import datetime, timedelta
from collections import deque
from timestamp_manager import TimestampManager

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
        self.current_row = {key: None for key in ["timestamp", "EDA", "HR", "BI", "HRV", "PG", "RR", "event_marker"]}
        # self.last_received = {key: None for key in ["EDA", "HR", "BI", "HRV", "PG", "RR"]}
        self.data_window = {key: deque(maxlen=500) for key in ["BI", "PPG:GRN"]}  # Sliding window for derived metrics
        self.baseline_buffer = []
        self.data_buffer = deque(maxlen=8000)
        self._event_marker = 'startup'
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
        self.lock = threading.Lock()
        # Variables for h5 file
        self.hdf5_filename = None
        self.hdf5_file = None
        self.dataset = None
        self._baseline_collected = False
        self._processing_baseline = False
        self._time_started = None
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
    def baseline_collected(self) -> bool:
        return self._baseline_collected
    
    @baseline_collected.setter
    def baseline_collected(self, value: bool) -> None:
        self._baseline_collected = value

    @property
    def processing_baseline(self) -> bool:
        return self._processing_baseline
    
    @processing_baseline.setter
    def processing_baseline(self, value: bool) -> None:
        self._processing_baseline = value

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

    def set_data_folder(self, subject_folder):
        self.data_folder = os.path.join(subject_folder, "emotibit_data")
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
                    ('EDA', 'f4'),
                    ('HR', 'f4'),
                    ('BI', 'f4'),
                    ('HRV', 'f4'),
                    ('PG', 'f4'),
                    ('RR', 'f4'),
                    ('event_marker', h5py.string_dtype(encoding='utf-8'))
                ])
                self.dataset = self.hdf5_file.create_dataset(
                    'data', shape=(0,), maxshape=(None,), dtype=dtype
                )
            else:
                self.dataset = self.hdf5_file['data']  

            with h5py.File(self.hdf5_filename, "r") as f:
                if "data" in f:
                    dt = f["data"]
                else:
                    print("Dataset 'data' not found in the HDF5 file.")

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
        self.baseline_collected = True
        print("Stopping Baseline Collection... ")

    def start(self) -> None:
        if self.server_thread and self.server_thread.is_alive():
            print("Server is already running.")
            return

        self.time_started = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Debug statement
        print(f"Starting server at {self._ip}:{self._port}")

        self.shutdown_event.clear()

        self.csv_file = open(self.csv_filename, mode="w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(["timestamp", "EDA", "HR", "BI", "HRV", "PG", "RR", "baseline_status"])

        self.server_thread = Thread(target=self.server.serve_forever)
        self.server_thread.start()
        self.is_streaming = True
        
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

            self.is_streaming = False
            print("Server stopped successfully.")
        else:
            print("Server is not running.")

    ###########################################
    # Data Handlers
    ###########################################
    def generic_handler(self, address: str, *args) -> None:
        """Generic handler for all incoming OSC messages."""
        if not hasattr(self, 'current_timestamp') or self.current_timestamp != self.timestamp_manager.get_timestamp("iso"):
            self.current_timestamp = self.timestamp_manager.get_timestamp("iso")

        if not hasattr(self, 'current_row') or self.current_row["timestamp"] != self.current_timestamp:
            self.current_row = {key: None for key in ["timestamp", "EDA", "HR", "BI", "HRV", "PG", "RR", "event_marker"]}
        
        stream_type = address.split('/')[-1]
        timestamp = self.current_timestamp
        value = args[0]
        # self.last_received[stream_type] = time.time()
        # derived_value = None

        # DEBUG
        # print(self.event_marker)

        self.current_row["timestamp"] = timestamp
        self.current_row["event_marker"] = self.event_marker

        # if stream_type in self.data_window:
        #     if value is not None:
        #         self.data_window[stream_type].append(value)
                
        #         if stream_type == "BI" and len(self.data_window["BI"]) > 10:  
        #             derived_value = self.calculate_hrv()
        #             self.current_row['HRV'] = derived_value if derived_value is not None else None
        #             print(f"HRV: {derived_value}")
        #         elif stream_type == "PPG:GRN" and len(self.data_window["PPG:GRN"]) > 200:  
        #             derived_value = self.calculate_rr()
        #             self.current_row['RR'] = derived_value if derived_value is not None else None

        if stream_type == "EDA":
            self.current_row["EDA"] = value
        elif stream_type == "HR":
            self.current_row["HR"] = value
        elif stream_type == "BI":
            self.current_row["BI"] = value
        elif stream_type == "PPG:GRN":
            self.current_row["PG"] = value

        if any(self.current_row[key] is not None for key in ["EDA", "HR", "BI", "PG"]):
            if self.event_marker == "biometric_baseline" and not self.baseline_collected:
                self.baseline_buffer.append(self.current_row)
                # Debug
                # print(f"Baseline Buffer: {self.baseline_buffer[-1]}")
            elif self.event_marker != "startup" and self.event_marker != "biometric_baseline" and not self.processing_baseline:
                self.data_buffer.append(self.current_row)
                # Debug
                # print(f"Data Buffer: {self.data_buffer[-1]}")

            self.write_to_hdf5(self.current_row)

    ###########################################
    # Derived Metrics
    ###########################################
    def calculate_hrv(self) -> float:
        """Calculate HRV (RMSSD) from BI values."""
        bi_values = np.array(self.data_window["BI"])
        cleaned_bi_values = self.remove_outliers(bi_values)

        if len(cleaned_bi_values) < 50: # 50 beat interval values
            return None  

        differences = np.diff(bi_values) / 1000.0  
        rmssd = np.sqrt(np.mean(np.square(differences)))
        return rmssd
    
    def remove_outliers(self, bi_values, threshold=2.0):
        mean_bi = np.mean(bi_values)
        std_bi = np.std(bi_values)
        return [bi for bi in bi_values if abs(bi - mean_bi) < threshold * std_bi]

    def calculate_rr(self) -> float:
        """Calculate RR from PG values."""
        ppg_values = np.array(self.data_window["PPG:GRN"])
        if len(ppg_values) < 200:
            return None  

        # Bandpass filter
        filtered_signal = self.bandpass_filter(ppg_values, 0.1, 0.6, 12)  # Assuming 12 Hz sampling rate
        envelope = np.abs(hilbert(filtered_signal))

        # FFT for respiratory frequency
        fft_result = np.fft.rfft(envelope)
        freqs = np.fft.rfftfreq(len(envelope), 1 / 12)  # 12 Hz sampling rate
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
            if self.hdf5_file is None or self.dataset is None:
                print("HDF5 file or dataset is not initialized.")
                return

            new_data = np.zeros(1, dtype=self.dataset.dtype)  
            new_data[0]['timestamp'] = row.get('timestamp', '')  
            new_data[0]['EDA'] = row.get('EDA', np.nan)
            new_data[0]['HR'] = row.get('HR', np.nan)
            new_data[0]['BI'] = row.get('BI', np.nan)
            new_data[0]['HRV'] = row.get('HRV', np.nan)
            new_data[0]['PG'] = row.get('PG', np.nan)
            new_data[0]['RR'] = row.get('RR', np.nan)
            new_data[0]['event_marker'] = row.get('event_marker', '')

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

    def get_averages(self, stream_type) -> float:
        baseline_avgs = []
        test_avgs = []

        for obj in self.baseline_buffer:
            if obj['event_marker'] == 'biometric_baseline' and obj[stream_type] is not None:
                baseline_avgs.append(np.mean(obj[stream_type]))

        for obj in self.data_buffer:
            if obj['event_marker'] != 'biometric_baseline' and obj[stream_type] is not None:
                test_avgs.append(np.mean(obj[stream_type]))

        return(baseline_avgs, test_avgs)   
        
    def compare_baseline(self) -> dict:
        """
        Compare the averages of the baseline data with a specified window of live data.
        Returns a dictionary with the comparison results.
        """
        if not self.baseline_collected:
            print("Baseline not collected yet.")
            return {}
        
        comparisons = {}
        ppg_bl_avgs, ppg_tst_avgs = self.get_averages("PG")
        bi_bl_avgs, bi_tst_avgs = self.get_averages("BI")
        hr_bl_avgs, hr_tst_avgs = self.get_averages("HR")
        eda_bl_avgs, eda_tst_avgs = self.get_averages("EDA")

        def evaluate_elevation(baseline_list, test_list):
            """Compares baseline and test lists and determines elevation status."""
            if not baseline_list:
                return {"status": "No baseline data", "baseline_avg": None, "test_avg": np.mean(test_list) if test_list else None}
            if not test_list:
                return {"status": "No test data", "baseline_avg": np.mean(baseline_list), "test_avg": None}
            
            baseline_avg = np.mean(baseline_list)
            test_avg = np.mean(test_list)
            
            if test_avg > baseline_avg:
                status = "Elevated"
            elif test_avg < baseline_avg:
                status = "Lowered"
            else:
                status = "Equal"

            return {"status": status, "baseline_avg": baseline_avg, "test_avg": test_avg}
        
        comparisons["PG"] = evaluate_elevation(ppg_bl_avgs, ppg_tst_avgs)
        comparisons["BI"] = evaluate_elevation(bi_bl_avgs, bi_tst_avgs)
        comparisons["HR"] = evaluate_elevation(hr_bl_avgs, hr_tst_avgs)
        comparisons["EDA"] = evaluate_elevation(eda_bl_avgs, eda_tst_avgs)

        print("Comparison Results:", comparisons)  # Debugging Output
        return comparisons 

    # NOTE: If derived values are add to the h5 file as a second dataset, this method will need to be altered.
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