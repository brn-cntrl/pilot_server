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
        self.current_row = {key: None for key in ["timestamp", "EDA", "HR", "BI", "HRV", "PG", "RR", "event_marker"]}
        self.last_received = {key: None for key in ["EDA", "HR", "BI", "HRV", "PG", "RR"]}
        self.data_window = {key: deque(maxlen=500) for key in ["BI", "PG"]}  # Sliding window for derived metrics
        self._event_marker = None
        self.collecting_baseline = False
        self.dispatcher = dispatcher.Dispatcher()
        self.dispatcher.map("/EmotiBit/0/*", self.generic_handler)
        self.server = osc_server.ThreadingOSCUDPServer((self._ip, self._port), self.dispatcher)
        self.server_thread = None
        self.shutdown_event = Event()
        self.default_value = 0
        self.csv_file = None
        self.csv_writer = None
        
        atexit.register(self.stop)

    @property 
    def event_marker(self) -> str:
        return self._event_marker

    @event_marker.setter
    def event_marker(self, value: str) -> None:
        self._event_marker = value

    def start_baseline_collection(self) -> None:
        if self.collecting_baseline:
            print("Already collecting baseline data.")
            return
        
        self.collecting_baseline = True

    def stop_baseline_collection(self) -> None:
        if not self.collecting_baseline:
            print("Not currently collecting baseline data.")
            return
        
        self.collecting_baseline = False

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

        if not hasattr(self, 'current_timestamp') or self.current_timestamp != self.timestamp_manager.get_iso_timestamp():
            self.timestamp_manager.update_timestamp()
            self.current_timestamp = self.timestamp_manager.get_iso_timestamp()

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

        self.write_to_csv(self.current_row)

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

    def get_baseline_entries(self) -> list:
        """Check the CSV file for rows with 'baseline' under 'baseline_status' and return as a list of dictionaries."""
        baseline_entries = []
        
        try:
            with open(self.csv_filename, 'r') as file:
                csv_reader = csv.DictReader(file)

                for row in csv_reader:
                    if row.get("baseline_status") == "baseline":
                        baseline_entries.append(row)
            
            return baseline_entries

        except FileNotFoundError:
            print(f"Error: The file {self.csv_filename} was not found.")
            return []
        except Exception as e:
            print(f"Error reading the CSV file: {e}")
            return []
        
    def get_live_entries(self, lookback_minutes: int = 2) -> list: 
        """Retrieve non-baseline entries (live data) from the last 'lookback_minutes' minutes.
            Args:
                lookback_minutes (int): The number of minutes to look back for live data.
            Returns:
                list: A list of dictionaries containing live data from the CSV file.
        """
        non_baseline_entries = []
        try:
            with open(self.csv_filename, 'r') as file:
                csv_reader = csv.DictReader(file)
                
                current_time = datetime.now()
                time_threshold = current_time - timedelta(minutes=lookback_minutes)
                
                for row in csv_reader:
                    baseline_status = row.get("baseline_status")
                    timestamp = row.get("timestamp")
                    
                    if baseline_status != "baseline" and timestamp:
                        row_time = datetime.fromisoformat(timestamp)
                        if row_time >= time_threshold:
                            non_baseline_entries.append(row)
            
            return non_baseline_entries
        
        except FileNotFoundError:
            print(f"Error: The file {self.csv_filename} was not found.")
            return []
        except Exception as e:
            print(f"Error reading the CSV file: {e}")
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

    def write_to_csv(self, current_row) -> None:
        """Write the current row to the CSV file."""
        
        if self.csv_writer:
            # Replace None with a default value ('N/A' or '0') for each field
            row = [
                current_row["timestamp"],                                           # timestamp
                current_row["EDA"] if current_row["EDA"] is not None else 'N/A',    # EDA
                current_row["HR"] if current_row["HR"] is not None else 'N/A',      # HR
                current_row["BI"] if current_row["BI"] is not None else 'N/A',      # BI
                current_row["HRV"] if current_row["HRV"] is not None else 'N/A',    # HRV
                current_row["PG"] if current_row["PG"] is not None else 'N/A',      # PG
                current_row["RR"] if current_row["RR"] is not None else 'N/A',      # RR
                current_row["baseline_status"]  
            ]
            
            self.csv_writer.writerow(row)
        else:
            print("CSV writer is not initialized.")

    def read_recent_csv_entries(self, csv_filename, cutoff_time):
        """
        Retrieve the most recent data from the CSV file that was collected within the
        specicifed cutoff_time threshold. If there is no data within the cutoff period 
        it returns an empty list.
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