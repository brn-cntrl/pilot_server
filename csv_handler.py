import csv
from subject_manager import SubjectManager
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
    def path(self) -> str:
        return self._path
    
    @path.setter
    def path(self, path) -> None:
        self._path = path
    
    @property
    def subject_data(self) -> dict:
        return self._subject_data
    
    @subject_data.setter
    def subject_data(self, subject_data) -> None:
        self._subject_data = subject_data

    def create_path(self) -> None:
        self.path = f'{self._id}_{self._name}_{self._date}.csv'

    def create_csv(self) -> None:
        max_rows = max(len(self.subject_data['Test_Transcriptions']),
            len(self.subject_data['VR_Transcriptions_1']),
            len(self.subject_data['VR_Transcriptions_2']),
            len(self.subject_data['Biometric_Baseline']),
            len(self.subject_data['Biometric_Data']),
            len(self.subject_data['SER_Baseline']),
            len(self.subject_data['pss4_data']),
            len(self.subject_data['background_data']),
            len(self.subject_data['demographics_data']),
            len(self.subject_data['exit_survey_data']),
            len(self.subject_data['student_data'])
        )

            # Create CSV headers

        # TODO: add start / stop columns for each task
        headers = ['ID', 'Date', 'Name', 'Email',
            'Test1_Timestamp', 'Test1_Transcript', 'Test1_Emotion',
            'VR1_Timestamp', 'VR1_Transcript', 'VR1_Emotion',
            'VR2_Timestamp', 'VR2_Transcript', 'VR2_Emotion', 
            'Baseline_EDA_Timestamp', 'Biometric_Baseline_EDA', 'Baseline_HR_Timestamp', 'Biometric_Baseline_HR', 
            'Baseline_BI_Timestamp', 'Biometric_Baseline_BI', 'Baseline_HRV_Timestamp', 'Biometric_Baseline_HRV',
            'EDA_Timestamp', 'Biometric_Data_EDA', 'HR_Timestamp', 'Biometric_Data_HR', 
            'BI_Timestamp', 'Biometric_Data_BI', 'HRV_Timestamp', 'Biometric_Data_HRV', 'SER_Baseline_Timestamp', 'SER_Baseline_Emotion'
        ]
        
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

                    if i == 0 and self.subject_data['pss4_data']:   
                        row['PSS4_Main_Purpose'] = self.subject_data['pss4_data']['main_purpose']
                        row['PSS4_Time_Nature'] = self.subject_data['pss4_data']['time_in_nature']
                        row['PSS4_Access_Gardens'] = self.subject_data['pss4_data']['access_gardens']
                        row['PSS4_Enjoy_Time_Natural'] = self.subject_data['pss4_data']['enjoy_time_natural']
                        row['PSS4_Environmental_Preference'] = self.subject_data['pss4_data']['environment_preference']
                        row['PSS4_Natural_Elements'] = self.subject_data['pss4_data']['natural_elements']
                        row['PSS4_Interior_Preference'] = self.subject_data['pss4_data']['interior_preference']
                        row['PSS4_Instructions'] = self.subject_data['pss4_data']['instructions']
                        row['PSS4_Expectations'] = self.subject_data['pss4_data']['expectations']
                        row['PSS4_Feedback'] = self.subject_data['pss4_data']['feedback']
                    else:
                        row['PSS4_Main_Purpose'] = row['PSS4_Time_Nature'] = row['PSS4_Access_Gardens'] = ''
                        row['PSS4_Enjoy_Time_Natural'] = row['PSS4_Environmental_Preference'] = row['PSS4_Natural_Elements'] = ''
                        row['PSS4_Interior_Preference'] = row['PSS4_Instructions'] = row['PSS4_Expectations'] = ''
                        row['PSS4_Feedback'] = ''

                    if i == 0 and self.subject_data['background_data']:
                        row['Background_Rush_Caffeine'] = self.subject_data['background_data']['rush_caffeine']
                        row['Background_Caffeine_Details'] = self.subject_data['background_data']['caffeine_details']
                        row['Background_Caffeine_Time'] = self.subject_data['background_data']['caffeine_time']
                        row['Background_Thirst_Hunger'] = self.subject_data['background_data']['thirst_hunger']
                        row['Background_Heart_Rate'] = self.subject_data['background_data']['heart_rate']
                        row['Background_VR_Experience'] = self.subject_data['background_data']['vr_experience']
                        row['Background_VR_Experience_Description'] = self.subject_data['background_data']['vr_experience_description']
                        row['Background_Balance_Issues'] = self.subject_data['background_data']['balance_issues']
                        row['Background_Motion_Sickness'] = self.subject_data['background_data']['motion_sickness']
                        row['Background_Neurological_Condition'] = self.subject_data['background_data']['neurological_conditions']
                        row['Background_Visual_Impairments'] = self.subject_data['background_data']['visual_impairments']
                        row['Background_Neurological_Vestibular'] = self.subject_data['background_data']['neurological_vestibular']
                        row['Background_Movement_Issues'] = self.subject_data['background_data']['movement_issues']
                        row['Background_Mobility_Issues'] = self.subject_data['background_data']['mobility_issues']
                        row['Background_Scars_Tattoo'] = self.subject_data['background_data']['scars_tattoos']
                        row['Background_Glasses'] = self.subject_data['background_data']['glasses']
                    else:
                        row['Background_Rush_Caffeine'] = row['Background_Caffeine_Details'] = row['Background_Caffeine_Time'] = ''
                        row['Background_Thirst_Hunger'] = row['Background_Heart_Rate'] = row['Background_VR_Experience'] = ''
                        row['Background_VR_Experience_Description'] = row['Background_Balance_Issues'] = row['Background_Motion_Sickness'] = ''
                        row['Background_Neurological_Condition'] = row['Background_Visual_Impairments'] = row['Background_Neurological_Vestibular'] = ''
                        row['Background_Movement_Issues'] = row['Background_Mobility_Issues'] = row['Background_Scars_Tattoo'] = ''
                        row['Background_Glasses'] = ''

                    if i == 0 and self.subject_data['demographics_data']:
                        row['Demographics_Age'] = self.subject_data['demographics_data']['age']
                        row['Demographics_Gender'] = self.subject_data['demographics_data']['gender']
                        row['Demographics_Education'] = self.subject_data['demographics_data']['education']
                        row['Demographics_Childhood_Setting'] = self.subject_data['demographics_data']['childhood_setting']
                        row['Demographics_Current_Setting'] = self.subject_data['demographics_data']['current_living_setting']
                        row['Demographics_Nature'] = self.subject_data['demographics_data']['exposure_to_nature']
                        row['Demographics_Green_Spaces'] = self.subject_data['demographics_data']['access_to_green_spaces']
                        row['Demographics_Pref_Natural'] = self.subject_data['demographics_data']['preference_for_natural_environments']
                        row['Demographics_Env_Prefs'] = self.subject_data['demographics_data']['environmental_preferences']
                        row['Demographics_Pref_Interior'] = self.subject_data['demographics_data']['preference_for_interior_design']
                        row['Demographics_Work_Study_Env'] = self.subject_data['demographics_data']['work_study_environment']
                        row['Demographics_Current_Mood'] = self.subject_data['demographics_data']['current_mood']
                        row['Demographics_Stress_Level'] = self.subject_data['demographics_data']['stress_level']
                        row['Demographics_Physical_Activity'] = self.subject_data['demographics_data']['physical_activity']
                        row['Demographics_Sleep_Quality'] = self.subject_data['demographics_data']['sleep_quality']
                        row['Demographics_VR_Experience'] = self.subject_data['demographics_data']['previous_vr_experience']
                        row['Demographics_VR_Comfort'] = self.subject_data['demographics_data']['comfort_with_vr']
                    else:
                        row['Demographics_Age'] = row['Demographics_Gender'] = row['Demographics_Education'] = ''
                        row['Demographics_Childhood_Setting'] = row['Demographics_Current_Setting'] = row['Demographics_Nature'] = ''
                        row['Demographics_Green_Spaces'] = row['Demographics_Pref_Natural'] = row['Demographics_Env_Prefs'] = ''
                        row['Demographics_Pref_Interior'] = row['Demographics_Work_Study_Env'] = row['Demographics_Current_Mood'] = ''
                        row['Demographics_Stress_Level'] = row['Demographics_Physical_Activity'] = row['Demographics_Sleep_Quality'] = ''
                        row['Demographics_VR_Experience'] = row['Demographics_VR_Comfort'] = ''

                    if i == 0 and self.subject_data['exit_survey_data']:
                        row['Exit_Survey_Main_Purpose'] = self.subject_data['exit_survey_data']['main_purpose']
                        row['Exit_Survey_Time_In_Nature'] = self.subject_data['exit_survey_data']['time_in_nature']
                        row['Exit_Survey_Access_Gardens'] = self.subject_data['exit_survey_data']['access_gardens']
                        row['Exit_Survey_Enjoy_Time_Natural'] = self.subject_data['exit_survey_data']['enjoy_time_natural']
                        row['Exit_Survey_Environ_Preference'] = self.subject_data['exit_survey_data']['environment_preference']
                        row['Exit_Survey_Natural_Elements'] = self.subject_data['exit_survey_data']['natural_elements']
                        row['Exit_Survey_Interior_Preference'] = self.subject_data['exit_survey_data']['interior_preference']
                        row['Exit_Survey_Instructions'] = self.subject_data['exit_survey_data']['instructions']
                        row['Exit_Survey_Expectations'] = self.subject_data['exit_survey_data']['expectations']
                        row['Exit_Survey_Feedback'] = self.subject_data['exit_survey_data']['feedback']
                    else:
                        row['Exit_Survey_Main_Purpose'] = row['Exit_Survey_Time_In_Nature'] = row['Exit_Survey_Access_Gardens'] = ''
                        row['Exit_Survey_Enjoy_Time_Natural'] = row['Exit_Survey_Environ_Preference'] = row['Exit_Survey_Natural_Elements'] = ''
                        row['Exit_Survey_Interior_Preference'] = row['Exit_Survey_Instructions'] = row['Exit_Survey_Expectations'] = ''
                        row['Exit_Survey_Feedback'] = ''

                    if i == 0 and self.subject_data['student_data']:
                        row['Student_Survey_PID'] = self.subject_data['student_data']['pid']
                        row['Student_Survey_Class'] = self.subject_data['student_data']['class']
                    else:
                        row['Student_Survey_PID'] = row['Student_Survey_Class'] = ''
                        
                    writer.writerow(row)

        except Exception as e:
            print(e)
            return None      

        # NOTE: UNCOMMENT when awshandler is ready
        # response = xr_awshandler.upload_subject_data(subject_data)

        # if response:
        #     return jsonify({"status": "success", "response": response}), 200
        # else:
        #     return jsonify({"status": "error", "message": "Failed to upload data"}), 400
        print("Data uploaded successfully")
        
    def read(self) -> str:
        with open(self.path, 'r') as file:
            return file.read()

    def write(self, data) -> None:
        with open(self.path, 'w') as file:
            file.write(data)

    def set_csv_filename(self) -> None:
            if self._subject_data['ID'] == '' or self._subject_data['Name'] == '' or self._date == '':
                raise ValueError('Cannot create CSV filename without all information')
            else:
                self.csv_filename = f'{self._subject_data["ID"]}_{self._subject_data["Name"]}_{self._date}.csv'