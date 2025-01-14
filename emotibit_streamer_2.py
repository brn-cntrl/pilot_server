import csv
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
    def __init__(self, port: int, csv_filename: str = "tmp.csv") -> None:
        self._ip = "127.0.0.1"
        self._port = port
        self.csv_filename = csv_filename
        self.timestamp_manager = TimestampManager()
        self.is_streaming = False
        self.current_row = {key: None for key in ["timestamp", "EDA", "HR", "BI", "HRV", "PG", "RR"]}
        self._baseline_data = {key: [] for key in ["EDA", "HR", "BI", "HRV", "PG", "RR"]}
        self.last_received = {key: None for key in self._baseline_data.keys()}
        self.data_window = {key: deque(maxlen=500) for key in ["BI", "PG"]}  # For derived metrics

        self.collecting_baseline = False

        self.dispatcher = dispatcher.Dispatcher()
        self.dispatcher.map("/EmotiBit/0/*", self.generic_handler)

        self.server = osc_server.ThreadingOSCUDPServer((self._ip, self._port), self.dispatcher)
        self.server_thread = None
        self.shutdown_event = Event()

        self.last_received = {key: time.time() for key in self.data.keys()}
        self.null_record_interval = 5  
        self.default_value = 0

        self.csv_file = None
        self.csv_writer = None

        atexit.register(self.stop)

    def start_baseline_collection(self) -> None:
        self.collecting_baseline = True

        # Reset the baseline values
        self._baseline_data = {key: [] for key in self._baseline_data.keys()}

    def stop_baseline_collection(self) -> None:
        if not self.collecting_baseline:
            print("Not currently collecting baseline data.")
            return
        
        self.collecting_baseline = False

        for stream_type, values in self._baseline_data.items():
            for value in values:
                self.write_to_csv(self.get_current_iso_time(), f"baseline_{stream_type}", value, None)

    def start(self) -> None:
        if self.server_thread and self.server_thread.is_alive():
            print("Server is already running.")
            return

        # Debug statement
        print(f"Starting server at {self._ip}:{self._port}")

        self.shutdown_event.clear()

        self.csv_file = open(self.csv_filename, mode="w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(["timestamp", "EDA", "HR", "BI", "HRV", "PG", "RR"])

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

            # Close CSV file
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None

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

        stream_type = address.split('/')[-1]
        if stream_type not in self._baseline_data:
            print(f"Unrecognized stream or invalid data format: {stream_type}")
            return

        self.timestamp_manager.update_timestamp()
        timestamp = self.timestamp_manager.get_iso_timestamp()

        value = args[0]
        self.last_received[stream_type] = time.time()

        derived_value = None

        if self.collecting_baseline:
            self._baseline_data[stream_type].append(value)

            if stream_type == "BI":
                derived_value = self.calculate_hrv()
                if derived_value is not None:
                    self._baseline_data["HRV"].append(derived_value)

            elif stream_type == "PG":
                derived_value = self.calculate_rr()
                if derived_value is not None:
                    self._baseline_data["RR"].append(derived_value)

        else:
            if stream_type in self.data_window:
                self.data_window[stream_type].append(value)

                if stream_type == "BI" and len(self.data_window["BI"]) > 30:  
                    derived_value = self.calculate_hrv()
                elif stream_type == "PG" and len(self.data_window["PG"]) > 100:  
                    derived_value = self.calculate_rr()

        self.record_null_values()

        # Write data to CSV
        self.write_to_csv(timestamp, value, derived_value, stream_type)

    ###########################################
    # Derived Metrics
    ###########################################
    def calculate_hrv(self) -> float:
        """Calculate HRV (RMSSD) from BI values."""
        bi_values = np.array(self.data_window["BI"])
        if len(bi_values) < 30: # 30 beat interval values
            return None  # Not enough data

        intervals = np.diff(bi_values) / 1000.0  # Convert to seconds
        rmssd = np.sqrt(np.mean(np.square(np.diff(intervals))))
        return rmssd

    def calculate_rr(self) -> float:
        """Calculate RR from PG values."""
        ppg_values = np.array(self.data_window["PG"])
        if len(ppg_values) < 100:
            return None  # Not enough data

        # Bandpass filter
        filtered_signal = self.bandpass_filter(ppg_values, 0.1, 0.5, 25)  # Assuming 25 Hz sampling rate
        envelope = np.abs(hilbert(filtered_signal))

        # FFT for respiratory frequency
        fft_result = np.fft.rfft(envelope)
        freqs = np.fft.rfftfreq(len(envelope), 1 / 25)  # 25 Hz sampling rate
        resp_freq = freqs[np.argmax(np.abs(fft_result))]
        return resp_freq * 60  # Convert to breaths per minute

    def bandpass_filter(self, data, lowcut, highcut, fs, order=4):
        nyquist = 0.5 * fs
        low = lowcut / nyquist
        high = highcut / nyquist
        b, a = butter(order, [low, high], btype="band")
        return filtfilt(b, a, data)

    ###########################################
    # Utility Methods
    ###########################################
    def record_null_values(self) -> None:
        """Records null values for each stream type if no values are incoming from the EmotiBit."""
        current_time = time.time()

        for stream_type in self.data.keys():
            if self.last_received[stream_type] is None or current_time - self.last_received[stream_type] >= self.null_record_interval:
                timestamp = self.get_current_iso_time()
                self.data[stream_type].append((timestamp, self.default_value))
                print(f"Appended null value for {stream_type}")

            self.last_received[stream_type] = current_time

    def compare_baseline(self) -> dict:
        """
        Compare the averages of the baseline data with the last 2 minutes of live data
        from the CSV file. If there is not enough data, return a message indicating so.

        Returns:
            dict or str: A dictionary with comparison results or a string message if
                         not enough data has been collected.
        """

        self.timestamp_manager.update_timestamp()
        now = self.timestamp_manager.get_raw_timestamp()
        two_minutes_ago = now - timedelta(minutes=2)
        recent_data = self.read_recent_csv_entries(two_minutes_ago)

        if not recent_data:
            return "Not enough data has been collected to perform the comparison."

        comparison_result = {}

        for stream_type in ["EDA", "HR", "BI", "HRV", "PG", "RR"]:
            baseline_data = self._baseline_data.get(stream_type, [])
            if baseline_data:
                baseline_avg = np.mean(baseline_data)
            else:
                baseline_avg = 0

            live_data = [entry[stream_type] for entry in recent_data if stream_type in entry]
            if live_data:
                live_avg = np.mean(live_data)
            else:
                live_avg = 0

            comparison_result[stream_type] = {
                "baseline_avg": baseline_avg,
                "live_avg": live_avg,
                "elevated": live_avg > baseline_avg
            }

        return comparison_result

    def record_null_values(self) -> None:
        """Records null values for each stream type if no values are incoming from the EmotiBit."""
        current_time = time.time()

        for stream_type in self.data.keys():
            if self.last_received[stream_type] is None or current_time - self.last_received[stream_type] >= self.null_record_interval:
                self.timestamp_manager.update_timestamp()
                timestamp = self.timestamp_manager.get_iso_timestamp()
                self.data[stream_type].append((timestamp, self.default_value))
                print(f"Appended null value for {stream_type}")

            self.last_received[stream_type] = current_time

    def write_to_csv(self, timestamp: str, value: float, derived_value: float, stream_type: str, baseline_status: str) -> None:
        """Write a single data point to the CSV file."""
        if self.csv_writer:
            row = [timestamp]  
            if stream_type == "EDA":
                row.append(value)  # EDA
                row.append(None)   # HR
                row.append(None)   # BI
                row.append(None)   # HRV
                row.append(None)   # PG
                row.append(None)   # RR
            elif stream_type == "HR":
                row.append(None)   # EDA
                row.append(value)  # HR
                row.append(None)   # BI
                row.append(None)   # HRV
                row.append(None)   # PG
                row.append(None)   # RR
            elif stream_type == "BI":
                row.append(None)   # EDA
                row.append(None)   # HR
                row.append(value)  # BI
                row.append(derived_value if derived_value is not None else None)  # HRV
                row.append(None)   # PG
                row.append(None)   # RR
            elif stream_type == "PG":
                row.append(None)   # EDA
                row.append(None)   # HR
                row.append(None)   # BI
                row.append(None)   # HRV
                row.append(value)  # PG
                row.append(derived_value if derived_value is not None else None)  # RR

            row.append(baseline_status)

            self.csv_writer.writerow(row)
        else:
            print("CSV writer is not initialized.")

    def read_recent_csv_entries(self, csv_filename, cutoff_time):
        """
        Retrieve the most recent data from the CSV file that was collected within the
        last two minutes. If there is no data from the last two minutes, returns an empty list.

        Args:
            cutoff_time (datetime): The cutoff time to retrieve data from.

        Returns:
            list: A list of dictionaries containing data from the last 2 minutes.
        """
        recent_data = []

        try:
            with open(csv_filename, mode="r") as csv_file:
                csv_reader = csv.DictReader(csv_file)
                for row in csv_reader:
                    timestamp_str = row["timestamp"]
                    timestamp = datetime.fromisoformat(timestamp_str)

                    if timestamp >= cutoff_time:
                        recent_data.append(row)

        except FileNotFoundError:
            print(f"Error: File {self.csv_filename} not found.")
        except Exception as e:
            print(f"Error reading CSV file: {e}")

        return recent_data