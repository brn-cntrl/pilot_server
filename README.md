# Pilot Experiment Server

## A command center for running all applications during experiment

**Dependencies to run the server**
* Flask
* Pyaudio (for handling audio device)
* Portaudio 
* vosk (fgor transcription)

**Installation**
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
Please note that the SER model prints information to the terminal when it loads, so you might need to scroll up to find this section.

* On Mac, CMD+click on the listed http address and the server will launch a webpage in your default browser
* To shutdown the server in the browser, click "Shutdown Server"
* To shutdown in terminal, run "ctrl+c"

**NOTE:** DO NOT remove the any of the html pages from the templates folder. This is where Flask will always look for them. Your home http address may vary.


### Transcription and SER

**Install Dependencies**

* Install PyTorch and additional libraries with:

        pip install torch, torchvision, torchaudio

* Install SpeechRecognition for Python with: 

        pip install SpeechRecognition

* Install SpeechBrain with:
        pip install speechbrain

**NOTE** The first time the server is run on the local machine, it will automatically download the model for speechbrain. This process might take a considerable amount of time and can be monitored in the terminal. Please wait until the model has finished downloading before running the tests. The model can be replaced by altering the source variable in this function:
    
    def get_ser_model():
        return EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="pretrained_models"
    )

More information can be found by visiting:

    https://speechbrain.readthedocs.io/en/0.5.7/API/speechbrain.pretrained.interfaces.html

### AWS Requester
This is the script that downloads Empatica data from the Amazon Cloud server

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
* Enter the AWS access key (Found on Empatica Care)
* Enter the AWS secret access key (Found on Empatica Care)
* Enter the default region name (us-west-2)
* Leave default output as None

**Notes**

* The AWS Requester retrieves the most recently created data file from the Empatica AWS cloud server and appends the name of the participant to the data filename. The participant information form must be submitted before downloading the data or the script will not run.
* Run the Empatica session and be sure to end the session before pressing the download button.