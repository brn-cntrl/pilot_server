import csv
from subject import Subject
from aws_handler import AWSHandler
from datetime import datetime

class CSVHandler:
    def __init__(self, subject):
        self._subject_data = subject.subject_data
        self._id = self._subject_data['ID']
        self._name = self._subject_data['Name']
        self._date = datetime.now().strftime('%Y-%m-%d')
        self._path = self.set_csv_filename()
        self.aws_handler = AWSHandler('session_a') # TODO: Get rid of the session parameter

    @property
    def path(self):
        return self._path
    
    @path.setter
    def path(self, path):
        self._path = path
    
    @property
    def subject_data(self):
        return self._subject_data
    
    @subject_data.setter
    def subject_data(self, subject_data):
        self._subject_data = subject_data

    def create_path(self):
        self.path = f'{self._id}_{self._name}_{self._date}.csv'

    def create_csv(self):
        max_rows = max(len(self.subject_data['Test_Transcriptions']),
            len(self.subject_data['VR_Transcriptions_1']),
            len(self.subject_data['VR_Transcriptions_2']),
            len(self.subject_data['Biometric_Baseline']),
            len(self.subject_data['Biometric_Data']),
            len(self.subject_data['SER_Baseline'])
        )

            # Create CSV headers
        headers = ['ID', 'Date', 'Name', 'Email',
            'Test_Timestamp', 'Test_Transcript', 'Test_Emotion',
            'VR1_Timestamp', 'VR1_Transcript', 'VR1_Emotion',
            'VR2_Timestamp', 'VR2_Transcript', 'VR2_Emotion', 
            'Baseline_EDA_Timestamp', 'Biometric_Baseline_EDA', 'Baseline_HR_Timestamp', 'Biometric_Baseline_HR', 
            'Baseline_BI_Timestamp', 'Biometric_Baseline_BI', 'Baseline_HRV_Timestamp', 'Biometric_Baseline_HRV',
            'EDA_Timestamp', 'Biometric_Data_EDA', 'HR_Timestamp', 'Biometric_Data_HR', 
            'BI_Timestamp', 'Biometric_Data_BI', 'HRV_Timestamp', 'Biometric_Data_HRV', 'SER_Baseline_Timestamp', 'SER_Baseline_Emotion',
            'PSS4_Survey', 'Background_Survey', 'Demographics_Survey', 'Exit_Survey', 'Student_Survey']
        
        try:
            # Open CSV file for writing
            with open(self.path, mode='w', newline='') as file:
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
                        row['Test_Transcript'] = self.subject_data['Test_Transcriptions'][i]['transcription']
                        row['Test_Emotion'] = self.subject_data['Test_Transcriptions'][i]['emotion']
                    else:
                        row['Test_Timestamp'] = row['Test_Transcript'] = row['Test_Emotion'] = ''

                    if i < len(self.subject_data['VR_Transcriptions_1']):
                        row['VR1_Timestamp'] = self.subject_data['VR_Transcriptions_1'][i]['timestamp']
                        row['VR1_Transcript'] = self.subject_data['VR_Transcriptions_1'][i]['transcription']
                        row['VR1_Emotion'] = self.subject_data['VR_Transcriptions_1'][i]['emotion']
                    else:
                        row['VR1_Timestamp'] = row['VR1_Transcript'] = row['VR1_Emotion'] = ''

                    if i < len(self.subject_data['VR_Transcriptions_2']):
                        row['VR2_Timestamp'] = self.subject_data['VR_Transcriptions_2'][i]['timestamp']
                        row['VR2_Transcript'] = self.subject_data['VR_Transcriptions_2'][i]['transcription']
                        row['VR2_Emotion'] = self.subject_data['VR_Transcriptions_2'][i]['emotion']
                    else:
                        row['VR2_Timestamp'] = row['VR2_Transcript'] = row['VR2_Emotion'] = ''

                    if i < len(self.subject_data['Biometric_Baseline']):
                        baseline_data = self.subject_data['Biometric_Baseline'][i]
                        row['Baseline_EDA_Timestamp'], row['Biometric_Baseline_EDA'] = baseline_data.get('EDA', ('', ''))
                        row['Baseline_HR_Timestamp'], row['Biometric_Baseline_HR'] = baseline_data.get('HR', ('', ''))
                        row['Baseline_BI_Timestamp'], row['Biometric_Baseline_BI'] = baseline_data.get('BI', ('', ''))
                        row['Baseline_HRV_Timestamp'], row['Biometric_Baseline_HRV'] = baseline_data.get('HRV', ('', ''))
                    else:
                        row['Baseline_EDA_Timestamp'] = row['Biometric_Baseline_EDA'] = ''
                        row['Baseline_HR_Timestamp'] = row['Biometric_Baseline_HR'] = ''
                        row['Baseline_BI_Timestamp'] = row['Biometric_Baseline_BI'] = ''
                        row['Baseline_HRV_Timestamp'] = row['Biometric_Baseline_HRV'] = ''

                    if i < len(self.subject_data['Biometric_Data']):
                        biometric_data = self.subject_data['Biometric_Data'][i]
                        row['EDA_Timestamp'], row['Biometric_Data_EDA'] = biometric_data.get('EDA', ('', ''))
                        row['HR_Timestamp'], row['Biometric_Data_HR'] = biometric_data.get('HR', ('', ''))
                        row['BI_Timestamp'], row['Biometric_Data_BI'] = biometric_data.get('BI', ('', ''))
                        row['HRV_Timestamp'], row['Biometric_Data_HRV'] = biometric_data.get('HRV', ('', ''))
                    else:
                        row['EDA_Timestamp'] = row['Biometric_Data_EDA'] = ''
                        row['HR_Timestamp'] = row['Biometric_Data_HR'] = ''
                        row['BI_Timestamp'] = row['Biometric_Data_BI'] = ''
                        row['HRV_Timestamp'] = row['Biometric_Data_HRV'] = ''

                    if i < len(self.subject_data['SER_Baseline']):
                        row['SER_Baseline_Timestamp'] = self.subject_data['SER_Baseline'][i]['timestamp']
                        row['SER_Baseline_Emotion'] = self.subject_data['SER_Baseline'][i]['emotion']
                    else:
                        row['SER_Baseline_Timestamp'] = row['SER_Baseline_Emotion'] = ''

                    row['PSS4_Survey'] = self.subject_data['pss4_data']
                    row['Background_Survey'] = self.subject_data['background_data']
                    row['Demographics_Survey'] = self.subject_data['demographics_data']
                    row['Exit_Survey'] = self.subject_data['exit_survey_data']
                    row['Student_Survey'] = self.subject_data['student_data']

                    # Write the row to the CSV file
                    writer.writerow(row)

        except Exception as e:
            print(e)
            return {"status": "error", "message": "Failed to create CSV file"}        

        # NOTE: UNCOMMENT when awshandler is ready
        # response = xr_awshandler.upload_subject_data(subject_data)

        # if response:
        #     return jsonify({"status": "success", "response": response}), 200
        # else:
        #     return jsonify({"status": "error", "message": "Failed to upload data"}), 400
        print("Data uploaded successfully")
        
    def read(self):
        with open(self.path, 'r') as file:
            return file.read()

    def write(self, data):
        with open(self.path, 'w') as file:
            file.write(data)

    def set_csv_filename(self):
            if self._subject_data['ID'] == '' or self._subject_data['Name'] == '' or self._date == '':
                raise ValueError('Cannot create CSV filename without all information')
            else:
                self.csv_filename = f'{self._subject_data["ID"]}_{self._subject_data["Name"]}_{self._date}.csv'