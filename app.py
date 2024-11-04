from flask import Flask, request, jsonify, render_template, redirect, send_file
import warnings
import threading
from threading import Thread
import boto3
import joblib
import os
import datetime
import time
import pyaudio
import wave
import threading
import signal 
import json
import re
import speech_recognition as sr
import numpy as np
import audinterface
import audeer
import audonnx
from subject import Subject
from recording_manager import RecordingManager
from test_manager import TestManager
from emotibit_streamer import EmotiBitStreamer
from ser_manager import SERManager
import shutil

##################################################################
## Globals 
##################################################################
participant_name = " "
unique_id = None
device_index = 0
RECORDING_FILE = 'tmp/recording.wav'
AUDIO_SAVE_FOLDER = 'audio_files'
recording_process = None
current_question_index = 0
current_ser_question_index = 0
current_test_number = 1
stop_event = threading.Event()
recording_started_event = threading.Event()
recording_thread = None
# emotibit_thread = None
timestamp = None
stream_is_active = None
TASK_QUESTIONS_1 = None
TASK_QUESTIONS_2 = None
SER_QUESTIONS = None
PORT_NUMBER = 8000
EMOTIBIT_PORT_NUMBER = 9005

# Singletons stored in global scope NOTE: These could be moved to Flask g instance to further reduce global access
subject = Subject() 
recording_manager = RecordingManager() 
test_manager = TestManager()
emotibit_streamer = EmotiBitStreamer(EMOTIBIT_PORT_NUMBER)

# TODO: Delete after implementing classes
subject_data = {
    'ID': None,
    'Date': None,
    'Name': None,
    'Email': None,
    'Test_Transcriptions': [], # This will hold the transcript, SER values, and timestamps in JSON object format
    'VR_Transcriptions_1': [], # This will hold the VR transcript, SER values, and timestamps in JSON object format
    'VR_Transcriptions_2': [], # This will hold the VR transcript, SER values, and timestamps in JSON object format
    'Biometric_Baseline': [], # This will hold the biometric baseline data in JSON object format
    'Biometric_Data': [], # This will hold the biometric data in JSON object format
    'pss4_data': None,
    'background_data': None,
    'demographics_data': None,
    'exit_survey_data': None,
    'student_data': None
}

TASK_QUESTIONS = {}
MODEL_ROOT = "model"
AUDONNX_MODEL = None
CLF = None

DYNAMODB = boto3.resource('dynamodb', region_name='us-west-1')
TABLE = DYNAMODB.Table('Users')
ID_TABLE = DYNAMODB.Table('available_ids')

# Initialize the Flask app and pass reference to ser manager singleton
app = Flask(__name__)
ser_manager = SERManager(app)
##################################################################
## Routes 
##################################################################

def start_emotibit_stream():
    start_emotibit()

    try:
        return jsonify({'message': 'Starting EmotiBit stream'})
    
    except Exception as e:
        return jsonify({'status': 'Error starting Emotibit stream', 'message': str(e)}), 400

def get_biometric_baseline():

    try:
        stop_emotibit()
        data = emotibit_streamer.get_baseline_data()
        return jsonify({'message': 'Baseline data collected.', 'data': data})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400 

def get_ser_question():
    global current_ser_question_index, ser_questions
    
    questions = ser_questions.get('questions', [])
    
    try:
        if 0 <= current_ser_question_index < len(questions):
            question = questions[current_ser_question_index]['text']
            current_ser_question_index += 1
            return jsonify({'question': question})
        
        elif current_ser_question_index >= len(questions):
            stop_recording()
            return jsonify({'question': 'SER task completed.'}), 200  

    except Exception as e:
        print(f"Error in get_ser_question: {e}") 
        return jsonify({'status': 'error', 'message': str(e)}), 400
    
def process_ser_answer():
    global RECORDING_FILE
    global current_ser_question_index
    global subject_data

    stop_recording()

    try:
        sig = get_wav_as_np(RECORDING_FILE)
        normed_sig = normalize_audio(sig)
        print(normed_sig.shape)
        emotion = predict_emotion(normed_sig)

        id = subject_data.get('ID')
        file_name = f"ID_{id}_SER_question_{current_ser_question_index}.wav"
        file_name = rename_audio_file(id, "SER_question_", current_ser_question_index)
        save_audio_file(RECORDING_FILE, file_name, 'audio_files')

        return jsonify({'status': 'Answer submitted.', 'message': emotion})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    
