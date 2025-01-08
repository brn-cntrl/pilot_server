from flask import Flask, request, jsonify, render_template, redirect, send_file, Response
import webview
import warnings
import threading
from threading import Thread
import boto3
import joblib
import os, sys
import datetime
import time
import pyaudio
import librosa
import signal 
import json
import re
import speech_recognition as sr
import numpy as np
import audinterface
import audeer
import audonnx

from subject_manager import SubjectManager
from recording_manager import RecordingManager
from test_manager import TestManager
from emotibit_streamer import EmotiBitStreamer
from ser_manager import SERManager
from csv_handler import CSVHandler
from audio_file_manager import AudioFileManager
from form_manager import FormManager

##################################################################
## Globals 
##################################################################

# Initialize the Flask app and pass reference to ser manager singleton
app = Flask(__name__)

device_index = 0
RECORDING_FILE = 'tmp/recording.wav'
AUDIO_SAVE_FOLDER = 'audio_files'
current_question_index = 0
current_ser_question_index = 0
current_test_number = 1
emotibit_thread = None
TASK_QUESTIONS_1 = None
TASK_QUESTIONS_2 = None
SER_QUESTIONS = None
PORT_NUMBER = 8000
EMOTIBIT_PORT_NUMBER = 9005

# Singletons stored in global scope NOTE: These could be moved to Flask g instance to further reduce global access
subject_manager = SubjectManager() 
recording_manager = RecordingManager(RECORDING_FILE, AUDIO_SAVE_FOLDER) 
test_manager = TestManager()
emotibit_streamer = EmotiBitStreamer(EMOTIBIT_PORT_NUMBER)
audio_file_manager = AudioFileManager(RECORDING_FILE, AUDIO_SAVE_FOLDER)
ser_manager = SERManager(app)
form_manager = FormManager()

TASK_QUESTIONS = {}
MODEL_ROOT = "model"
AUDONNX_MODEL = None
CLF = None

DYNAMODB = boto3.resource('dynamodb', region_name='us-west-1')
TABLE = DYNAMODB.Table('Users')
ID_TABLE = DYNAMODB.Table('available_ids')

