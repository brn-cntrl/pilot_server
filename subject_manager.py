from aws_handler import AWSHandler

# This class will hold all the data for a single subject
# The data will be stored in a dictionary with the following keys
# ID: The ID of the subject
# Date: The date the data was collected
# Name: The name of the subject
# Email: The email of the subject
# Test_Transcriptions: A list of JSON objects that hold the transcript, SER values, and timestamps for the test data
# VR_Transcriptions_1: A list of JSON objects that hold the transcript, SER values, and timestamps for the VR data
# VR_Transcriptions_2: A list of JSON objects that hold the transcript, SER values, and timestamps for the VR data
# Biometric_Baseline: A list of JSON objects that hold the biometric baseline data
# Biometric_Data: A list of JSON objects that hold the biometric data
# pss4_data: A JSON object that holds the PSS-4 data
# background_data: A JSON object that holds the background data
# demographics_data: A JSON object that holds the demographics data
# exit_survey_data: A JSON object that holds the exit survey data
# student_data: A JSON object that holds the student survey data
# NOTE: All data will be uploaded to the AWS database once the subject has completed the study. 
# A CSV file will also be created for the subject

class SubjectManager:
    def __init__(self):
        self._subject_data = {
            'ID': '',
            'Date': '',
            'Name': '',
            'Email': '',
            'Test_Transcriptions': [], 
            'VR_Transcriptions_1': [], 
            'VR_Transcriptions_2': [], 
            'Biometric_Baseline': [],
            'Biometric_Data': [], 
            'SER_Baseline': [],
            'pss4_data': {},
            'background_data': {},
            'demographics_data': {},
            'exit_survey_data': {},
            'student_data': {}
        }

        # Create subject ID when the object is created
        # self.aws_handler = AWSHandler('session_a')

        # TODO: Uncomment when ready to go to production
        # self.subject_data["ID"] = self.aws_handler.get_subject_id()

    ######################## GETTERS / SETTERS ########################
    @property
    def subject_data(self):
        return self._subject_data
    
    @subject_data.setter
    def subject_data(self, subject_data):
        self._subject_data = subject_data