def get_question():
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

def get_next_test():
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

def get_stream_active():
    global stream_is_active
    global recording_manager
    # stream_is_active = recording_manager.get_stream_is_active()
    return jsonify({'stream_active': stream_is_active})

def test_audio():
    try:
        stop_recording()
        transcription = transcribe_audio()
        print(transcription)
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

def submit_answer():
    global current_question_index, current_test_number, subject_data
    global stop_event, recording_thread, stream_is_active
    global TASK_QUESTIONS, RECORDING_FILE

    questions = TASK_QUESTIONS.get(current_test_number)

    id = subject_data.get('ID')

    # TODO Implement after subject class is finished and delete global reference
    # id = subject.get_id() 

    file_name = f"ID_{id}_test_{current_test_number}_question_{current_question_index}.wav"

    try:
        stop_recording()
        transcription = transcribe_audio()
        ts = get_timestamp()
        # ser = perform_ser()
        # Open audio file
        try:
            sig = get_wav_as_np(RECORDING_FILE)
            normed_sig = normalize_audio(sig)
            ser = predict_emotion(normed_sig)
            save_audio_file(RECORDING_FILE, file_name, "audio_files")

        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

        append_test_transcription(ts, transcription, ser)
        
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

def shutdown():
    shutdown_server()
    return jsonify({'message': 'Server shutting down...'})

def submit_pss4():
    global subject
    try:
        pss4 = {
            'response_1': request.form.get('controlFeeling1'),
            'response_1_other': request.form.get('otherText'),
            'response_2': request.form.get('controlFeeling2'),
            'response_3': request.form.get('controlFeeling3'),
            'response_4': request.form.get('controlFeeling4')
        }

        subject_data['pss4_data'] = pss4

        if subject:
            subject.set_pss4(pss4)
            # Debugging statement
            print(subject.get_pss4())

        else:
            print("Create instance of Subject first.")

        return jsonify({'message': 'PSS-4 submitted successfully.'}), 200
    
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 400
    
def submit_background():
    global subject
    try:
        background_data = {
            'rush_caffeine': request.form.get('rush_caffeine'),
            'caffeine_details': request.form.get('caffeine_details'),
            'caffeine_time': request.form.get('caffeine_time'),
            'thirst_hunger': request.form.get('thirst_hunger'),
            'heart_rate': request.form.get('heart_rate'),
            'neurological_conditions': request.form.get('neurological_conditions'),
            'neurological_description': request.form.get('neurological_description'),
            'scars_tattoos': request.form.get('scars_tattoos'),
            'vr_conditions': request.form.get('vr_conditions'),
            'vr_condition_description': request.form.get('vr_condition_description'),
            'glasses': request.form.get('glasses'),
        }

        subject_data['background_data'] = background_data # TODO: Delete after subject class tests

        if subject:
            subject.set_background_data(background_data)
            # Debugging statement
            print(subject.get_background_data())
        else:
            print("First create instance of Subject class")

        return jsonify({'message': 'Background data submitted successfully.'}), 200
    
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 400

def submit_exit():
    global subject
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

        subject_data['exit_survey_data'] = exit_survey_data # TODO: Delete after subject class tests

        if subject:
            subject.set_exit_survey_data(exit_survey_data)
            # Debugging statement
            print(subject.get_exit_survey_data())

        else:
            print("First create instance of Subject class")

        return jsonify({'message': 'Exit survey data submitted successfully.'}), 200
    
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 400

