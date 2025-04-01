import whisper
import warnings
import threading

class TranscriptionManager:
    def __init__(self):
        """
        Initializes the TranscriptionManager class.

        This constructor performs the following actions:
        - Suppresses specific warnings related to future changes and FP16 support on CPU.
        - Loads a Whisper model with the "base" configuration.
        - Converts the model to use 32-bit floating point precision.
        - Moves the model to the CPU.
        - Initializes the result attribute to None.
        - Creates a threading lock for managing concurrent access.

        Attributes:
            model (whisper.Model): The Whisper model used for transcription.
            result (None): Placeholder for the transcription result.
            lock (threading.Lock): A lock to ensure thread-safe operations.
        """

        warnings.filterwarnings("ignore", category=FutureWarning)
        warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

        self.model = whisper.load_model("base")
        self.model = self.model.float()
        self.model = self.model.to("cpu")
        self.result = None
        self.lock = threading.Lock()

    def switch_model(self, model_name):
        try:
            self.model = whisper.load_model(model_name)
            self.model = self.model.float()
            self.model = self.model.to("cpu")
            print(f"Model switched to {model_name}.")

        except FileNotFoundError:
            print(f"Model {model_name} not found. Please ensure that the model is in the correct directory and that the model name is correct.")

    def transcribe_audio(self, audio_file):
        """
        Transcribes the given audio file using the Whisper model.
        Args:
            audio_file (str): The path to the audio file to be transcribed.
        Returns:
            None: The transcription result is stored in the instance variable `self.result`.
        """

        with self.lock:
            audio = whisper.load_audio(audio_file)
            result = self.model.transcribe(audio)
            self.result = result["text"]

    def transcribe(self, audio_file):
        """
        Starts the transcription process for the given audio file.
        This method creates a new thread to handle the transcription of the provided
        audio file. It waits for the transcription to complete and then returns the result.
        Args:
            audio_file (str): The path to the audio file to be transcribed.
        Returns:
            str: The transcription result of the audio file.
        """

        thread = threading.Thread(target=self.transcribe_audio, args=(audio_file,))
        thread.start()
        thread.join()
        with self.lock:
            return self.result
