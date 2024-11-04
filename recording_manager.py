import threading
import datetime
import pyaudio
import wave
import time
import numpy as np
import os
import shutil
import speech_recognition as sr

class RecordingManager():
    def __init__(self): 
        self.stop_event = threading.Event()
        self.recording_started_event = threading.Event()
        self.recording_thread = None
        self.stream_is_active = False
        self.recording_file = "tmp/recording.wav"
        self.audio_save_folder = "audio_files"
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

    def get_audio_chunk_as_np(self, offset=0, duration=None, sample_rate=16000):
        """
        This function returns the section of audio specified by the offset and 
        duration parameters as a normalized numpy array. This is necessary for the
        current SER classifier and is subject to change.
        """
        try:
            with wave.open(self.recording_file, 'rb') as wf:
                num_channels = wf.getnchannels()
                original_sample_rate = wf.getframerate()
                start_frame = int(offset * original_sample_rate)
                num_frames = int(duration * original_sample_rate) if duration else wf.getnframes() - start_frame

                wf.setpos(start_frame)
                signal = wf.readframes(num_frames)
                signal = np.frombuffer(signal, dtype=np.int16).astype(np.float32)
                signal = signal / np.iinfo(np.int16).max  

                # Convert stereo to mono by averaging channels
                if num_channels == 2:
                    signal = signal.reshape(-1, 2).mean(axis=1)

                # If the original sample rate differs, resample to target sample rate
                if original_sample_rate != sample_rate:
                    signal = self.resample_audio(signal, original_sample_rate, sample_rate)

                return signal
            
        except Exception as e:
            print(f"An error occurred while processing the audio: {e}")
            return None

    def resample_audio(signal, original_sample_rate, target_sample_rate):
        """
        Resamples the signal to match the target sample rate using linear interpolation.
        """
        ratio = target_sample_rate / original_sample_rate
        resampled_length = int(len(signal) * ratio)
        resampled_signal = np.interp(
            np.linspace(0, len(signal) - 1, resampled_length), np.arange(len(signal)), signal
        )
        return resampled_signal

    def get_audio_duration(self):
        with wave.open(self.recording_file, 'rb') as wf:
            frames = wf.getnframes()          
            rate = wf.getframerate()          
            duration = frames / float(rate)   
        return duration

    def delete_recording_file(self):
        try:
            if os.path.exists(self.recording_file):
                os.remove(self.recording_file)
                print(f"File '{self.recording_file}' deleted successfully.")
            else:
                print(f"File '{self.recording_file}' does not exist.")
        except PermissionError:
            print(f"Permission denied: Unable to delete file '{self.recording_file}'. Check file permissions.")
        except FileNotFoundError:
            print(f"File not found: '{self.recording_file}' might have already been deleted.")
        except Exception as e:
            print(f"An error occurred while trying to delete the file '{self.recording_file}': {str(e)}")

    def save_audio_file(self, filename):
        try:
            os.makedirs(self.audio_save_folder, exist_ok=True)
            new_filename = os.path.join(self.audio_save_folder, filename)
            shutil.copy(self.recording_file, new_filename)
            print(f"File '{filename}' saved successfully.")
        except PermissionError:
            print(f"Permission denied: Unable to save file '{filename}'. Check file permissions.")
        except FileNotFoundError:
            print(f"File not found: '{self.recording_file}' might have already been deleted.")
        except Exception as e:
            print(f"An error occurred while trying to save the file '{filename}': {str(e)}")

    # Necessary for SER task
    def normalize_audio(self, audio):
        audio_array = audio / np.max(np.abs(audio))
        return audio_array

    def record_timestamps(self, timestamps):  # For use in thread
        while not self.stop_event.is_set():
            timestamps.append(datetime.datetime.now().isoformat())
            time.sleep(10)

    def rename_audio_file(self, id, prefix, suffix):
        return f"ID_{id}_{prefix}_{suffix}.wav"
    
    def process_audio_segments(self, subject, ser_manager, ts, prefix):
        """
        This function processes the audio segments in 20.
        -second chunks and returns a list of transcriptions
        with timestamps and SER values in JSON object format.
        """
        initial_timestamp = ts
        recognizer = sr.Recognizer()
        audio_segments = []

        with wave.open(self.recording_file, 'rb') as wf:
            sample_rate = wf.getframerate()
            channels = wf.getnchannels()
            total_frames = wf.getnframes()
            duration = total_frames / float(sample_rate)

            segment_duration = 20
            segment_frames = int(segment_duration * sample_rate)
            total_segments = int(duration // segment_duration)

            for i in range(total_segments + 1): # Include last segment if remainder exists
                start_time = initial_timestamp + i * segment_duration
                iso_timestamp = datetime.datetime.fromtimestamp(start_time).isoformat()
                wf.setpos(i * segment_frames)

                frames = wf.readframes(segment_frames)
                if(len(frames) == 0):
                    break # EOF

                temp_file = f"tmp/temp_segment_{i}.wav"

                id = subject.get_id()

                # save_file = f"audio_save_folder/ID_{id}_{prefix}_segment_{i}.wav"

                with wave.open(temp_file, 'wb') as wf_temp:
                    wf_temp.setnchannels(channels)
                    wf_temp.setsampwidth(wf.getsampwidth())
                    wf_temp.setframerate(sample_rate)
                    wf_temp.writeframes(frames)

                with sr.AudioFile(temp_file) as source:
                    audio_data = recognizer.record(source)
                    try:
                        recognized_text = recognizer.recognize_google(audio_data)
                        sig = self.get_wav_as_np(temp_file)

                        # TODO: Implement emotion prediction class
                        emotion = ser_manager.predict_emotion(sig)

                        transcription_data = {
                            'timestamp': iso_timestamp,
                            'recognized_text': recognized_text,
                            'emotion': emotion
                        }

                        audio_segments.append(transcription_data)
                    except sr.UnknownValueError:
                        print(f"Google Speech Recognition could not understand the audio at {start_time:.2f}.")
                    except sr.RequestError as e:
                        print(f"Error with the recognition service: {e}")

                    # Cleanup
                    file_name = self.rename_audio_file(id, prefix, f"segment_{i}")
                    self.save_audio_file(self.recording_file, file_name, 'audio_files')
                    os.remove(temp_file)

        return audio_segments

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