def submit_demographics():
    global subject
    try:
        demographics_data = {
            'age': request.form.get('age'),
            'gender': request.form.get('gender'),
            'education': request.form.get('education'),
            'childhood_setting': request.form.get('childhood_setting'),
            'current_living_setting': request.form.get('current_living_setting'),
            'exposure_to_nature': request.form.get('exposure_to_nature'),
            'access_to_green_spaces': request.form.get('access_to_green_spaces'),
            'preference_for_natural_environments': request.form.get('preference_for_natural_environments'),
            'environmental_preferences': request.form.get('environmental_preferences'),
            'preference_for_interior_design': request.form.get('preference_for_interior_design'),
            'work_study_environment': request.form.get('work_study_environment'),
            'current_mood': request.form.get('current_mood'),
            'stress_level': request.form.get('stress_level'),
            'physical_activity': request.form.get('physical_activity'),
            'sleep_quality': request.form.get('sleep_quality'),
            'previous_vr_experience': request.form.get('previous_vr_experience'),
            'comfort_with_vr': request.form.get('comfort_with_vr'),
        }

        subject_data['demographics_data'] = demographics_data

        if subject:
            subject.set_demographics_data(demographics_data)
            # Debugging statement
            print(subject.get_demographics_data())
        else:
            print("First create instance of Subject class")

        return jsonify({'message': 'Demographics data submitted successfully.'}), 200
    
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 400

def submit_student_data():
    global subject_data
    global subject
    try:
        student_data = {
            'PID': request.form.get('PID'),
            'class': request.form.get('class')
        }

        subject_data['student_data'] = student_data

        if subject:
            subject.set_student_data(student_data)
            # Debugging statement
            print(subject.get_student_data())
        else:
            print("First create instance of Subject class")

        return jsonify({'message': 'Student data submitted successfully.'}), 200
    
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 400
    
def upload_subject_data():
    global subject

    result = subject.upload_to_database()

    if result['status'] == 'error':
        raise Exception(result['message'])
    else:
        print(result['message'])
    
def submit():
    global unique_id
    global participant_name
    global subject

    try:
        if request.method == 'POST':
            participant_name = request.form['name']
            email = request.form['email']   
            current_date = datetime.datetime.now().strftime('%Y-%m-%d')

            # NOTE: This is a temporary test method to generate unique IDs
            # The aws_handler will assign the ID when upload_subject_data is called
            # at the end of the test session
            unique_id = get_available_id()
            
            if subject:
                subject.set_name(participant_name)
                subject.set_email(email)
                subject.set_id(unique_id)
                subject.set_csv_filename()
            else:
                print("Create instance of Subject class first.")

            # TODO: Remove line setting unique_id when AWS server is ready
            # TODO: Remove block after subject class implemented
            subject_data['ID'] = unique_id
            subject_data['Name'] = participant_name
            subject_data['Date'] = current_date
            subject_data['Email'] = email

            return jsonify({'message': 'User information submitted.'}), 200
        
    except Exception as e:
        return jsonify({'message': 'Error processing request.'}), 400

##################################################################
## Audio Recording Routes
##################################################################
def record_vr_task():
    global subject_data, subject
    global recording_manager, ser_manager
    global stream_is_active, stop_event

    try:
        data = request.get_json()
        task_id = data.get('task_id')
        action = data.get('action')
        # Debug statement
        print(f"Received task_id: {task_id}, action: {action}")
        current_time_unix = int(time.time())

        if action == 'start':
            # max_attempts = 10
            # attempts = 0
            # # Check for active stream and break after 10 attempts
            # while not stream_is_active and attempts < max_attempts:
            #     time.sleep(2)
            #     attempts += 1
            #     # stream_is_active = recording_manager.get_stream_is_active()
            
            return jsonify({'message': 'Recording started.', 'task_id': task_id}), 200
        
        # if not stream_is_active:
        #     return jsonify({'message': 'Recording could not be started.'}), 400
        
        elif action == 'stop':
            stop_recording()
            # stop_event = recording_manager.get_stop_event()
            if not stop_event or not stop_event.is_set():
                return jsonify({'message': 'Error stopping recording.'}), 400
            else:
                # ts = get_timestamp()
                # vr_transcript = transcribe_vr_audio(ts, task_id)

                vr_transcript = process_audio_segments(current_time_unix, task_id)

                # TODO: Uncomment after all classes implemented and delete global references
                # vr_transcript = recording_manager.process_audio_segments(subject, ser_manager, current_time_unix, task_id)

                if task_id == 'taskID1':
                    subject_data['VR_Transcriptions_1'] = vr_transcript 
                    # TODO: Uncomment after subject class is implemented and delete global reference
                    # if subject:
                    #     subject.set_vr_transcriptions_1(vr_transcript)
                    #     # Debugging statement
                    #     print(subject.get_vr_transcriptions_1())
                    # else:
                    #     print("Create instance of Subject class first.")

                elif task_id == 'taskID2':
                    subject_data['VR_Transcriptions_2'] = vr_transcript # TODO: Delete after subject class is implemented
                    # if subject:
                    #     subject.set_vr_transcriptions_2(vr_transcript)
                    #     # Debugging statement
                    #     print(subject.get_vr_transcriptions_2())
                    # else:
                    #     print("Create instance of Subject class first.")

                else:
                    return jsonify({'message': 'All tasks completed.'}), 400
                
                # Debugging statement
                print(f"subject vr transcripts 1: {subject_data['VR_Transcriptions_1']}")

                delete_recording_file(RECORDING_FILE)

                return jsonify({'message': 'Recording stopped.', 'task_id': task_id}), 200

    except Exception as e:
        return jsonify({'message': 'Error processing request.'}), 400
    
