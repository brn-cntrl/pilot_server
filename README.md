# Pilot Experiment Server

## A command center for running all applications during experiment

**Dependencies to run the server**
* Flask
* Pyaudio (for handling audio device)
* Portaudio 
* Audonnx (SER model to TBD)
* Boto3

**Installation**

*Please note that all installation will soon be handled with PyInstaller.

Install Flask: 

    pip install flask
To install Homebrew, run the following command in Terminal:

    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
Install portaudio with:

    brew install portaudio
Install pyaudio with:

    pip install pyaudio

**NOTE:** The best way to install Pyaudio and Portaudio on Mac is with HomeBrew. 

**Instructions for server**

To run the server, simply open a terminal, navigate to the root folder and type:
python exp_server.py

You should see the following result in Terminal: 
 
    * Serving Flask app 'exp_serve'
    * Debug mode: on
    WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
    * Running on http://127.0.0.1:5000
    Press CTRL+C to quit
    * Restarting with watchdog (fsevents)
    * Debugger is active!
    * Debugger PIN: 122-354-517

* On Mac, CMD+click on the listed http address and the server will launch a webpage in your default browser
* To shutdown the server in the browser, click "Shutdown Server"
* To shutdown in terminal, run "ctrl+c"

**NOTE:** DO NOT remove the any of the html pages from the templates folder. This is where Flask will always look for them. Your home http address may vary.


### Transcription and SER

**Install Dependencies**

* Install Audonnx with:

        pip install audonnx

* Install SpeechRecognition for Python with: 

        pip install SpeechRecognition


**NOTE** The classifier used for SER is included in this repository. The use of the classifier and audonnx is likely to change once a more accurate SER classifier is identified.


### AWS Client 
**Installation**

Install the AWS SDK with: 

    pip install boto3

Download the the AWS CLI package with: 

    curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"

Install the AWS CLI with: 

    sudo installer -pkg ./AWSCLIV2.pkg -target /

**Instructions**

**Setup AWS Credentials**

* In terminal, run: aws configure
* Enter the AWS access key (to be provided)
* Enter the AWS secret access key (to be provided)
* Enter the default region name (us-west-2)
* Leave default output as None


### Classes

**Please note that at the moment all variables for handling data shared between functions are in global scope. The following classes will encapsulate these variables and clean up the global namespace, but they are currently under construction**

**Subject**

The susbject.py class handles all subject data collected during the experiment

**AWS Handler**

The aws_handler.py class manages the uploading of subject data to the XR lab's AWS server.

**Recording Manager**

The recording_manager.py class handles all recording threads and audio input settings.

**Test Manager**

The test_manager.py class handles all testing procedures. The test questions are stored in external JSON files:
    SER_questions.json
    task_1_data.json
    task_2_data.json