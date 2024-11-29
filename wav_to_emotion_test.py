import os
import numpy as np
import tensorflow as tf
from pydub import AudioSegment
from pydub.utils import make_chunks
from feature_extraction import get_feature_opensmile

# Configuration for OpenSMILE
class Config:
    opensmile_path = "/Users/howieli/Documents/cogs210a_fa24/opensmile/build/progsrc/smilextract/SMILExtract"
    opensmile_config = "/Users/howieli/Documents/cogs210a_fa24/opensmile/config/is09-13/IS09_emotion.conf"
    feature_folder = "features"

# Paths to the model files
MODEL_JSON_PATH = "model/CNN1D_OPENSMILE_IS10.json"
MODEL_WEIGHTS_PATH = "model/CNN1D_OPENSMILE_IS10.h5"

# Load the model architecture from JSON
with open(MODEL_JSON_PATH, "r") as json_file:
    model_json = json_file.read()
model = tf.keras.models.model_from_json(model_json)

# Load the model weights from the H5 file
model.load_weights(MODEL_WEIGHTS_PATH)
print("Model loaded successfully!")

# Define emotion labels (adjust based on the model's training dataset)
emotion_labels = ["angry", "fear", "happy", "neutral", "sad", "surprise"]

def split_audio(audio_file: str, chunk_length_ms: int = 5000) -> list:
    """
    Splits an audio file into smaller chunks.

    Args:
        audio_file (str): Path to the .wav file.
        chunk_length_ms (int): Length of each chunk in milliseconds.

    Returns:
        list: List of paths to the split audio chunks.
    """
    from pathlib import Path

    print(f"Splitting audio file: {audio_file}")
    
    # Ensure the tmp directory exists
    tmp_dir = Path("tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # Load the audio file and split into chunks
    audio = AudioSegment.from_file(audio_file, format="wav")
    chunks = make_chunks(audio, chunk_length_ms)

    # Save each chunk to the tmp directory
    chunk_paths = []
    for i, chunk in enumerate(chunks):
        chunk_path = tmp_dir / f"chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")
        print(f"Created chunk: {chunk_path}")
        chunk_paths.append(str(chunk_path))
    
    print(f"Total chunks created: {len(chunk_paths)}")
    return chunk_paths

def predict_emotion(audio_file: str, config: Config) -> str:
    """
    Predicts the emotion from a single audio file using the pre-trained CNN1D model.

    Args:
        audio_file (str): Path to the .wav file.
        config (Config): Configuration object for OpenSMILE.

    Returns:
        str: Predicted emotion label.
    """
    print(f"Predicting emotion for file: {audio_file}")
    # Step 1: Extract features using OpenSMILE
    features = get_feature_opensmile(config, audio_file)

    # Step 2: Preprocess features for the model
    print(f"Extracted features: {features[:10]} (showing first 10 values)")
    features = np.array(features, dtype=np.float32)  # Convert to float32
    features = np.expand_dims(features, axis=(0, -1))  # Reshape for model [batch, time, channels]

    # Step 3: Predict emotion
    predictions = model.predict(features)
    predicted_label = emotion_labels[np.argmax(predictions)]
    print(f"Predicted emotion: {predicted_label}")

    # Step 4: Return the result
    return predicted_label

# def predict_emotions_long_audio(audio_file: str, config: Config) -> str:
#     """
#     Predicts the emotion from a longer audio file by splitting it into chunks.

#     Args:
#         audio_file (str): Path to the longer .wav file.
#         config (Config): Configuration object for OpenSMILE.

#     Returns:
#         str: Most frequently predicted emotion label.
#     """
#     print(f"Starting emotion prediction for long audio: {audio_file}")
#     chunk_paths = split_audio(audio_file)
#     emotion_counts = {emotion: 0 for emotion in emotion_labels}

#     for chunk_path in chunk_paths:
#         print(f"Processing chunk: {chunk_path}")
#         try:
#             # Pass the chunk path to predict_emotion
#             emotion = predict_emotion(chunk_path, config)
#             emotion_counts[emotion] += 1
#             print(f"Emotion detected for chunk {chunk_path}: {emotion}")
#         except Exception as e:
#             print(f"Error processing chunk {chunk_path}: {e}")
#         finally:
#             os.remove(chunk_path)
#             print(f"Removed chunk: {chunk_path}")

#     # Aggregate results by majority vote
#     print(f"Emotion counts: {emotion_counts}")
#     most_common_emotion = max(emotion_counts, key=emotion_counts.get)
#     print(f"Most common emotion: {most_common_emotion}")
#     return most_common_emotion

def predict_emotion_full_audio(audio_file: str, config: Config) -> str:
    """
    Predicts the emotion from the full audio file without splitting it into chunks.

    Args:
        audio_file (str): Path to the .wav file.
        config (Config): Configuration object for OpenSMILE.

    Returns:
        str: Predicted emotion label.
    """
    print(f"Starting emotion prediction for full audio: {audio_file}")
    try:
        # Pass the entire audio file to OpenSMILE and predict
        emotion = predict_emotion(audio_file, config)
        print(f"Emotion detected for full audio: {emotion}")
        return emotion
    except Exception as e:
        print(f"Error processing audio file {audio_file}: {e}")
        return "unknown"

if __name__ == "__main__":
    # Example usage
    config = Config()
    audio_file = "tmp/recording.wav"  # Path to the full .wav file

    if not os.path.exists(audio_file):
        print(f"Audio file not found: {audio_file}")
        exit(1)

    predicted_emotion = predict_emotion_full_audio(audio_file, config)
    print(f"Predicted Emotion: {predicted_emotion}")

