from aws_handler import AWSHandler

# This class will hold all the data for a single subject
# The data will be stored in a dictionary with the following keys
# ID: The ID of the subject
# Date: The date the data was collected
# Name: The name of the subject
# Email: The email of the subject
# Student_Data: A JSON object that holds the student survey data
# Task_ID: A list of tuples that hold the timestamp for when a task is started (including idling between tasks) and the task id.
# Test_Transcriptions: A list of JSON objects that hold the transcript, SER values, and timestamps for the test data
# VR_Transcriptions_1: A list of JSON objects that hold the transcript, SER values, and timestamps for the VR data
# VR_Transcriptions_2: A list of JSON objects that hold the transcript, SER values, and timestamps for the VR data
# Biometric_Baseline: A list of JSON objects that hold the biometric baseline data
# Biometric_Data: A list of JSON objects that hold the biometric data
# NOTE: All data will be uploaded to the AWS database once the subject has completed the study. 
# A CSV file will also be created for the subject

class SubjectManager:
    def __init__(self) -> None:
        self._subject_data = {
            'ID': '',
            'Date': '',
            'Name': '',
            'Email': '',
            'student_data': {},
            'Task_ID': [],
            'Test_Transcriptions': [], 
            'VR_Transcriptions_1': [], 
            'VR_Transcriptions_2': [], 
            'Biometric_Baseline': [],
            'Biometric_Data': [], 
            'SER_Baseline': []
        }

        # Create subject ID when the object is created
        # self.aws_handler = AWSHandler('session_a')

        # TODO: Uncomment when ready to go to production
        # self.subject_data["ID"] = self.aws_handler.get_subject_id()

    ######################## GETTERS / SETTERS ########################
    @property
    def subject_data(self) -> dict:
        return self._subject_data
    
    @subject_data.setter
    def subject_data(self, subject_data) -> None:
        self._subject_data = subject_data