import audonnx
import audinterface
import audeer
import numpy as np
import joblib
import os
import pandas as pd
import wave
import librosa

# # download the model from the notebook
# model_root = 'model'
# cache_root = 'cache'


# audeer.mkdir(cache_root)
# def cache_path(file):
#     return os.path.join(cache_root, file)


# url = 'https://zenodo.org/record/6221127/files/w2v2-L-robust-12.6bc4a7fd-1.1.0.zip'
# dst_path = cache_path('model.zip')

# if not os.path.exists(dst_path):
#     audeer.download_url(
#         url, 
#         dst_path, 
#         verbose=True,
#     )
    
# if not os.path.exists(model_root):
#     audeer.extract_archive(
#         dst_path, 
#         model_root, 
#         verbose=True,
#     )

CLF = joblib.load('classifier/emotion_classifier.joblib')
RECORDING_FILE = 'tmp/recording.wav'
MODEL_ROOT = "model"
AUDONNX_MODEL = audonnx.load(MODEL_ROOT)

# I think these methods are not needed, if we use librosa package to load the model.

# def normalize_audio(audio): # Necessary for SER task
#     audio_array = audio / np.max(np.abs(audio))
#     return audio_array

# def get_wav_as_np(filename):
#     """
#     Loads the entire wav file stored in tmp and returns it as a normalized numpy array.
#     Arguments: 
#         - the path and filename of the wav file
#     Returns: 
#         - the wav file as a numpy array
#     Exception: 
#         - if the file is not found
#     """
#     try:
#         with wave.open(filename, 'rb') as wf:
#             num_channels = wf.getnchannels()
#             num_frames = wf.getnframes()
#             signal = wf.readframes(num_frames)
#             signal = np.frombuffer(signal, dtype=np.int16).astype(np.float32)
#             signal = signal / np.iinfo(np.int16).max

#             if num_channels == 2:
#                 signal = signal.reshape(-1, 2)
#                 signal = signal.mean(axis=1)

#             return signal
#     except Exception as e:
#         print("Couldn't locate an audio file.")
#         return None
    
def predict_emotion(audio_chunk):
    """
    Predicts the emotion from an audio chunk using a pre-trained classifier and an ONNX model.
    Args:
        audio_chunk (numpy.ndarray): The input audio chunk to be analyzed. It should be a numpy array.
    Returns:
        str: The predicted emotion label.
    Raises:
        ValueError: If the AUDONNX_MODEL is not initialized.
    Notes:
        - The function expects the global variables `CLF` (classifier) and `AUDONNX_MODEL` (ONNX model) to be initialized before calling this function.
        - The audio chunk will be converted to float32 if it is not already in that format.
        - The function extracts hidden states from the audio chunk using the ONNX model and then uses these features to predict the emotion using the classifier.
    """

    import pandas as pd
    global CLF, AUDONNX_MODEL

    #################### ONLY FOR TESTING #######################
    # CLF = joblib.load('classifier/emotion_classifier.joblib')
    # MODEL_ROOT = "model"
    # AUDONNX_MODEL = audonnx.load(MODEL_ROOT)
    #############################################################
    
    if audio_chunk.dtype != np.float32:
        audio_chunk = audio_chunk.astype(np.float32)

    if AUDONNX_MODEL is None:
        raise ValueError("The AUDONNX_MODEL is not initialized. Please load the model before calling this function.")
    
    # Here we set the sampling_rate to 16000hz, just like what the notebook have set to, but our audio is 44100hz which
    # is causing the issue of inaccuracy.
    sampling_rate = 16000
    hidden_states_feature = audinterface.Feature(
        AUDONNX_MODEL.labels('hidden_states'),
        process_func=AUDONNX_MODEL,
        process_func_args={'outputs': 'hidden_states'},
        sampling_rate=sampling_rate,
        resample=True,
        num_workers=1,
        verbose=True
    )
    
    hidden_states = hidden_states_feature(audio_chunk, sampling_rate)

    if hidden_states.ndim == 3:
        hidden_states = hidden_states.reshape(1, -1)

    hidden_states_df = pd.DataFrame(hidden_states)
    hidden_states_df.columns = [f'hidden_states-{i}' for i in range(1024)]

    prediction = CLF.predict(hidden_states_df)

    return prediction[0]

if __name__ == "__main__":  
    signal, orig_sr = librosa.load(RECORDING_FILE, sr=None)
    print(f"Original sampling rate: {orig_sr} Hz")
    signal_resampled = librosa.resample(signal, orig_sr=orig_sr, target_sr=16000)
    prediction = predict_emotion(signal_resampled)
    print(f"Predicted emotion: {prediction}")