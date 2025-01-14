from ser_manager3 import SERManager

ser_manager = SERManager()

audio_chunk = 'audio_files/ID_None_SER_question__2.wav'

emotion, confidence = ser_manager.predict_emotion(audio_chunk)

print(f"Predicted emotion: {emotion}")
print(f"Confidence: {confidence}")