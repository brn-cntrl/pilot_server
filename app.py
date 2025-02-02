from flask import Flask, request, jsonify, render_template, render_template_string, redirect, send_file, Response
import webview
import warnings
import threading
from threading import Thread
import boto3
import os, sys
import datetime
import time
import pyaudio
import librosa
import signal 
import re
import speech_recognition as sr
from subject_manager_2 import SubjectManager
from recording_manager import RecordingManager
from test_manager import TestManager
from emotibit_streamer_2 import EmotiBitStreamer
from ser_manager3 import SERManager
from audio_file_manager import AudioFileManager
from form_manager import FormManager
from timestamp_manager import TimestampManager

app = Flask(__name__)
emotibit_thread = None

PORT_NUMBER = 8000
EMOTIBIT_PORT_NUMBER = 9005

# Class instances stored in global scope 
# NOTE: These could be moved to Flask g instance to further reduce global access
subject_manager = SubjectManager() 
recording_manager = RecordingManager('tmp/recording.wav') 
test_manager = TestManager()
emotibit_streamer = EmotiBitStreamer(EMOTIBIT_PORT_NUMBER)
audio_file_manager = AudioFileManager('tmp/recording.wav', 'tmp') # tmp folder is a backup in case the root isn't set
ser_manager = SERManager()
form_manager = FormManager()
timestamp_manager = TimestampManager()

