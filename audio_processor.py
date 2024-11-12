import os
import numpy as np 
import wave

class AudioProcessor:
    """
    The audio processor class is responsible for handling audio processing functions.
    """
    def __init__(self, recording_file, audio_save_folder):
        self._recording_file = recording_file
        self._audio_folder = audio_save_folder

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

    def get_audio_chunk_as_np(self, offset=0, duration=None, sample_rate=16000):
        """
        Returns the section of audio specified by the offset and duration parameters as a normalized 
        numpy array. This is necessary for the current SER classifier and is subject to change when 
        another SER module is implemented.

        Parameters
        - the path and filename of the wav file, 
        - the offset in seconds, 
        - the duration in seconds, 
        - the samplerate in Hz.
        Returns: 
        - the audio chunk as a numpy array
        Exception:
        - if the file is not found
        """
        try:
            with wave.open(self._recording_file, 'rb') as wf:
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

        Parameters: 
        - the signal as a numpy array, 
        - the original sample rate in Hz, 
        - the target sample rate in Hz.
        Returns:
        - the resampled signal as a numpy array
        """
        ratio = target_sample_rate / original_sample_rate
        resampled_length = int(len(signal) * ratio)
        resampled_signal = np.interp(
            np.linspace(0, len(signal) - 1, resampled_length), np.arange(len(signal)), signal
        )
        return resampled_signal

    def get_audio_duration(self):
        """
        Calculate the duration of an audio file.
        This function opens an audio file specified by the file_path, reads the number of frames and the frame rate,
        and calculates the duration of the audio in seconds.
        Parameter:
            file_path (str): The path/filename of the audio file.
        Returns:
            float: The duration of the audio file in seconds.
        """
        with wave.open(self._recording_file, 'rb') as wf:
            frames = wf.getnframes()          
            rate = wf.getframerate()          
            duration = frames / float(rate)   
        return duration

    def normalize_audio(self, audio): # Necessary for SER task
        audio_array = audio / np.max(np.abs(audio))
        return audio_array

    # def record_timestamps(self, timestamps): # For use in thread
    #     while not self.stop_event.is_set():
    #         timestamps.append(datetime.datetime.now().isoformat())
    #         time.sleep(10)
    
    def split_wav_to_segments(self, task_id, input_wav, segment_duration=20, output_folder="tmp/"):
        """
        Splits a WAV file into user defined number of segments and saves each segment in the specified output folder.

        Parameters:
        - input_wav (str): Path to the input WAV file.
        - segment_duration (int): Duration of each segment in seconds. Default is 20 seconds.
        - output_folder (str): Folder to save the output segments. Default is 'tmp'.
        Returns:
        - List of paths/filenames to the saved segment files.
        """
        # Ensure the output folder exists
        if not output_folder or not isinstance(output_folder, str):
            raise ValueError("Invalid output folder path.")
        
        os.makedirs(output_folder, exist_ok=True)
        
        segment_files = []
        try:
            with wave.open(input_wav, 'rb') as wf:
                sample_rate = wf.getframerate()
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                total_frames = wf.getnframes()
                duration = total_frames / sample_rate
                
                print(f"Total frames: {total_frames}, Sample rate: {sample_rate}, Duration: {duration:.2f} seconds")

                # Calculate frames per segment
                segment_frames = int(segment_duration * sample_rate)
                total_segments = int(duration // segment_duration) + (1 if duration % segment_duration != 0 else 0)
                
                for i in range(total_segments):
                    wf.setpos(i * segment_frames)
                
                    frames = wf.readframes(segment_frames)

                    segment_file = os.path.join(output_folder, f"{task_id}_segment_{i}.wav")
                    print(f"Creating segment file: {segment_file}")  # Debugging statement
                    
                    with wave.open(segment_file, 'wb') as segment_wf:
                        segment_wf.setnchannels(channels)
                        segment_wf.setsampwidth(sample_width)
                        segment_wf.setframerate(sample_rate)
                        segment_wf.writeframes(frames)
                    
                    segment_files.append(segment_file)
                    print(f"Segment {i} saved as {segment_file}")
                    
            return segment_files
        except Exception as e:
            print(f"An error occurred while splitting the WAV file: {str(e)}")
        
        return segment_files