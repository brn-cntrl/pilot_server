import datetime
from aws_handler import AWSHandler
import csv

# This class will hold all the data for a single subject
# The data will be stored in a dictionary with the following keys
# ID: The ID of the subject
# Date: The date the data was collected
# Name: The name of the subject
# Email: The email of the subject
# Test_Transcriptions: A list of JSON objects that hold the transcript, SER values, and timestamps for the test data
# VR_Transcriptions_1: A list of JSON objects that hold the transcript, SER values, and timestamps for the VR data
# VR_Transcriptions_2: A list of JSON objects that hold the transcript, SER values, and timestamps for the VR data
# Biometric_Data: A list of JSON objects that hold the biometric data
# pss4_data: A JSON object that holds the PSS-4 data
# background_data: A JSON object that holds the background data
# demographics_data: A JSON object that holds the demographics data
# exit_survey_data: A JSON object that holds the exit survey data
# intro_data: A JSON object that holds the intro data
# NOTE: All data will be uploaded to the AWS database once the subject has completed the study. 
# A CSV file will also be created for the subject

class Subject:
    def __init__(self):
        self.date = datetime.datetime.now().strftime('%Y-%m-%d')
        self.subject_data = {
            'ID': '',
            'Date': '',
            'Name': '',
            'Email': '',
            'Test_Transcriptions': [], 
            'VR_Transcriptions_1': [], 
            'VR_Transcriptions_2': [], 
            'Biometric_Data': [], 
            'pss4_data': {},
            'background_data': {},
            'demographics_data': {},
            'exit_survey_data': {},
            'intro_data': {}
        }

        self.csv_filename = ''

    ######################## SETTERS ########################
    def set_id(self, id):
        self.subject_data['ID'] = id

    def set_name(self, name):
        self.subject_data['Name'] = name
    
    def set_date(self, date):
        self.subject_data['Date'] = date

    def set_email(self, email):
        self.subject_data['Email'] = email
    
    def set_test_transcriptions(self, test_transcriptions):
        self.subject_data['Test_Transcriptions'] = test_transcriptions

    def set_vr_transcriptions_1(self, vr_transcriptions_1):
        self.subject_data['VR_Transcriptions_1'] = vr_transcriptions_1
    
    def set_vr_transcriptions_2(self, vr_transcriptions_2):
        self.subject_data['VR_Transcriptions_2'] = vr_transcriptions_2

    def set_biometric_data(self, biometric_data):
        self.subject_data['Biometric_Data'] = biometric_data

    def set_pss4(self, pss4):
        self.subject_data['pss4_data'] = pss4

    def set_background_data(self, background):
        self.subject_data['background_data'] = background   

    def set_demographics_data(self, demographics):
        self.subject_data['demographics_data'] = demographics

    def set_exit_survey_data(self, exit_survey):
        self.subject_data['exit_survey_data'] = exit_survey
    
    def set_intro_data(self, intro):
        self.subject_data['intro_data'] = intro

    def set_csv_filename(self):
        if self.subject_data['ID'] == '' or self.subject_data['Name'] == '' or self.date == '':
            raise ValueError('Cannot create CSV filename without all information')
        else:
            self.csv_filename = f'{self.subject_data["ID"]}_{self.subject_data["Name"]}_{self.date}.csv'