##################################################################
## Routes 
##################################################################
@app.route('/set_event_marker', methods=['POST'])
def set_event_marker():
    global emotibit_streamer
    data = request.get_json()
    try:
        emotibit_streamer.event_marker = data.get('event_marker')
        print("Event marker set to: ", emotibit_streamer.event_marker)

        return jsonify({'status': 'Event marker set.'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/baseline_comparison', methods=['POST'])
def baseline_comparison() -> Response:
    global emotibit_streamer

    try:
        response = emotibit_streamer.compare_baseline()
        return jsonify({"message": response})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    
@app.route('/reset_ser_question_index', methods=['POST'])
def reset_ser_question_index() -> Response:
    global test_manager

    test_manager.current_ser_question_index = 0

    return jsonify({'status': 'SER questions reset'})

@app.route('/start_biometric_baseline', methods=['POST'])
def start_biometric_baseline() -> Response:
    global emotibit_streamer
    try:
        emotibit_streamer.start()
        emotibit_streamer.start_baseline_collection()
        return jsonify({'status': 'Collecting baseline data.'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400 
    
@app.route('/stop_biometric_baseline', methods=['POST'])
def stop_biometric_baseline() -> Response:
    global emotibit_streamer
    try:
        emotibit_streamer.stop_baseline_collection()
        return jsonify({'status': 'Baseline data collection stopped.'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    
@app.route('/get_ser_question', methods=['GET'])
def get_ser_question() -> Response:
    """
    Retrieve the current SER (Speech Emotion Recognition) question and increment the question index.
    This function fetches the current SER question from the test manager's list of questions,
    increments the question index, and returns the question in a JSON response. If the index
    exceeds the number of available questions, it stops the recording and resets the index.
    Returns:
        Response: A JSON response containing the current question or a completion message.
    Raises:
        Exception: If an error occurs during the process, a JSON response with the error message is returned.
    """
    global test_manager, recording_manager
    questions = test_manager.ser_questions.get('questions', [])
    
    try:
        if 0 <= test_manager.current_ser_question_index < len(questions):
            question = questions[test_manager.current_ser_question_index]['text']
            test_manager.current_ser_question_index += 1

            # DEBUG
            print(f"SER Question Index: {test_manager.current_ser_question_index}")
            print(f"SER Question: {question}")

            return jsonify({'message': 'Question found', 'question': question})
        
        elif test_manager.current_ser_question_index >= len(questions):
            recording_manager.stop_recording()
            # test_manager.current_ser_question_index = 0

            return jsonify({'message': 'SER task completed.'}), 200  

    except Exception as e:
        print(f"Error in get_ser_question: {e}") 
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/process_ser_answer', methods=['POST'])  
def process_ser_answer() -> Response:
    """
    Processes the user's spoken answer for a SER (Speech Emotion Recognition) question.
    This function performs the following steps:
    Set the event markers
    1. Stops the current audio recording.
    2. Renames the audio file based on the subject's ID and the current question index.
    3. Saves the renamed audio file to the 'audio_files' directory.
    4. Returns a JSON response indicating the status of the submission.
    Returns:
        - Response: A JSON response with the status of the answer submission.
            If successful, returns {'status': 'Answer submitted.'}.
            If an error occurs, returns {'status': 'error', 'message': str(e)} with a 400 status code.
    """
    global subject_manager, recording_manager, audio_file_manager, test_manager

    recording_manager.stop_recording()

    try:
        ts = recording_manager.timestamp
        id = subject_manager.subject_id

        file_name = f"{id}_{ts}_ser_baseline_question_{test_manager.current_ser_question_index}.wav"

        # DEBUG
        print(f"Audio File Name: {file_name}")

        # Header structure: 'Timestamp', 'Event_Marker', 'Transcription', 'SER_Emotion', 'SER_Confidence'
        subject_manager.append_data({'Timestamp': ts, 'Event_Marker': 'ser_baseline', 'Audio_File': file_name, 'Transcription': None, 'SER_Emotion': None, 'SER_Confidence': None})
        audio_file_manager.save_audio_file(file_name)

        return jsonify({'status': 'Answer processed successfully.'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/get_first_question', methods=['POST'])
def get_first_question() -> Response:
    global test_manager, recording_manager
    test_manager.current_question_index = 0
    questions = test_manager.get_task_questions(test_manager.current_test_index)
    try:
        if questions is None:
            return jsonify({"message": "No questions found."})
        else:
            recording_manager.start_recording()
            question = questions[test_manager.current_question_index]
            
            return jsonify({'message': 'Question found.', 'question': question['question'], "test_index": test_manager.current_test_index})
    except Exception as e:
        return jsonify({'message': 'Error getting first question.', 'error': str(e)}), 400
    
@app.route('/process_answer', methods=['POST'])
def process_answer() -> Response:
    """
    Process the answer submitted by the user.
    This function handles the following tasks:
    - Stops the current recording.
    - Retrieves the current test and its questions.
    - Extracts the test status from the request.
    - Generates a filename for the audio file based on the subject ID, timestamp, test, and question index.
    - Transcribes the audio file and saves it.
    - Appends the transcription and other data to the subject's data file.
    - Handles errors related to transcription.
    - Updates the test and question indices based on the test status and correctness of the answer.
    - Returns a JSON response indicating the status of the operation.
    Returns:
        Response: A Flask JSON response indicating the status and result of the operation.
    """

    global recording_manager, subject_manager, audio_file_manager, test_manager
    recording_manager.stop_recording()
    current_test = test_manager.current_test_index
    questions = test_manager.get_task_questions(current_test)
    test_ended = request.get_json().get('test_status')

    try:
        ts = recording_manager.timestamp
        id = subject_manager.subject_id

        file_name = f"{id}_{ts}_stressor_test_{current_test+1}_question_{test_manager.current_question_index}.wav"
        transcription = transcribe_audio(audio_file_manager.recording_file)
        audio_file_manager.save_audio_file(file_name)

        # Header structure: 'Timestamp', 'Event_Marker', 'Audio_File', 'Transcription', 'SER_Emotion', 'SER_Confidence'
        subject_manager.append_data({'Timestamp': ts, 'Event_Marker': f'stressor_test_{current_test+1}', 'Audio_File': file_name,'Transcription': transcription, 'SER_Emotion': None, 'SER_Confidence': None})

        
        if test_ended:
            if current_test < 1:
                test_manager.current_test_index += 1
            else:
                test_manager.current_test_index = 0
            return jsonify({'status': 'times_up.', 'message': 'Answer recorded and logged.'})
        
        else:
            if test_manager.current_question_index >= len(questions):
                test_manager.current_question_index = 0
                if current_test < 1:
                    test_manager.current_test_index += 1
                else:
                    test_manager.current_test_index = 0
                return jsonify({'status': 'complete', 'message': 'Answer recorded and logged.'})
            
            else:
                if transcription.startswith("Google Speech Recognition could not understand"):
                    return jsonify({'status': 'error', 'result': 'error', 'message': "Sorry, I could not understand the response."}), 400
    
                elif transcription.startswith("Could not request results"):
                    return jsonify({'status': 'error', 'message': "Could not request results from Google Speech Recognition service."}), 400
                
                correct_answer = questions[test_manager.current_question_index]['answer']
                result = 'incorrect'

                if test_manager.check_answer(transcription, correct_answer):
                    result = 'correct'
                    test_manager.current_question_index += 1
                
                recording_manager.start_recording()
                return jsonify({'status': 'Answer submitted and recording started...', 'result': result})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/get_current_test', methods=['POST'])
def get_current_test() -> Response:
    global test_manager
    print(f"Test Index: {test_manager.current_test_index}.")
    return jsonify({"test_number": test_manager.current_test_index})

@app.route('/get_stream_active', methods=['GET'])
def get_stream_active() -> Response:
    global recording_manager
    stream_is_active = recording_manager.stream_is_active
    return jsonify({'stream_active': stream_is_active})

@app.route('/submit_experiment', methods=['POST'])
def submit_experiment() -> Response:
    global subject_manager

    experiment_name = request.form.get('experiment_name')
    trial_name = request.form.get('trial_name')

    if not experiment_name or not trial_name:
        return jsonify({"error": "Missing experiment_name or trial_name"}), 400
    
    subject_manager.experiment_name = form_manager.clean_string(experiment_name)
    subject_manager.trial_name = form_manager.clean_string(trial_name)
    
    # DEBUG
    print("Subject Experiment: ", subject_manager.experiment_name)
    print("Subject Trial: ", subject_manager.trial_name)

    return jsonify({'message': 'Experiment and trial names submitted.'}), 200

@app.route('/upload_survey_file', methods=['POST'])
def upload_survey_csv() -> Response:
    global subject_manager, form_manager

    if subject_manager.subject_folder is None:
        return jsonify({'message': 'Subject information is not set.'}), 400
   
    try:
        if 'file' not in request.files:
            return jsonify({'message': 'No file part.'}), 400
        
        file = request.files['file']
        if not file.filename or not file.filename.lower().endswith(".csv"):
            return jsonify({"success": False, "error": "Invalid file type. Only CSV files are allowed."}), 400
        
        survey_found = form_manager.find_survey(file, subject_manager)
        if survey_found:
            return jsonify({'message': 'Survey data processed.'}), 200
        else:
            return jsonify({'message': 'Subject not found in survey data.'}), 400
    
    except Exception as e:
        return jsonify({'error': 'Error uploading file.'}), 400

@app.route('/upload_subject_data', methods=['POST'])
def upload_subject_data() -> Response:
    global subject_manager, emotibit_streamer
    try:
        emotibit_streamer.hdf5_to_csv()

        # TODO: Add code for uploading to MySQL

        return jsonify({'message': 'Subject biometric data processed.'}), 200

    except Exception as e:
        return jsonify({'error': 'Error processing subject data.'}), 400

@app.route('/submit', methods=['POST'])    
def submit() -> Response:
    """
    Handle the submission of user information and set up necessary resources for the experiment.
    This function performs the following steps:
    1. Validates that the experiment and trial names are set.
    2. Cleans and retrieves the subject's first name, last name, and email from the form data.
    3. Validates the email address format.
    4. Encrypts the subject's name and email to generate a unique subject ID.
    5. Cleans and retrieves the subject's PID and class name from the form data.
    6. Sets the subject information in the subject manager.
    7. Configures the audio file manager and emotibit streamer with the experiment, trial, and subject information.
    8. Generates custom URLs for the PSS4 and exit surveys.
    Returns:
        Response: A JSON response indicating the success or failure of the operation.
        - On success: Returns a JSON object with a success message and URLs for the PSS4 and exit surveys, with a 200 status code.
        - On failure: Returns a JSON object with an error message, with a 400 status code.
    """
    global subject_manager, form_manager, audio_file_manager, emotibit_streamer

    experiment_name = subject_manager.experiment_name
    trial_name = subject_manager.trial_name
    try:
        if experiment_name is None or trial_name is None:
            return jsonify({'message': 'Experiment and trial names must be set.'}), 400
        
        else:
            subject_first_name = form_manager.clean_string(request.form.get('first_name'))
            subject_manager.subject_first_name = subject_first_name
            subject_last_name = form_manager.clean_string(request.form.get('last_name'))
            subject_manager.subject_last_name = subject_last_name
            subject_email = request.form.get('email').lower().strip().replace(" ", "_")

            if not is_valid_email(subject_email):
                return jsonify({'message': 'Invalid email address.'}), 400
            
            subject_manager.subject_email = subject_email
            subject_id = encrypt_name(subject_first_name, subject_last_name, subject_email)
            subject_PID = form_manager.clean_string(request.form.get('PID')) 
            subject_class = form_manager.clean_string(request.form.get('class'))
            subject_manager.set_subject({"id": subject_id, "PID": subject_PID, "class_name": subject_class})
            audio_file_manager.set_audio_folder(experiment_name, trial_name, subject_id)
            emotibit_streamer.set_data_folder(experiment_name, trial_name, subject_id)
            emotibit_streamer.initialize_hdf5_file(subject_id)
            pss4 = form_manager.get_custom_url("pss4", subject_manager.subject_id)
            exit_survey = form_manager.get_custom_url("exit", subject_manager.subject_id)

            return jsonify({'message': 'User information submitted.', 'pss4': pss4, 'exit_survey': exit_survey}), 200
        
    except Exception as e:
        return jsonify({'message': 'Error processing request.'}), 400

@app.route('/encrypt_subject', methods=['POST'])
def encrypt_subject() -> Response:
    global form_manager

    first_name = form_manager.clean_string(request.form.get('first_name'))
    last_name = form_manager.clean_string(request.form.get('last_name'))
    email = request.form.get('email')

    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email address.'}), 400
    
    subject_id = encrypt_name(first_name, last_name, email)

    return jsonify({'message': subject_id})

@app.route('/decrypt_subject', methods=['POST'])
def decrypt_subject() -> Response:
    try:
        firstname, lastname, email = decrypt_name(request.form.get('id_string'))
        fullname = f"{firstname} {lastname}"

        return jsonify({'full_name': fullname, 'email': email})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/shutdown', methods=['POST'])
def shutdown() -> Response:
    response = jsonify ({'message': 'Server shutting down...'})
    response.status_code = 200
    threading.Thread(target=shutdown_server).start() 

    return response

##################################################################
## Audio Routes
##################################################################
@app.route('/test_audio', methods=['POST'])
def test_audio() -> Response:
    """
    Endpoint to test audio recording and transcription.
    This function stops the current audio recording, transcribes the audio file,
    and returns the transcription result in a JSON response. It handles various
    exceptions that may occur during the transcription process and returns
    appropriate error messages.
    Returns:
        Response: A JSON response containing the transcription result or an error message.
            - If transcription is successful, returns {'result': transcription}.
            - If transcription could not understand the audio, returns {'result': 'error', 'message': "Sorry, I could not understand the response."} with status code 400.
            - If there is a request error with the Google Speech Recognition service, returns {'result': 'error', 'message': "Could not request results from Google Speech Recognition service."} with status code 400.
            - If an unknown value error occurs, returns {'status': 'error', 'message': "Sorry, I could not understand the response."} with status code 400.
            - If a request error occurs, returns {'status': 'error', 'message': f"Could not request results from Google Speech Recognition service; {e}"} with status code 500.
            - If any other exception occurs, returns {'status': 'error', 'message': str(e)} with status code 500.
    """
    global recording_manager
    try:
        # stop_recording()
        recording_manager.stop_recording()
        transcription = transcribe_audio(recording_manager.recording_file)
        
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
    
@app.route('/get_audio_devices', methods=['GET'])
def get_audio_devices() -> Response:
    global recording_manager
    audio_devices = recording_manager.get_audio_devices()
    return jsonify(audio_devices)

@app.route('/set_device', methods=['POST'])
def set_device() -> Response:
    global recording_manager
    """
    Route for setting the audio device for the session.
    """
    data = request.get_json()
    device_index = int(data.get('device_index'))
    p = pyaudio.PyAudio()

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

@app.route('/record_task_audio', methods=['POST'])
def record_task_audio():
    """
    Handle audio recording tasks based on the provided action.
    This function processes JSON data from a request to either start or stop an audio recording.
    It manages the recording state, updates event markers, and saves audio files with appropriate metadata.
    Request JSON structure:
    {"action": "start" or "stop", "question": <question_number>,"event_marker": <event_marker_text>}
    Returns:
        Response: A JSON response with a message indicating the result of the action and an HTTP status code.
        - If action is 'start': {"message": "Recording started."}, 200
        - If action is 'stop':  {"message": "Recording stopped."}, 200
        - If action is invalid: {"message": "Invalid action."}, 400
    """
    global recording_manager, timestamp_manager, subject_manager
    data = request.get_json()
    action = data.get('action')
    question = data.get('question')
    event_marker = data.get('event_marker')
    event_marker = f"{event_marker}_question_{question}"

    try:
        if action == 'start':
            recording_manager.start_recording()
            emotibit_streamer.event_marker = event_marker
            start_time = 10 # seconds
            while not recording_manager.stream_is_active:
                if time.time() - start_time > 10:
                    return jsonify({'message': 'Error starting recording.'}), 400
                time.sleep(0.5)

            return jsonify({'message': 'Recording started...'}), 200
        
        elif action == 'stop':
            recording_manager.stop_recording()
            ts = recording_manager.timestamp
            id = subject_manager.subject_id

            file_name = f"{id}_{ts}_{event_marker}.wav"

            # Header structure: 'Timestamp', 'Event_Marker', 'Transcription', 'SER_Emotion', 'SER_Confidence'
            subject_manager.append_data({'Timestamp': ts, 'Event_Marker': event_marker, 'Audio_File': file_name, 'Transcription': None, 'SER_Emotion': None, 'SER_Confidence': None})
            audio_file_manager.save_audio_file(file_name)

            return jsonify({'message': 'Recording stopped.'}), 200
        else:
            return jsonify({'message': 'Invalid action.'}), 400
        
    except Exception as e:
        return jsonify({'error': 'Error processing request.'}), 400
      
@app.route('/record_task', methods=['POST'])
def record_task() -> Response:
    """
    Endpoint to handle general task audio recording.
    This function processes incoming JSON requests to start or stop audio recording.
    The function performs the following actions:
        - If the action is 'start', it returns a success message. The "start_recording" route is called from the client.
        - If the action is 'stop', it stops the recording, splits the audio into segments, generates
            timestamps, transcribes the audio, predicts emotions, and stores the results in the subject data.
    Returns:
        - Response: A JSON response indicating the result of the action with an appropriate HTTP status code.
    Raises:
        - Exception: If any error occurs during the processing of the request, an error message is returned
                   with a 400 HTTP status code.
    """
    global recording_manager, subject_manager, audio_file_manager
    global timestamp_manager, emotibit_streamer

    try:
        data = request.get_json()
        event_marker = data.get('event_marker')
        action = data.get('action')
        current_time_unix = timestamp_manager.get_timestamp()
        
        if action == 'start':
            recording_manager.start_recording()
            emotibit_streamer.event_marker = event_marker
            timeout = 10 # seconds
            start_time = time.time()
            # DEBUG
            print(f"EmbotiBit Event Marker: {emotibit_streamer.event_marker}")

            while not recording_manager.stream_is_active:
                if time.time() - start_time > timeout:
                    return jsonify({'message': 'Error starting recording.'}), 400
                time.sleep(0.5)

            return jsonify({'message': 'Recording started.'}), 200
        
        elif action == 'stop':
            recording_manager.stop_recording()

            # Handling the emotibit event marker in client "Task Completed" function.
            id = subject_manager.subject_id
            audio_segments = audio_file_manager.split_wav_to_segments(id, event_marker, audio_file_manager.recording_file, 20, "tmp/")

            audio_segments = sorted(audio_segments, key=lambda x: 
                                    int(os.path.splitext(os.path.basename(x))[0].split('_')[-1]))

            timestamps = generate_timestamps(current_time_unix, 20, "tmp/")

            task_data = [{'Timestamp': ts, 'Event_Marker': event_marker, 'Audio_File': fn, 'Transcription': None, 'SER_Emotion': None, 'SER_Confidence': None} 
                    for ts, fn, in zip(timestamps, audio_segments)]
            
            for data in task_data:
                subject_manager.append_data(data)
            
            audio_file_manager.backup_tmp_audio_files()

            return jsonify({'message': 'Audio successfully processed.', 'event_marker': event_marker}), 200
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
        start_time = time.time()

        timeout = 10 # seconds
        while not recording_manager.stream_is_active:
            if time.time() - start_time > timeout:
                return jsonify({'status': 'Error starting recording.'}), 400
            time.sleep(0.5)

        return jsonify({'status': 'Recording started.'}), 200
    except Exception as e:
        return jsonify({'status': 'Error starting recording.'}), 400

##################################################################
## Views 
##################################################################
@app.route('/prs')
def prs():
    import random
    AUDIO_DIR = 'static/prs_audio'
    intro = "1-PRS-Intro.mp3"
    prs_audio_files = [f for f in os.listdir(AUDIO_DIR) if f.endswith('.mp3') and f != intro]
    random.shuffle(prs_audio_files)
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PRS</title>
        <script src="{{ url_for('static', filename='js/scripts.js') }}"></script>
        <link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">
    </head>
    <body>
        <h1>PRS Task</h1>
        <h2> Instruction Text</h2>
        <ul>
            <li>For the next section of the experiment, we will be asking you to rate the extent to which a given statement describes your experience in this room.</li> 
            <li>The scale will be from 0 to 6. An answer of 0 means “Not at all” and an answer of 6 means “Completely”.</li> 
            <li>After each question, you can take as much time as you need to think about it before speaking your response aloud. Then, you will provide a reason for each rating you provide.</li> 
            <li>The statements will begin now. As a reminder, you will answer with a number from 0 to 6, with 0 being “Not at all” and 6 being “completely”.</li>
            <li>Please provide a brief explanation for your answer after each question.</li>
            <li>IMPORTANT: Click "Record Answer" and wait until you see the message, "Recording started" before you begin speaking your answer.</li>
            <li> Click "Stop Recording" when you are finished with your answer and explanation.</li>
        </ul><br><br>
        <div id="intro">
            <h3>Introduction</h3>
            <audio id="intro-audio-player" controls>
                <source src="{{ url_for('static', filename='prs_audio/' + intro) }}" type="audio/mpeg">
                Your browser does not support the audio element.
            </audio><br><br>
            <button onclick="startMonitoring()">Start Monitoring</button><br><br>
            <div class="meter"><div class="level"></div></div>
        </div><br>
        {% for audio in audio_files %}
        <div>
            <audio controls id="audio{{ loop.index }}-player">
                <source src="{{ url_for('static', filename='prs_audio/' + audio) }}" type="audio/mpeg">
                Your browser does not support the audio element.
            </audio>
            <div id="audio{{ loop.index }}-recording-status"></div>
            <button id="audio{{ loop.index }}-record-button" class="record-button">Record Answer</button><br><br>
        </div>
        {% endfor %}
        <script>
            recordButtons.forEach((button) => {
                button.addEventListener("click", async function () {
                    const audioElement = button.previousElementSibling.querySelector("source");
                    const statusElement = button.nextElementSibling;
                    
                    if (audioElement) {
                        const audioSrc = audioElement.getAttribute("src"); 
                        const fileName = audioSrc.split('/').pop();
                        const baseName = fileName.substring(0, fileName.lastIndexOf('.'));

                        if (button.innerText === 'Record Answer') {
                            statusElement.innerText = "Starting recording...";
                            try {
                                await startRecording();  // Wait for recording to start before updating UI
                                button.innerText = 'Stop Recording';
                                playBeep();
                            } catch (error) {
                                console.error("Recording failed:", error);
                            }
                        } else {
                            recordTask(eventMarker, 'stop', baseName, statusElement);
                            button.innerText = 'Record Answer';
                        }
                    }
                });
            });
        });
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template, intro=intro, audio_files=prs_audio_files)

@app.route('/room_observation')
def room_observation() -> Response:
    return render_template('room_observation.html')

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
    global test_manager
    # DEBUG
    print(f"Current quesiton index: {test_manager.current_question_index}")
    print(f"Current test index: {test_manager.current_test_index}")
    return render_template('test_page.html')

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
        return jsonify({'message': 'EmotiBit stream stopped.'}), 200
    
    except Exception as e:
        print(f"An error occurred while trying to stop OSC stream: {str(e)}")
        return jsonify({'error': 'Error stopping EmotiBit stream.'}), 400

# File and System Ops ############################################
def is_valid_email(email):
    """
    Validate if the provided email address is in a correct format.
    Args:
        email (str): The email address to validate.
    Returns:
        bool: True if the email address is valid, False otherwise.
    """

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return True
    else:
        return False

def encrypt_name(firstname: str, lastname: str, email: str) -> str:
    """Encrypts the subject's name and email into a reversible string."""
    
    firstname = firstname.lower().replace(" ", "_")
    lastname = lastname.lower().replace(" ", "_")
    email = email.lower()

    fullname = f"{firstname}_{lastname}"
    combined = f"{fullname}|{email}"
    obfuscated = "".join(chr(ord(c) + 3) for c in combined[::-1])

    return obfuscated

def decrypt_name(obfuscated: str) -> tuple:
    """Decrypts the obfuscated string back into the original name and email."""
    
    combined = "".join(chr(ord(c) - 3) for c in obfuscated)[::-1]
    name, email = combined.split("|", 1)
    firstname, lastname = name.split("_", 1)
    return firstname, lastname, email

def preprocess_text(text) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()

def check_answer(transcription, correct_answers) -> bool:
    print(f"Transcription: {transcription}")
    transcription = preprocess_text(transcription)

    return any(word in correct_answers for word in transcription.split())

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
    global recording_manager 

    recognizer = sr.Recognizer()
    with sr.AudioFile(file) as source:
        audio_data = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio_data)
        
        except sr.UnknownValueError:
            return "Google Speech Recognition could not understand the audio."
        
        except sr.RequestError as e:
            return f"Could not request results from Google Speech Recognition service; {e}"

def run_flask():
    app.run(debug=False, use_reloader=False)

####################################################################
# Main Loop
####################################################################
if __name__ == '__main__':
    # Suppress warnings 
    warnings.filterwarnings("ignore")

    # TODO: For now, debug must be set to false when Emotibit streaming code is active.
    # This is because the port used by the EmotiBit will report as in use when in debug mode.
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