def start_recording():
    try:
        record_audio()
        return jsonify({'status': 'Recording started.'}), 200
    except Exception as e:
        return jsonify({'status': 'Error starting recording.'}), 400

##################################################################
## Views 
##################################################################
def index():
    return render_template('index.html')

def break_page():
    return render_template('break_page.html')

def video(filename):
    video_path = os.path.join('static', 'videos', filename)
    return send_file(video_path)

def test_page():
    global current_question_index, current_test_number, TASK_QUESTIONS
    current_question_index = 0
    current_test_number = 1

    return render_template('test_page.html')

def vr_task():
    return render_template('vr_task.html')

def pss4():
    return render_template('pss4.html')

def demographic_survey():
    return render_template('demographic_survey.html')

def background():
    return render_template('background.html')

def exit_survey():
    return render_template('exit_survey.html')

##################################################################
## Helper Functions 
##################################################################
# def record_timestamps(timestamps):  # For use in thread
#     while not stop_event.is_set():
#         timestamps.append(datetime.datetime.now().isoformat())
#         time.sleep(10)

def start_emotibit():
    # global emotibit_thread, emotibit_streamer
    global emotibit_streamer

    try:
        # emotibit_thread = Thread(target=emotibit_streamer.start)
        # emotibit_thread.start()
        emotibit_streamer.start()
        print("OSC server is streaming data.")

    except Exception as e:
        print(f"An error occurred while trying to start OSC stream: {str(e)}")

def stop_emotibit():
    # global emotibit_thread, emotibit_streamer
    global emotibit_streamer

    try:
        # if emotibit_thread is not None and emotibit_thread.is_alive():
        #     emotibit_streamer.stop()
        #     emotibit_thread.join()
        #     print("OSC server stopped.")
        emotibit_streamer.stop()
    
    except Exception as e:
        print(f"An error occurred while trying to stop OSC stream: {str(e)}")
    
# def biometric_baseline():
#     global emotibit_streamer
    
#     try:
#         emotibit_thread = Thread(target=emotibit_streamer.start)
#         emotibit_thread.start()

#         time.sleep(10)  # Collect data for 10 seconds

#         emotibit_streamer.stop()
#         emotibit_thread.join()

#         eda_data = emotibit_streamer.get_eda_data() # TODO: Implement all streams and call get_data() instead of get_eda_data()

#         return eda_data

#     except Exception as e:
#         print("An error occurred while trying to start stream.")
#         return []

# def stop_emotibit_stream():
#     global emotibit_streamer
#     emotibit_streamer.stop()

def set_timestamp(t):   
    global timestamp
    timestamp = t

def get_timestamp():
    global timestamp
    return timestamp

