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

    def update_timestamp(self):
        with self.lock:
            self.current_timestamp = datetime.now()

    def get_raw_timestamp(self):
        """Returns the current timestamp as a datetime object."""
        with self.lock:
            return self.current_timestamp
        
    def get_iso_timestamp(self):
        """Returns the current timestamp."""
        with self.lock:
            return self.current_timestamp.isoformat()