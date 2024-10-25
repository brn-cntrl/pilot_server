import threading
import datetime
import pyaudio
import wave

class RecordingManager():
    def __init__(self): 
        self.stop_event = threading.Event()
        self.recording_started_event = threading.Event()
        self.recording_thread = None
        self.stream_is_active = False
        self.recording_file = "tmp/recording.wav"
        self.device_index = 0
        self.audio_devices = self.fetch_audio_devices()

    ##################################################################
    ## GENERAL METHODS
    ##################################################################
    def _set_timestamp(self, t):
        self.timestamp = t
    
    def start_recording(self):
        self.stop_event.clear()
        self.recording_started_event.set()

        t = datetime.datetime.now().isoformat()
        self._set_timestamp(t)

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
    def get_timestamp(self):
        return self.timestamp
    
    def get_recording_file(self):
        return self.recording_file  
    
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