import threading
import datetime
import pyaudio
import wave
import speech_recognition as sr

class RecordingManager():
    """
    Handles all recording logic and file read/write for audio files. Also handles
    the setting of system audio device. All handling of audio files post recording
    is handled in the app.py file. Audio processing is handled in the 
    audio_processor.py file.
    """
    def __init__(self, recording_file, audio_save_folder): 
        self.stop_event = threading.Event()
        self.recording_started_event = threading.Event()
        self.recording_thread = None
        self.stream_is_active = False
        self._recording_file = recording_file
        self._audio_folder = audio_save_folder
        self.device_index = 0
        self.audio_devices = self.fetch_audio_devices()
        self._timestamp = None

    ##################################################################
    ## GENERAL METHODS
    ##################################################################
    @property
    def timestamp(self):
        return self._timestamp
    
    @timestamp.setter
    def timestamp(self, value):
        self._timestamp = value
    
    @property
    def recording_file(self):
        return self._recording_file
    
    @recording_file.setter
    def recording_file(self, recording_file):
        self._recording_file = recording_file
    
    @property
    def audio_folder(self):
        return self._audio_folder
    
    @audio_folder.setter
    def audio_folder(self, audio_save_folder):
        self._audio_folder = audio_save_folder

    def start_recording(self):
        self.stop_event.clear()
        self.recording_started_event.set()

        t = datetime.datetime.now().isoformat()
        self.timestamp = t

        self.recording_thread = threading.Thread(target=self.record_thread)
        self.recording_thread.start()
        self.recording_started_event.wait()

        print("Recording thread started")   

    def stop_recording(self):
        self.stop_event.set()
        self.recording_thread.join()
        self.recording_started_event.clear()
        self.stream_is_active = False
        print("Recording thread stopped")

    def record_thread(self):
        audio = pyaudio.PyAudio()
        stream = audio.open(format=pyaudio.paInt16, 
                            channels=1, 
                            rate=44100, 
                            input=True, 
                            input_device_index=self.device_index,
                            frames_per_buffer=1024)
        
        frames = []

        self.recording_started_event.set()
        self.stream_is_active = stream.is_active()
        while not self.stop_event.is_set():
            data = stream.read(1024)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        audio.terminate()

        with wave.open(self.recording_file, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(44100)
            wf.writeframes(b''.join(frames))

        print(f"Recording stopped, saved to {self.recording_file}")

    ##################################################################
    ## GETTERS
    ##################################################################
    def get_stream_is_active(self):
        return self.stream_is_active    
    
    def get_stop_event(self):
        return self.stop_event
    
    def get_audio_devices(self):
        return self.audio_devices
    
    ## System call to get audio devices
    def fetch_audio_devices(self):
        p = pyaudio.PyAudio()
        audio_devices = [{'index': i, 'name': p.get_device_info_by_index(i)['name']}
                        for i in range(p.get_device_count())
                        if p.get_device_info_by_index(i)['maxInputChannels'] > 0]
        
        p.terminate()
        return audio_devices

    ##################################################################
    ## SETTERS
    ##################################################################
    def set_device(self, index):
        self.device_index = index
        print(f"Device set to {self.audio_devices[index]['name']}")

    ##################################################################