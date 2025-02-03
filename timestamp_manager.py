from datetime import datetime
import threading

class TimestampManager:
    _instance = None  
    _lock = threading.Lock()  

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'current_timestamp'):
            self.current_timestamp = None
            self.lock = threading.Lock()
            self.timestamp_event = threading.Event()
            print("Timestamp manager initialized...")

    def update_timestamp(self):
        with self.lock:
            self.current_timestamp = datetime.now()

    def get_raw_timestamp(self):
        """Returns the current timestamp as a datetime object."""
        with self.lock:
            return self.current_timestamp.timestamp()
        
    def get_iso_timestamp(self):
        """Returns the current timestamp."""
        with self.lock:
            return self.current_timestamp.isoformat()
        
    def get_timestamp(self, type: str="iso") -> str:
        """
        Updates the timestamp if possible, otherwise waits for the latest timestamp.
        Args:
            type (str): The type of timestamp to return ("iso" or "raw").
        """
        if self.lock.acquire(blocking=False):  # Try to acquire lock without waiting
            try:
                self.current_timestamp = datetime.now()
                self.timestamp_event.set()  # Signal that an update occurred
                self.timestamp_event.clear()  # Reset event for future updates
            finally:
                self.lock.release()
        else:
            self.timestamp_event.wait()  # Wait for the current update to finish

        with self.lock:
            if type == "iso":
                return self.current_timestamp.isoformat()
            
            return self.current_timestamp  # Default to raw