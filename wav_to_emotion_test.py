import json
import numpy as np
import tensorflow
from feature_extraction import extract_features
import tensorflow as tf

# Paths to model architecture and weights
JSON_PATH = 'model/CNN1D_LIBROSA_IS10.json'
WEIGHTS_PATH = 'model/CNN1D_LIBROSA_IS10.h5'

# Load the emotion labels
emotion_labels = ["angry", "fear", "happy", "neutral", "sad", "surprise"]

# Step 1: Load the model architecture from the JSON file
with open(JSON_PATH, 'r') as json_file:
    model_json = json_file.read()

model = tensorflow.keras.models.model_from_json(model_json)  # Deserialize the model architecture

# Step 2: Load the weights into the model
model.load_weights(WEIGHTS_PATH)

def predict_emotion(file: str) -> str:
    """
    Predict emotion from an audio file using the pre-trained model.
    
    Args:
        file (str): Path to the .wav file.
        
    Returns:
        str: Predicted emotion label.
    """
    # Step 1: Extract features
    features = extract_features(file, pad=True)  # Ensure consistent length

    # Step 2: Reshape for model input
    features = features.reshape(1, -1, 1)  # Adjust shape for 1D CNN
    print("Extracted Features Shape:", features.shape)
    print("Extracted Features Sample:", features[:10])

    # Step 3: Predict emotion
    prediction = model.predict(features)
    print("Class Probabilities:", prediction)
    predicted_emotion = emotion_labels[np.argmax(prediction)]
    print(f"Predicted Emotion: {predicted_emotion}")

    return predicted_emotion

if __name__ == "__main__":
    # Example usage
    AUDIO_FILE = 'tmp/recording.wav'  # Path to the .wav file
    emotion = predict_emotion(AUDIO_FILE)
    print(f"Predicted emotion: {emotion}")
