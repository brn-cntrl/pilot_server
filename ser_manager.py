import pandas as pd
import audinterface
import audonnx
import audeer
import numpy as np
import joblib
import os

class SERManager:
    def __init__(self, app):
        self.audonnx_model = None
        self.MODEL_ROOT = None
        self.CLF = joblib.load('classifier/emotion_classifier.joblib')
        self.cache_root = None
        self.app = app

    def _is_folder_empty(self, folder_name):
        folder_path = os.path.join(self.app.root_path, folder_name)
        return not os.path.exists(folder_path) or len(os.listdir(folder_path)) == 0   
    
    def set_aud_model(self):
        if self._is_folder_empty('model'):
            url = 'https://zenodo.org/record/6221127/files/w2v2-L-robust-12.6bc4a7fd-1.1.0.zip'
            self.cache_root = audeer.mkdir('cache')
            self.MODEL_ROOT = audeer.mkdir('model')
            archive_path = audeer.download_url(url, cache_root, verbose=True)
            audeer.extract_archive(archive_path, MODEL_ROOT)
            model = audonnx.load(MODEL_ROOT)
        else:
            cache_root = os.path.join(self.app.root_path, 'cache')
            MODEL_ROOT = os.path.join(self.app.root_path, 'model')
            model = audonnx.load(self.MODEL_ROOT)

        return model
    
    def predict_emotion(self, audio_chunk):
        
        if audio_chunk.dtype != np.float32:
            audio_chunk = audio_chunk.astype(np.float32)

        if self.audonnx_model is None:
            raise ValueError("The AUDONNX_MODEL is not initialized. Please load the model before calling this function.")
        
        sampling_rate = 16000
        hidden_states_feature = audinterface.Feature(
            self.audonnx_model.labels('hidden_states'),
            process_func=self.audonnx_model,
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

        prediction = self.CLF.predict(hidden_states_df)

        return prediction[0]