##################################################################
## Routes 
##################################################################
@app.route('/set_task_id', methods=['POST'])
def set_task_id() -> Response:
    global subject_manager
    try:
        data = request.get_json()
        print(data)
        ts = datetime.datetime.now().isoformat()
        task = data.get("task_id")
        if not task:
            return jsonify({'status': 'error', 'message': 'Task ID is required'}), 400
    
        subject_manager.subject_data['Task_ID'].append((ts, task))
       
        return jsonify({'status': f'{task} appended to data with at timestamp {ts}.'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/baseline_comparison', methods=['POST'])
def baseline_comparison() -> Response:
    global subject_manager
    data = request.get_json()
    label = data.get("label")
    if not label:
        return jsonify({'status': 'error', 'message': 'Label parameter is required'}), 400
    
    try:
        bio_baseline_data = next(
            (entry for entry in subject_manager.subject_data.get('Biometric_Baseline', [])
             if entry.get("label") == "baseline"),
            None
        )

        # Fetch session data by label
        bio_data = next(
            (entry for entry in subject_manager.subject_data.get('Biometric_Data', [])
             if entry.get("label") == label),
            None
        )

        if not bio_baseline_data:
            return jsonify({'status': 'error', 'message': 'No baseline data found'}), 404
        if not bio_data:
            return jsonify({'status': 'error', 'message': f'No data found for label: {label}'}), 404

        keys = ["EDA", "HR", "BI", "HRV"]

        baseline_means = {key: calculate_biometric_mean(bio_baseline_data, key) for key in keys}
        data_means = {key: calculate_biometric_mean(bio_data, key) for key in keys}

        return jsonify({'baseline_means': baseline_means, 'data_means': data_means})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    
@app.route('/reset_ser_question_index', methods=['POST'])
def reset_ser_question_index() -> Response:
    # TODO: implement test manager class and remove global reference
    global current_ser_question_index
    current_ser_question_index = 0

    test_manager.current_question_index = 0

    return jsonify({'status': 'SER questions reset'})

@app.route('/start_emotibit_stream', methods=['POST'])
def start_emotibit_stream() -> Response:
    start_emotibit()

    try:
        return jsonify({'message': 'Starting EmotiBit stream'})
    
    except Exception as e:
        return jsonify({'status': 'Error starting Emotibit stream', 'message': str(e)}), 400

@app.route('/push_emotibit_data', methods=['POST'])
def push_emotibit_data() -> Response:
    """
    Route for pushing EmotiBit data to the subject's data array.
    This route receives a JSON object with a label and pushes the current EmotiBit data to the subject's data array.
    The data is stored in the 'Biometric_Data' key of the subject's data dictionary.
    Returns:
        - Response: A JSON response indicating the status of the data push.
            If successful, returns {'message': 'Biometric data pushed to array with label: {label}'}.
            If an error occurs, returns {'status': 'error', 'message': str(e)} with a 400 status code.
    """
    global subject_manager, emotibit_streamer

    try:
        stop_emotibit()

        data = request.get_json()
        label = data.get('label')
        labeled_data = {"label": label, **{timestamp: value for timestamp, value in emotibit_streamer.data}}
        subject_manager.subject_data['Biometric_Data'].append(labeled_data)

        # Flush the streamer data
        if labeled_data in subject_manager.subject_data['Biometric_Data'] and labeled_data:
            del emotibit_streamer.data
            return jsonify({'message': f'Biometric data pushed to array with label: {label}, and streamer is flushed.'}), 200
        
        else:
            return jsonify({'message': f"The entry, {labeled_data}, does not exist or is empty, not deleting emotibit_streamer.data"}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/get_biometric_baseline', methods=['POST'])
def get_biometric_baseline() -> Response:
    global subject_manager
    try:
        stop_emotibit()

        data = emotibit_streamer.get_biometric_baseline()
        label = "baseline"
        labeled_data = {"label": label, **{timestamp: value for timestamp, value in data}}
        subject_manager.subject_data['Biometric_Baseline'].append(labeled_data)

        # Debug statement
        print(f"Biometric baseline data: {labeled_data}")

        return jsonify({'message': 'Baseline data collected.', 'data': data})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400 

@app.route('/get_ser_question', methods=['GET'])
def get_ser_question() -> Response:
    global current_ser_question_index, SER_QUESTIONS
    global recording_manager
    questions = SER_QUESTIONS.get('questions', [])
    
    try:
        if 0 <= current_ser_question_index < len(questions):
            question = questions[current_ser_question_index]['text']
            current_ser_question_index += 1
            return jsonify({'question': question})
        
        elif current_ser_question_index >= len(questions):
            recording_manager.stop_recording()
            # stop_recording()
            return jsonify({'question': 'SER task completed.'}), 200  

    except Exception as e:
        print(f"Error in get_ser_question: {e}") 
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/process_ser_answer', methods=['POST'])  
def process_ser_answer() -> Response:
    """
    Processes the user's spoken answer for a SER (Speech Emotion Recognition) question.
    This function performs the following steps:
    1. Stops the current audio recording.
    2. Loads the audio file with librosa.
    3. Resamples the audio signal.
    4. Predicts the emotion from the normalized audio signal with call to the ser_manager.
    5. Appends the predicted emotion to the subject's SER baseline data.
    6. Renames the audio file based on the subject's ID and the current question index.
    7. Saves the renamed audio file to the 'audio_files' directory.
    8. Returns a JSON response indicating the status of the submission.
    Returns:
        - Response: A JSON response with the status of the answer submission.
            If successful, returns {'status': 'Answer submitted.'}.
            If an error occurs, returns {'status': 'error', 'message': str(e)} with a 400 status code.
    """

    global RECORDING_FILE, subject_manager, ser_manager
    global current_ser_question_index, recording_manager, audio_file_manager

    recording_manager.stop_recording()

    try:
        sig, orig_sr = librosa.load(RECORDING_FILE, sr=None)
        sig_resampled = librosa.resample(sig, orig_sr=orig_sr, target_sr=16000)
        
        emotion, confidence = ser_manager.predict_emotion(sig_resampled)

        print(f"Predicted emotion: {emotion}, Confidence: {confidence}")
        ts = recording_manager.timestamp
        subject_manager.subject_data['SER_Baseline'].append({'timestamp': ts, 'emotion': emotion, 'confidence': confidence})
        
        id = subject_manager.subject_data['ID']
        file_name = f"ID_{id}_SER_question_{current_ser_question_index}.wav"
        file_name = audio_file_manager.rename_audio_file(id, "SER_question_", current_ser_question_index)
        audio_file_manager.save_audio_file(RECORDING_FILE, file_name, 'audio_files')

        return jsonify({'status': 'Answer submitted.'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/get_question', methods=['POST'])
def get_question() -> Response:
    """
    Retrieve the current question for the ongoing test.
    This route fetches the current question based on the global variables
    `current_question_index` and `current_test_number`. It accesses the
    `TASK_QUESTIONS` dictionary to get the list of questions for the current
    test. If there are no more questions in the current test, it increments
    the test number and resets the question index to 0 to fetch the next set
    of questions. If no questions are found for the current or next test,
    it returns a JSON response with `{"question": None}`.

    Returns:
        - Response: A JSON response containing the current question and the
            test number, or `{"question": None}` if no questions are available.
    """

    global current_question_index, current_test_number, TASK_QUESTIONS
    questions = TASK_QUESTIONS.get(current_test_number)

    if questions is None:
        return jsonify({"question": None})
    
    if current_question_index >= len(questions):
        current_test_number += 1
        current_question_index = 0
        questions = TASK_QUESTIONS.get(current_test_number)
        if questions is None:
            return jsonify({"question": None})
        
    question = questions[current_question_index]
    return jsonify({'question': question['question'], "test_number": current_test_number})

@app.route('/get_next_test', methods=['POST'])
def get_next_test() -> Response:
    global current_test_number, current_question_index, TASK_QUESTIONS

    if current_test_number >= 2:
        return jsonify({"message": "All tests completed."})
    else:
        current_test_number += 1
        current_question_index = 0
        questions = TASK_QUESTIONS.get(current_test_number)

        if questions is None:
            return jsonify({"message": "All tests completed."})
        
        return jsonify({"message": "Next test initiated.", "test_number": current_test_number})

@app.route('/get_stream_active', methods=['GET'])
def get_stream_active() -> Response:
    global recording_manager
    stream_is_active = recording_manager.get_stream_is_active()
    return jsonify({'stream_active': stream_is_active})

@app.route('/test_audio', methods=['POST'])
def test_audio() -> Response:
    global RECORDING_FILE, recording_manager
    try:
        # stop_recording()
        recording_manager.stop_recording()
        transcription = transcribe_audio(RECORDING_FILE)
        
        if transcription.startswith("Google Speech Recognition could not understand"):
            return jsonify({'result': 'error', 'result': 'error', 'message': "Sorry, I could not understand the response."}), 400
        
        if transcription.startswith("Could not request results"):
            return jsonify({'result': 'error', 'message': "Could not request results from Google Speech Recognition service."}), 400
                           
        else:
            return jsonify({'result': transcription})
    
    except sr.UnknownValueError:
        return jsonify({'status': 'error', 'message': "Sorry, I could not understand the response."}), 400
    
    except sr.RequestError as e:
        return jsonify({'status': 'error', 'message': f"Could not request results from Google Speech Recognition service; {e}"}), 500

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/submit_answer', methods=['POST'])
def submit_answer() -> Response:
    """
    Route to submit an answer for the current question in the test.
    This function handles the submission of an answer by performing the following steps:
        1. Stops the current audio recording.
        2. Transcribes the recorded audio.
        3. Predicts the emotion label.
        4. Saves the audio file with a specific naming convention.
        5. Appends the transcription and emotion prediction to the test data.
        6. Checks the transcription against the correct answer and determines if it is correct or incorrect.
        7. Increments the question index for the next question.
    Returns:
        - JSON response indicating the status of the submission and the result (correct/incorrect).
    Raises:
        - 400: If the transcription could not be understood or if there was an error requesting results from the speech recognition service.
        - 500: If there was any other error during the process.
    """

    global current_question_index, current_test_number
    global recording_manager, subject_manager, audio_file_manager, ser_manager
    global TASK_QUESTIONS, RECORDING_FILE

    questions = TASK_QUESTIONS.get(current_test_number)

    id = subject_manager.subject_data.get('ID')

    file_name = f"ID_{id}_test_{current_test_number}_question_{current_question_index}.wav"

    try:
        recording_manager.stop_recording()
        transcription = transcribe_audio(RECORDING_FILE)
        ts = recording_manager.timestamp
        try:
            sig, sr = librosa.load(RECORDING_FILE, sr=None)
            resampled_sig = librosa.resample(sig, orig_sr=sr, target_sr=16000)

            ser = ser_manager.predict_emotion(resampled_sig)
            audio_file_manager.save_audio_file(RECORDING_FILE, file_name, "audio_files")

        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

        subject_manager.subject_data["Test_Transcriptions"].append({'timestamp': ts, 'transcript': transcription, 'emotion':ser})
        
        if transcription.startswith("Google Speech Recognition could not understand"):
            return jsonify({'status': 'error', 'result': 'error', 'message': "Sorry, I could not understand the response."}), 400
        
        if transcription.startswith("Could not request results"):
            return jsonify({'status': 'error', 'message': "Could not request results from Google Speech Recognition service."}), 400
                           
        correct_answer = questions[current_question_index]['answer']
        result = 'incorrect'

        if check_answer(transcription, correct_answer):
            result = 'correct'

        current_question_index += 1

        return jsonify({'status': 'Answer submitted.', 'result': result})
    
    except sr.UnknownValueError:
        return jsonify({'status': 'error', 'message': "Sorry, I could not understand the response."}), 400
    
    except sr.RequestError as e:
        return jsonify({'status': 'error', 'message': f"Could not request results from Google Speech Recognition service; {e}"}), 500

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/shutdown', methods=['POST'])
def shutdown() -> Response:
    response = jsonify ({'message': 'Server shutting down...'})
    response.status_code = 200
    threading.Thread(target=shutdown_server).start() 

    return response

@app.route('/add_survey', methods=['POST'])
def add_survey() -> Response:
    global subject_manager, form_manager
    try:
        survey_name = request.form.get('surveyName')
        url = request.form.get('URL')
        form_manager.add_survey(survey_name, url)

        return jsonify({'message': 'Survey added successfully.'}), 200
  
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 400

@app.route('/submit_exit', methods=['POST'])
def submit_exit() -> Response:
    global subject_manager
    try:
        exit_survey_data = {
            'main_purpose': request.form.get('purpose'),
            'time_in_nature': request.form.get('time_in_nature'),
            'access_gardens': request.form.get('access_gardens'),
            'enjoy_time_natural': request.form.get('enjoy_time_natural'),
            'environment_preference': request.form.get('environment_preference'),
            'natural_elements': request.form.get('natural_elements'),
            'interior_preference': request.form.get('interior_preference'),
            'instructions': request.form.get('instructions'),
            'expectations': request.form.get('expectations'),
            'feedback': request.form.get('feedback')
        }

        subject_manager.subject_data['exit_survey_data'] = exit_survey_data 

        return jsonify({'message': 'Exit survey data submitted successfully.'}), 200
    
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 400

@app.route('/submit_student_data', methods=['POST'])
def submit_student_data() -> Response:
    """
    Route for submitting data for students with PID numbers and class information.
    This form will be kept local to server for simplicity.
    """
    global subject_manager

    try:
        student_data = {
            'PID': request.form.get('PID'),
            'class': request.form.get('class')
        }

        subject_manager.subject_data['student_data'] = student_data

        return jsonify({'message': 'Student data submitted successfully.'}), 200
    
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 400

@app.route('/upload_subject_data', methods=['POST'])    
def upload_subject_data() -> Response:
    global subject_manager, csv_handler

    try:
        csv_handler = CSVHandler(subject_manager)
        csv_handler.create_csv()

    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 400

@app.route('/submit', methods=['POST'])    
def submit() -> Response:
    global subject_manager, form_manager
    try:
        if request.method == 'POST':
            participant_name = request.form['name']
            email = request.form['email']   
            current_date = datetime.datetime.now().strftime('%Y-%m-%d')

            # NOTE: get_available_id() is a temporary test method to generate unique IDs
            # The aws_handler will assign the ID when subject instance is created
            # at the end of the test session
            unique_id = get_available_id()
            
            subject_manager.subject_data['Name'] = participant_name
            subject_manager.subject_data['Email'] = email
            subject_manager.subject_data['ID'] = unique_id
            subject_manager.subject_data['Date'] = current_date
            print("In HERE NOW")
            # Prep all forms with username and unique id
            form_manager.autofill_forms(participant_name, unique_id)
            print(form_manager.surveys)
            return jsonify({'message': 'User information submitted.'}), 200
        
    except Exception as e:
        return jsonify({'message': 'Error processing request.'}), 400
    
##################################################################
## Audio Routes
##################################################################
@app.route('/get_audio_devices', methods=['GET'])
def get_audio_devices() -> Response:
    global recording_manager
    audio_devices = recording_manager.get_audio_devices()
    return jsonify(audio_devices)

@app.route('/set_device', methods=['POST'])
def set_device() -> Response:
    global device_index
    global recording_manager
    data = request.get_json()

    p = pyaudio.PyAudio()
    device_index = int(data.get('device_index'))
    if device_index is not None:
        try:
            info = p.get_device_info_by_index(device_index)
            if info:
                device_index = info['index']
                recording_manager.set_device(info['index'])
                p.terminate()
                print(f'Device index set to: {device_index}')
                return jsonify({'message': 'Device index set.'})
            else:
                p.terminate()
                return jsonify({'message': 'Device index not found.'}), 400
            
        except Exception as e:
            return jsonify({'message': f'Error setting device index: {str(e)}'}), 400
    
    else:
        p.terminate()
        return jsonify({'message': 'Device index not provided.'}), 400
    
@app.route('/record_vr_task', methods=['POST'])
def record_vr_task() -> Response:
    """
    Endpoint to handle VR task recording actions.
    This function processes incoming JSON requests to start or stop a VR task recording.
    Depending on the action specified in the request, it either starts the recording or stops it
    and processes the recorded audio.
    The function performs the following actions:
        - If the action is 'start', it returns a success message. The actual "start_recording" route is called from the client.
        - If the action is 'stop', it stops the recording, splits the audio into segments, generates
            timestamps, transcribes the audio, predicts emotions, and stores the results in the subject data.
    Returns:
        - Response: A JSON response indicating the result of the action with an appropriate HTTP status code.
    Raises:
        - Exception: If any error occurs during the processing of the request, an error message is returned
                   with a 400 HTTP status code.
    """

    global recording_manager, ser_manager, subject_manager, audio_file_manager
    global RECORDING_FILE

    try:
        data = request.get_json()
        task_id = data.get('task_id')
        action = data.get('action')

        current_time_unix = int(time.time())

        if action == 'start':
            return jsonify({'message': 'Recording started.', 'task_id': task_id}), 200
        
        elif action == 'stop':
            recording_manager.stop_recording()
            
            audio_segments = audio_file_manager.split_wav_to_segments(task_id, RECORDING_FILE, 20, "tmp/")

            # Extract the index number from the filename to enforce sorting order
            audio_segments = sorted(audio_segments, key=lambda x: 
                                    int(os.path.splitext(os.path.basename(x))[0].split('_')[-1]))

            timestamps = generate_timestamps(current_time_unix, 20, "tmp/")
            
            transcriptions = []
            ser_predictions = []
            
            for segment_file in audio_segments:
                transcription = transcribe_audio(segment_file)
                transcriptions.append(transcription)

                # SER
                sig, sr = librosa.load(segment_file, sr=None)
                resampled_sig = librosa.resample(sig, orig_sr=sr, target_sr=16000)
                emotion = ser_manager.predict_emotion(resampled_sig)
                ser_predictions.append(emotion)

            vr_data = [{'timestamp': ts, 'transcription': tr, 'SER': ser} 
                    for ts, tr, ser in zip(timestamps, transcriptions, ser_predictions)]
            
            if task_id == 'taskID1':
                subject_manager.subject_data["VR_Transcriptions_1"] = vr_data
                
            elif task_id == 'taskID2':
                subject_manager.subject_data["VR_Transcriptions_2"] = vr_data

            audio_file_manager.backup_tmp_audio_files()

            return jsonify({'message': 'Audio successfully processed.', 'task_id': task_id}), 200
        else:
            print("Invalid Action")
            return jsonify({'message': 'Invalid action.'}), 400
    except Exception as e:
        print(f"Exception: {str(e)}")
        return jsonify({'message': 'Error processing request.'}), 400

@app.route('/start_recording', methods=['POST'])    
def start_recording() -> Response:
    global recording_manager
    try:
        recording_manager.start_recording()
        return jsonify({'status': 'Recording started.'}), 200
    except Exception as e:
        return jsonify({'status': 'Error starting recording.'}), 400

##################################################################
## Views 
##################################################################
@app.route('/')
def home() -> Response:
    return render_template('index.html')

@app.route('/break_page', methods=['GET'])
def break_page() -> Response:
    return render_template('break_page.html')

@app.route('/subject_gui', methods=['GET'])
def subject_gui() -> Response:
    return render_template('subject_gui.html')

@app.route('/video/<filename>')
def video(filename) -> Response:
    video_path = os.path.join('static', 'videos', filename)
    return send_file(video_path)

@app.route('/test_page', methods=['GET'])
def test_page() -> Response:
    global current_question_index, current_test_number, TASK_QUESTIONS
    current_question_index = 0
    current_test_number = 1

    return render_template('test_page.html')

@app.route('/survey/<survey_name>')
def survey(survey_name) -> Response:
    global form_manager
    survey = next((s for s in form_manager.surveys if s['name'] == survey_name), None)
    if survey and survey['url']:
        embed_url = survey['url']
        return render_template('survey.html', survey_name=survey_name, embed_url=embed_url)
    return "Survey not found or no URL provided.", 404

@app.route('/get_surveys', methods=['GET'])
def get_surveys() -> Response:
    global form_manager
    surveys = form_manager.surveys
    return jsonify(surveys)

@app.route('/vr_task', methods=['GET'])
def vr_task() -> Response:
    return render_template('vr_task.html')

@app.route('/pss4', methods=['GET'])
def pss4() -> Response:
    return render_template('pss4.html')

@app.route('/demographic_survey', methods=['GET'])
def demographic_survey() -> Response:
    return render_template('demographic_survey.html')

@app.route('/background', methods=['GET'])
def background() -> Response:
    return render_template('background.html')

@app.route('/exit_survey', methods=['GET'])
def exit_survey() -> Response:
    return render_template('exit_survey.html')

##################################################################
## Helper Functions 
##################################################################
def calculate_biometric_mean(data, key) -> float:
    global subject_manager
    try:
        values = [
            metrics[key] for timestamp, metrics in data.items()
            if timestamp != 'label' and metrics.get(key) is not None
        ]
        
        if not values:
            return None
        
        return sum(values) / len(values)
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

# Emotibit #######################################################
def start_emotibit() -> None:
    global emotibit_streamer

    try:
        emotibit_streamer.start()
        print("OSC server is streaming data.")

    except Exception as e:
        print(f"An error occurred while trying to start OSC stream: {str(e)}")

def stop_emotibit() -> None:
    global emotibit_streamer

    try:
        emotibit_streamer.stop()
    
    except Exception as e:
        print(f"An error occurred while trying to stop OSC stream: {str(e)}")

##################################################################
def preprocess_text(text) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()

def check_answer(transcription, correct_answers) -> bool:
    print(f"Transcription: {transcription}")
    transcription = preprocess_text(transcription)

    return any(word in correct_answers for word in transcription.split())

def is_folder_empty(app, folder_name) -> bool:
    folder_path = os.path.join(app.root_path, folder_name)
    return not os.path.exists(folder_path) or len(os.listdir(folder_path)) == 0

def initialize_ids(filename="available_ids.txt") -> None:
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            for i in range (1, 501):
                f.write(f"1_1_{i}\n")

# NOTE: This function only for test purposes
def get_available_id(filename='available_ids.txt') -> str:
    # TODO: The list of available ids should be determined by a call to the AWS server
    # and not by a txt file. This is a temporary solution until the server is set up.

    with open(filename, 'r') as f:
        ids = f.read().splitlines()
        if ids:
            assigned_id = ids[0]
            with open(filename, 'w') as f:
                f.write('\n'.join(ids[1:]))
            return assigned_id
        else:
            raise Exception('No more IDs available')
    
def shutdown_server() -> None:
    time.sleep(1)
    pid = os.getpid()
    os.kill(pid, signal.SIGINT)

def generate_timestamps(start_time_unix, segment_duration=20, output_folder="tmp/") -> list:
    """
    Generates a list of ISO 8601 formatted start timestamps for each audio segment file
    in the specified output folder, assuming they were created sequentially.
    Args:
        - start_time_unix (int): Unix timestamp of the start of the recording.
        - segment_duration (int): Duration of each segment in seconds.
        - output_folder (str): Folder containing the segment files.
    Returns:
        - List of start timestamps in ISO 8601 format for each segment.
    """
    segment_timestamps = []
    segment_files = sorted([f for f in os.listdir(output_folder) if f.endswith('.wav')])
    
    segment_timestamps = [
        datetime.datetime.fromtimestamp(start_time_unix + (i * segment_duration)).isoformat(timespec='seconds')
        for i in range(len(segment_files))
    ]
    
    return segment_timestamps

##################################################################
## Speech Recognition 
##################################################################
def transcribe_audio(file) -> str:
    #TODO: Remove global reference and uncomment below when recording_manager is implemented
    global recording_manager
    # RECORDING_FILE = recording_manager.get_recording_file() 

    recognizer = sr.Recognizer()
    with sr.AudioFile(file) as source:
        audio_data = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio_data)
        
        except sr.UnknownValueError:
            return "Google Speech Recognition could not understand the audio."
        
        except sr.RequestError as e:
            return f"Could not request results from Google Speech Recognition service; {e}"
    
##################################################################
## SER 
##################################################################

#TODO: Delete after SER class is finished
def set_aud_model(app) -> audonnx.Model:
    if is_folder_empty(app, 'model'):
        url = 'https://zenodo.org/record/6221127/files/w2v2-L-robust-12.6bc4a7fd-1.1.0.zip'
        cache_root = audeer.mkdir('cache')
        MODEL_ROOT = audeer.mkdir('model')
        archive_path = audeer.download_url(url, cache_root, verbose=True)
        audeer.extract_archive(archive_path, MODEL_ROOT)
        model = audonnx.load(MODEL_ROOT)
    else:
        cache_root = os.path.join(app.root_path, 'cache')
        MODEL_ROOT = os.path.join(app.root_path, 'model')
        model = audonnx.load(MODEL_ROOT)

    return model

# TODO: Delete after SER class is finished
def predict_emotion(audio_chunk) -> str:
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

def run_flask():
    app.run(debug=False, use_reloader=False)

####################################################################
# Main Loop
####################################################################
if __name__ == '__main__':
    # Suppress warnings 
    warnings.filterwarnings("ignore")

    # TODO: replace this with a call to the AWS server to retrieve the list of available IDs
    initialize_ids()

    TASK_QUESTIONS_1 = test_manager.get_task_questions()
    SER_QUESTIONS = test_manager.ser_questions
    AUDONNX_MODEL = set_aud_model(app)
    ser_manager.set_aud_model()

    CLF = joblib.load('classifier/emotion_classifier.joblib')

    # Debug must be set to false when Emotibit streaming code is active
    app.run(port=PORT_NUMBER,debug=False)
    
    # Uncomment when switching to pywebview
    # flask_thread = threading.Thread(target=run_flask)
    # flask_thread.daemon = True  
    # flask_thread.start()

    # window = webview.create_window("Pilot Server", "http://127.0.0.1:5000")

    # try:
    #     webview.start()
    # except Exception as e:
    #     print(f"Error: {e}")
    # finally:
    #     # Close the program when the webview window is closed
    #     sys.exit()