def preprocess_text(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()

def check_answer(transcription, correct_answers):
    print(f"Transcription: {transcription}")
    transcription = preprocess_text(transcription)

    return any(word in correct_answers for word in transcription.split())

# Saves to file at root of the project. Transcriptions are appended when "submit_answer" is called
def append_test_transcription(timestamp, transcription, ser):
    global subject, subject_data
    entry = {
        'timestamp': timestamp,
        'transcription': transcription,
        'ser': ser
    }

    # Append to the json data
    try:
        subject_data['Test_Transcriptions'].append(entry) # TODO: Delete once subject class is fully implemented
        if subject:
            subject.append_test_transcription(entry)
        else:
            print("Create instance of Subject class first.")

    except Exception as e:
        print(f"Error appending to JSON: {e}")

def is_folder_empty(app, folder_name):
    folder_path = os.path.join(app.root_path, folder_name)
    return not os.path.exists(folder_path) or len(os.listdir(folder_path)) == 0

def initialize_ids(filename="available_ids.txt"):
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            for i in range (1, 501):
                f.write(f"1_1_{i}\n")

# NOTE: This function only for test purposes
def get_available_id(filename='available_ids.txt'):
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
    
def shutdown_server():
    pid= os.getpid()
    os.kill(pid, signal.SIGINT)

def prime_test():
    global TASK_QUESTIONS_1, TASK_QUESTIONS_2, TASK_QUESTIONS
    with open('task_1_data.json', 'r') as f:
        TASK_QUESTIONS_1 = json.load(f)
        # print(TASK_QUESTIONS_1)
    with open('task_2_data.json', 'r') as f:
        TASK_QUESTIONS_2 = json.load(f)
        # print(TASK_QUESTIONS_2)
    TASK_QUESTIONS = {
        1: TASK_QUESTIONS_1,
        2: TASK_QUESTIONS_2
    }

def prime_ser_task():
    ser_questions = None
    try:
        with open('SER_questions.json', 'r') as f:
            ser_questions = json.load(f)
        return ser_questions
    except Exception as e:
        print(f"An error occurred: {str(e)}")

##################################################################
## Audio 
##################################################################
def record_audio():
    global stop_event
    global recording_thread
    global timestamp
    global recording_started_event
    # global recording_manager
    # Reset the stop event to false

    # recording_manager.start_recording()
    # t = recording_manager.get_timestamp()
    stop_event.clear()
    recording_started_event.clear()

    t = datetime.datetime.now().isoformat()
    set_timestamp(t)

    recording_thread = threading.Thread(target=record_thread)
    recording_thread.start()
    recording_started_event.wait()

    print("Recording thread started.")

def stop_recording():
    global recording_thread, stop_event, stream_is_active
    # global recording_manager

    # recording_manager.stop_recording()
    stop_event.set()
    stream_is_active = False
    # Wait for recording thread to finish
    recording_thread.join()

# TODO: Delete all audio functions after recording manager class is fully implemented
# Record audio in separate thread
def record_thread():
    global RECORDING_FILE
    global stop_event
    global recording_started_event
    global stream_is_active

    audio = pyaudio.PyAudio()
    stream = audio.open(format=pyaudio.paInt16, 
                        channels=1, 
                        rate=44100, 
                        input=True, 
                        input_device_index=device_index,
                        frames_per_buffer=1024)
    
    frames = []

    recording_started_event.set()
    stream_is_active = stream.is_active()
    while not stop_event.is_set():
        data = stream.read(1024)
        frames.append(data)
    
    # Save to wav after exiting while loop
    stream.stop_stream()
    stream.close()
    audio.terminate()

    with wave.open(RECORDING_FILE, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(44100)
        wf.writeframes(b''.join(frames))

    print(f"Recording stopped, saved to {RECORDING_FILE}")
        
def get_wav_as_np(filename):
    """
    This function loads the entire wav file stored in tmp and returns it as a 
    normalized numpy array.
    """
    try:
        with wave.open(filename, 'rb') as wf:
            num_channels = wf.getnchannels()
            num_frames = wf.getnframes()
            signal = wf.readframes(num_frames)
            signal = np.frombuffer(signal, dtype=np.int16).astype(np.float32)
            signal = signal / np.iinfo(np.int16).max

            if num_channels == 2:
                signal = signal.reshape(-1, 2)
                signal = signal.mean(axis=1)

            return signal
    except Exception as e:
        print("Couldn't locate an audio file.")
        return None
    
def get_audio_chunk_as_np(filename, offset=0, duration=None, sample_rate=16000):
    """
    This function returns the section of audio specified by the offset and 
    duration parameters as a normalized numpy array. This is necessary for the
    current SER classifier and is subject to change.
    """
    try:
        with wave.open(filename, 'rb') as wf:
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
                signal = resample_audio(signal, original_sample_rate, sample_rate)

            return signal
        
    except Exception as e:
        print(f"An error occurred while processing the audio: {e}")
        return None

def resample_audio(signal, original_sample_rate, target_sample_rate):
    """
    Resamples the signal to match the target sample rate using linear interpolation.
    """
    ratio = target_sample_rate / original_sample_rate
    resampled_length = int(len(signal) * ratio)
    resampled_signal = np.interp(
        np.linspace(0, len(signal) - 1, resampled_length), np.arange(len(signal)), signal
    )
    return resampled_signal

def get_audio_duration(file_path):
    with wave.open(file_path, 'rb') as wf:
        frames = wf.getnframes()          
        rate = wf.getframerate()          
        duration = frames / float(rate)   
    return duration

def rename_audio_file(id, name_param1, name_param2):
    filename = f"ID_{id}_{name_param1}_{name_param2}.wav"

    return filename

def save_audio_file(old_path_filename, new_filename, save_folder):
    try:
        os.makedirs(save_folder, exist_ok=True)
        new_filename = os.path.join(save_folder, new_filename)
        #TODO: change function so that source folder and filename are separate. Get rid of global filename.
        shutil.copy(old_path_filename, new_filename)

        print(f"File '{old_path_filename}' saved successfully.")
    except PermissionError:
        print(f"Permission denied: Unable to save file '{old_path_filename}'. Check file permissions.")
    except FileNotFoundError:
        print(f"File not found: '{old_path_filename}' might have already been deleted.")
    except Exception as e:
        print(f"An error occurred while trying to save the file '{old_path_filename}': {str(e)}")

def delete_recording_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"File '{file_path}' deleted successfully.")
        else:
            print(f"File '{file_path}' does not exist.")
    except PermissionError:
        print(f"Permission denied: Unable to delete file '{file_path}'. Check file permissions.")
    except FileNotFoundError:
        print(f"File not found: '{file_path}' might have already been deleted.")
    except Exception as e:
        print(f"An error occurred while trying to delete the file '{file_path}': {str(e)}")

def normalize_audio(audio): # Necessary for SER task
    audio_array = audio / np.max(np.abs(audio))
    return audio_array

def process_audio_segments(ts, prefix):
    """
    This function processes the audio segments in 20.
    -second chunks and returns a list of transcriptions
    with timestamps and SER values in JSON object format.
    """
    global RECORDING_FILE
    global recording_manager, subject, subject_data
    initial_timestamp = ts
    recognizer = sr.Recognizer()
    audio_segments = []

    with wave.open(RECORDING_FILE, 'rb') as wf:
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        total_frames = wf.getnframes()
        duration = total_frames / float(sample_rate)

        segment_duration = 20
        segment_frames = int(segment_duration * sample_rate)
        total_segments = int(duration // segment_duration)

        for i in range(total_segments + 1): # Include last segment if remainder exists
            start_time = initial_timestamp + i * segment_duration
            iso_timestamp = datetime.datetime.fromtimestamp(start_time).isoformat()
            wf.setpos(i * segment_frames)

            frames = wf.readframes(segment_frames)
            if(len(frames) == 0):
                break # EOF

            temp_file = f"tmp/temp_segment_{i}.wav"

            #TODO: Implement after subject class is finished and delete global reference
            # id = subject.get_id()
            id = subject_data.get('ID')

            # save_file = f"audio_save_folder/ID_{id}_{prefix}_segment_{i}.wav"

            with wave.open(temp_file, 'wb') as wf_temp:
                wf_temp.setnchannels(channels)
                wf_temp.setsampwidth(wf.getsampwidth())
                wf_temp.setframerate(sample_rate)
                wf_temp.writeframes(frames)

            with sr.AudioFile(temp_file) as source:
                audio_data = recognizer.record(source)
                try:
                    recognized_text = recognizer.recognize_google(audio_data)
                    sig = get_wav_as_np(temp_file)
                    emotion = predict_emotion(sig)

                    transcription_data = {
                        'timestamp': iso_timestamp,
                        'recognized_text': recognized_text,
                        'emotion': emotion
                    }

                    audio_segments.append(transcription_data)
                except sr.UnknownValueError:
                    print(f"Google Speech Recognition could not understand the audio at {start_time:.2f}.")
                except sr.RequestError as e:
                    print(f"Error with the recognition service: {e}")

                # Cleanup
                file_name = rename_audio_file(id, prefix, f"segment_{i}")
                save_audio_file(RECORDING_FILE, file_name, 'audio_files')
                os.remove(temp_file)

    try:
        # Debug statement
        print(audio_segments)
        return audio_segments
    
    except Exception as e:
        print(f"An error occurred: {str(e)}") 
        return []

##################################################################
## Speech Recognition 
##################################################################
def transcribe_audio():
    global RECORDING_FILE #TODO: Remove when recording_manager is implemented
    global recording_manager
    # RECORDING_FILE = recording_manager.get_recording_file() #TODO - Implement this when recording manager is finished

    recognizer = sr.Recognizer()
    with sr.AudioFile(RECORDING_FILE) as source:
        audio_data = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio_data)
        
        except sr.UnknownValueError:
            return "Google Speech Recognition could not understand the audio."
        
        except sr.RequestError as e:
            return f"Could not request results from Google Speech Recognition service; {e}"

# NOTE: Leave this function in place for now.
# def transcribe_vr_audio(start_time, task_id):
#     """ 
#     This function transcribes the audio file in chunks of 5 seconds and returns a list of
#     transcriptions with timestamps and SER values in json format.
#     """
#     global RECORDING_FILE
#     global recording_manager

#     # RECORDING_FILE = recording_manager.get_recording_file() #TODO - Implement this when recording manager is finished
#     recording_start_time = datetime.datetime.fromisoformat(start_time)
#     recognizer = sr.Recognizer()
#     vr_transcriptions = []  
    
#     with sr.AudioFile(RECORDING_FILE) as source:
#         try:
#             duration = get_audio_duration(RECORDING_FILE)
#             print(f"Audio duration: {duration}")

#             chunk_duration = 5
#             current_time = 0

#             if chunk_duration > duration:
#                 print(f"Error: Chunk duration ({chunk_duration} seconds) exceeds audio file duration ({duration} seconds).")
#                 return []
        
#             while current_time + chunk_duration <= duration:
#                 print(f"Transcribing from offset {current_time} seconds...") 
#                 try:
#                     remaining_time = duration - current_time
#                     chunk_time = min(chunk_duration, remaining_time)
#                     audio_chunk = recognizer.record(source, duration=chunk_time, offset=current_time)
#                     recognized_text = recognizer.recognize_google(audio_chunk)
#                     sig = get_audio_chunk_as_np(RECORDING_FILE, offset=current_time, duration=chunk_duration)
#                     # sig = recording_manager.get_audio_chunk_as_np(current_time, chunk_duration)
#                     # normed_sig = normalize_audio(sig)
#                     emotion = predict_emotion(sig)
#                     real_timestamp = recording_start_time + datetime.timedelta(seconds=current_time)
#                     real_timestamp_iso = real_timestamp.isoformat()

#                     transcription_data = {
#                         'taskID': task_id,
#                         'timestamp': real_timestamp_iso,
#                         'recognized_text': recognized_text,
#                         'emotion': emotion
#                     }

#                     vr_transcriptions.append(transcription_data)
#                     current_time += chunk_duration

#                 except sr.UnknownValueError:
#                     print(f"Google Speech Recognition could not understand the audio  at{current_time:.2f}.")
#                     current_time += chunk_duration
#                 except sr.RequestError as e:
#                     print(f"Error with the recognition service: {e}")
#                     break
                
#             return vr_transcriptions
        
#         except Exception as e:
#             print(f"An error occurred: {str(e)}")
#             return []
    
################################################
## SER 
################################################

#TODO: Delete after SER class is finished
def set_aud_model(app):
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
def predict_emotion(audio_chunk):
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

################################################

def get_audio_devices():
    audio_devices = fetch_audio_devices()
    # global recording_manager
    # audio_devices = recording_manager.get_audio_devices()
    return jsonify(audio_devices)

def set_device():
    global device_index
    global recording_manager
    data = request.get_json()
    print(f'Received data: {data}')  # Debugging statement

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
    
def fetch_audio_devices():
    p = pyaudio.PyAudio()
    audio_devices = [{'index': i, 'name': p.get_device_info_by_index(i)['name']}
                     for i in range(p.get_device_count())
                     if p.get_device_info_by_index(i)['maxInputChannels'] > 0]
    
    p.terminate()

    return audio_devices

# Register Views
app.add_url_rule('/', 'index', index)
app.add_url_rule('/break_page', 'break_page', break_page, methods=['GET'])
app.add_url_rule('/test_page', 'test_page', test_page, methods=['GET'])
app.add_url_rule('/vr_task', 'vr_task', vr_task, methods=['GET'])
app.add_url_rule('/pss4', 'pss4', pss4, methods=['GET'])
app.add_url_rule('/demographic_survey', 'demographic_survey', demographic_survey, methods=['GET'])
app.add_url_rule('/background', 'background', background, methods=['GET'])
app.add_url_rule('/exit_survey', 'exit_survey', exit_survey, methods=['GET'])

# Register Routes
app.add_url_rule('/get_ser_question', 'get_ser_question', get_ser_question, methods=['GET'])
app.add_url_rule('/process_ser_answer', 'process_ser_answer', process_ser_answer, methods=['POST'])
app.add_url_rule('/get_question', 'get_question', get_question, methods=['POST'])
app.add_url_rule('/get_next_test', 'get_next_test', get_next_test, methods=['POST'])
app.add_url_rule('/get_stream_active', 'get_stream_active', get_stream_active, methods=['GET'])
app.add_url_rule('/submit_answer', 'submit_answer', submit_answer, methods=['POST'])
app.add_url_rule('/shutdown', 'shutdown', shutdown, methods=['POST'])
app.add_url_rule('/upload_subject_data', 'upload_subject_data', upload_subject_data, methods=['POST'])
app.add_url_rule('/submit', 'submit', submit, methods=['POST'])
app.add_url_rule('/get_audio_devices', 'get_audio_devices', get_audio_devices, methods=['GET'])
app.add_url_rule('/set_device', 'set_device', set_device, methods=['POST'])
app.add_url_rule('/test_audio', 'test_audio', test_audio, methods=['POST'])
app.add_url_rule('/record_vr_task', 'record_vr_task', record_vr_task, methods=['POST'])
app.add_url_rule('/start_recording', 'start_recording', start_recording, methods=['POST'])
app.add_url_rule('/video/<filename>', 'video', video)
app.add_url_rule('/submit_pss4', 'submit_pss4', submit_pss4, methods=['POST'])
app.add_url_rule('/submit_background', 'submit_background', submit_background, methods=['POST'])
app.add_url_rule('/submit_exit', 'submit_exit', submit_exit, methods=['POST'])
app.add_url_rule('/submit_demographics', 'submit_demographics', submit_demographics, methods=['POST'])
app.add_url_rule('/submit_student_data', 'submit_student_data', submit_student_data, methods=['POST'])
app.add_url_rule('/start_emotibit_stream', 'start_emotibit_stream', start_emotibit_stream, methods=['POST'])
app.add_url_rule('/get_biometric_baseline', 'get_biometric_baseline', get_biometric_baseline, methods=['GET'])

######################################################
# Main Loop
######################################################
if __name__ == '__main__':
    # Suppress warnings for now
    warnings.filterwarnings("ignore")

    # TODO: replace this with a call to the AWS server to retrieve the list of available IDs
    initialize_ids()

    # Load in the json data
    prime_test()
    
    # Set up SER
    ser_questions = prime_ser_task()
    AUDONNX_MODEL = set_aud_model(app)

    # TODO: Uncomment after ser_manager class is finished and delete global model reference
    # AUDONNX_MODEL = ser_manager.set_aud_mode()

    CLF = joblib.load('classifier/emotion_classifier.joblib')

    app.run(port=PORT_NUMBER,debug=False)