######################## GETTERS ########################
    def get_id(self):
        return self.subject_data['ID']

    def get_name(self):
        return self.subject_data['Name']
    
    def get_date(self):
        return self.subject_data['Date']
    
    def get_email(self):
        return self.subject_data['Email']

    def get_test_transcriptions(self):
        return self.subject_data['Test_Transcriptions']

    def get_vr_transcriptions_1(self):
        return  self.subject_data['VR_Transcriptions_1']
    
    def get_vr_transcriptions_2(self):
        return self.subject_data['VR_Transcriptions_2']
    
    def get_biometric_data(self):
        return self.subject_data['Biometric_Data']
    
    def get_pss4(self):
        return self.subject_data['pss4_data']
    
    def get_background_data(self):
        return self.subject_data['background_data']
    
    def get_demographics_data(self):
        return self.subject_data['demographics_data']
    
    def get_exit_survey_data(self):
        return self.subject_data['exit_survey_data']
    
    def get_intro_data(self):
        return self.subject_data['intro_data']
    
    def get_date(self):
        return self.date
    
    def get_subject_data(self):
        return self.subject_data
    
    ######################## METHODS ########################
    def append_test_transcription(self, transcription):
        self.subject_data['Test_Transcriptions'].append(transcription)

    def upload_to_database(self):
        try:
            # TODO: Implement AWS database upload
            xr_awshandler = AWSHandler('session_a')
            self.subject_data['ID'] = xr_awshandler.assign_available_id()

            unique_id = xr_awshandler.assign_available_id()
            self.subject_data['ID'] = unique_id

            max_rows = max(len(self.subject_data['Test_Transcriptions']),
                        len(self.subject_data['VR_Transcriptions_1']),
                        len(self.subject_data['VR_Transcriptions_2']))

            # Create CSV headers
            headers = ['ID', 'Date', 'Name', 'Email',
                    'Test_Timestamp', 'Test_Transcript', 'Test_Emotion',
                    'VR1_Timestamp', 'VR1_Transcript', 'VR1_Emotion',
                    'VR2_Timestamp', 'VR2_Transcript', 'VR2_Emotion', 'PSS4_Survey',
                    'Background_Survey', 'Demographics_Survey', 'Exit_Survey', 'Intro_Survey']

            # Open CSV file for writing
            with open(self.csv_filename, mode='w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=headers)
                writer.writeheader()

                for i in range(max_rows):
                    row = {
                        'ID': self.subject_data['ID'],
                        'Date': self.subject_data['Date'],
                        'Name': self.subject_data['Name'],
                        'Email': self.subject_data['Email']
                    }
                    
                    if i < len(self.subject_data['Test_Transcriptions']):
                        row['Test_Timestamp'] = self.subject_data['Test_Transcriptions'][i]['timestamp']
                        row['Test_Transcript'] = self.subject_data['Test_Transcriptions'][i]['transcript']
                        row['Test_Emotion'] = self.subject_data['Test_Transcriptions'][i]['emotion']
                    else:
                        row['Test_Timestamp'] = row['Test_Transcript'] = row['Test_Emotion'] = ''

                    if i < len(self.subject_data['VR_Transcriptions_1']):
                        row['VR1_Timestamp'] = self.subject_data['VR_Transcriptions_1'][i]['timestamp']
                        row['VR1_Transcript'] = self.subject_data['VR_Transcriptions_1'][i]['transcript']
                        row['VR1_Emotion'] = self.subject_data['VR_Transcriptions_1'][i]['emotion']
                    else:
                        row['VR1_Timestamp'] = row['VR1_Transcript'] = row['VR1_Emotion'] = ''

                    if i < len(self.subject_data['VR_Transcriptions_2']):
                        row['VR2_Timestamp'] = self.subject_data['VR_Transcriptions_2'][i]['timestamp']
                        row['VR2_Transcript'] = self.subject_data['VR_Transcriptions_2'][i]['transcript']
                        row['VR2_Emotion'] = self.subject_data['VR_Transcriptions_2'][i]['emotion']
                    else:
                        row['VR2_Timestamp'] = row['VR2_Transcript'] = row['VR2_Emotion'] = ''

                    # Write the row to the CSV file
                    writer.writerow(row)

                # NOTE: UNCOMMENT when awshandler is ready
                # response = xr_awshandler.upload_subject_data(subject_data)

                # if response:
                #     return jsonify({"status": "success", "response": response}), 200
                # else:
                #     return jsonify({"status": "error", "message": "Failed to upload data"}), 400
                print("Data uploaded successfully")
                return {"status": "success", "message": "Data uploaded successfully"}
            
        except Exception as e:
            print(e)
            return {"status": "error", "message": "Failed to upload data"}
    
    def create_csv(self):
        pass