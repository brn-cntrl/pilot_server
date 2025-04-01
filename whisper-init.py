import whisper
import pyaudio
import wave
import os
import warnings

def record_audio(filename, duration=5, rate=16000, channels=1, chunk_size=1024):
    p = pyaudio.PyAudio()

    stream = p.open(format=pyaudio.paInt16,
                    channels=channels,
                    rate=rate,
                    input=True,
                    frames_per_buffer=chunk_size)
    
    print(f"Recording audio for {duration} seconds...")
    
    frames = []
    for _ in range(0, int(rate / chunk_size * duration)):
        data = stream.read(chunk_size)
        frames.append(data)
    
    print("Recording complete.")
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(rate)
        wf.writeframes(b''.join(frames))
    
    print(f"Audio saved to {filename}")

def transcribe_audio(filename):
    print("Loading Whisper model...")
    model = whisper.load_model("base") 
    
    print("Transcribing audio...")
    result = model.transcribe(filename)
    
    print("Transcription complete:")
    print(result["text"])

def main():
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

    audio_filename = "tmp/whisper-init.wav"
    
    record_audio(audio_filename, duration=5)
    
    transcribe_audio(audio_filename)

    os.remove(audio_filename)
    print(f"Temporary audio file {audio_filename} has been deleted.")

if __name__ == "__main__":
    main()
