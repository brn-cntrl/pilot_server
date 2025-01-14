import librosa
import torch
from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2Processor
import json
import numpy as np
import torch.nn.functional as F

class SERManager:
    def __init__(self) -> None:
        device = 'mps' if torch.backends.mps.is_built() else 'cpu'  # Automatically detect if MPS is available
        self.device = device  # Save device for later use
        self._model = Wav2Vec2ForSequenceClassification.from_pretrained("SER_MODEL").to(self.device)
        self._processor = Wav2Vec2Processor.from_pretrained("SER_MODEL")
        self.max_length = 32000
        
        try:
            with open('label_maps/label_map.json', 'r') as f:
                self.label_map = json.load(f)

            with open('label_maps/inverse_label_map.json', 'r') as f:
                self.inverse_label_map = json.load(f)

        except FileNotFoundError:
            print("Label maps not found. Please ensure that the label maps are in the correct directory.")

    def _preprocess_audio(self, audio_chunk):
        """
        Predicts the emotion from a given audio chunk using a custom trained Wav2Vec2 model.
        Parameters:
            - audio_chunk: audio file in wav format. 
        Returns:
            - str: The predicted emotion label.
        """
        speech, sr = librosa.load(audio_chunk, sr=16000)

        if len(speech) > self.max_length:
            speech = speech[:self.max_length]
        else:
            speech = np.pad(speech, (0, self.max_length - len(speech)))

        inputs = self._processor(speech, sampling_rate=16000, return_tensors="pt", padding=True, truncation=True, max_length=self.max_length)

        return inputs.input_values.squeeze()
    
    def predict_emotion(self, audio_chunk):
        input_values = self._preprocess_audio(audio_chunk).unsqueeze(0).to(self.device)

        with torch.no_grad():
            outputs = self._model(input_values)

        logits = outputs.logits
        predicted_id = logits.argmax(dim=-1).item()
        softmax_probs = F.softmax(logits, dim=-1)
        
        confidence = softmax_probs[0, predicted_id].item()

        return self.inverse_label_map[str(predicted_id)], confidence