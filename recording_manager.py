import threading
import pyaudio
import wave
import speech_recognition as sr
from timestamp_manager import TimestampManager

class RecordingManager():
    """
    Handles all recording logic and file read/write for audio files. Also handles
    the setting of system audio device. All handling of audio files post recording
    is handled in the app.py file. Audio processing is handled in the 
    audio_processor.py file.
    """
    def __init__(self, recording_file) -> None: 
        self.audio = pyaudio.PyAudio()
        self.stop_event = threading.Event()
        self.recording_started_event = threading.Event()
        self.stream_ready_event = threading.Event()
        self.recording_thread = None
        self._stream_is_active = False
        self._recording_file = recording_file
        self.device_index = 0
        self.audio_devices = self.fetch_audio_devices()
        self._timestamp = None
        self._end_timestamp = None
        self.timestamp_manager = TimestampManager()
        print("Recording manager initialized...")
        print(f"Recording manager's temporary recording file set to {self.recording_file}")

    ##################################################################
    ## GENERAL METHODS
    ##################################################################
    @property
    def timestamp(self) -> str:
        return self._timestamp
    
    @timestamp.setter
    def timestamp(self, value) -> None:
        self._timestamp = value
    
    @property
    def end_timestamp(self) -> str:
        return self._end_timestamp
    
    @end_timestamp.setter
    def end_timestamp(self, value) -> None:
        self._end_timestamp = value

    @property
    def recording_file(self) -> str:
        return self._recording_file
    
    @recording_file.setter
    def recording_file(self, recording_file) -> None:
        self._recording_file = recording_file

    @property
    def stream_is_active(self) -> bool:
        return self._stream_is_active
    
    @stream_is_active.setter
    def stream_is_active(self, value) -> None:
        self._stream_is_active = value

    def start_recording(self) -> None:
        self.stop_event.clear()
        self.recording_started_event.set()

        self.timestamp = self.timestamp_manager.get_timestamp("iso")

        self.recording_thread = threading.Thread(target=self.record_thread)
        self.recording_thread.start()
        self.stream_ready_event.wait()
        self.stream_is_active = True
        self.recording_started_event.wait()

        print("Recording thread started")   

    def stop_recording(self) -> None:
        self.stop_event.set()
        self.recording_thread.join()
        self.recording_started_event.clear()
        self.stream_ready_event.clear()
        self.stream_is_active = False
        self.end_timestamp = self.timestamp_manager.get_timestamp("iso")
        print(f"Recording stopped at {self.end_timestamp}")

    def reset_audio_system(self):
        try:
            if self.audio is not None:
                self.audio.terminate()
            self.audio = pyaudio.PyAudio()
            print("Audio system reset successfully.")

        except Exception as e:
                    print(f"Error resetting audio system: {e}")

    def record_thread(self) -> None:
        stream = self.audio.open(format=pyaudio.paInt16, 
                            channels=1, 
                            rate=44100, 
                            input=True, 
                            input_device_index=self.device_index,
                            frames_per_buffer=1024)
        
        self.stream_ready_event.set()

        frames = []

        self.recording_started_event.set()

        while not self.stop_event.is_set():
            data = stream.read(1024)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        # self.audio.terminate()

        with wave.open(self.recording_file, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(44100)
            wf.writeframes(b''.join(frames))

        print(f"Recording stopped, saved to {self.recording_file}")

    ##################################################################
    ## GETTERS
    ##################################################################
    def get_stop_event(self) -> threading.Event:
        return self.stop_event
    
    def get_audio_devices(self) -> list:
        return self.audio_devices
    
    ## System call to get audio devices
    def fetch_audio_devices(self) -> list:
        if self.audio is None:
            self.audio = pyaudio.PyAudio()
        
        audio_devices = [{'index': i, 'name': self.audio.get_device_info_by_index(i)['name']}
                        for i in range(self.audio.get_device_count())
                        if self.audio.get_device_info_by_index(i)['maxInputChannels'] > 0]
        
        return audio_devices

    ##################################################################
    ## SETTERS
    ##################################################################
    def set_device(self, index) -> None:
        self.device_index = index
        name = None
        for device in self.audio_devices:
            if device['index'] == index:
                name = device['name']
                break
        print(f"Device set to {name if name else 'Unknown (index not in audio_devices list)'}")

    ##################################################################