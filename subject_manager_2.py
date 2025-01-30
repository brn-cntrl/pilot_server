import csv
import os
from aws_handler import AWSHandler
from datetime import datetime

class SubjectManager:
    def __init__(self) -> None:
        self._subject_id = None
        self.csv_file_path = None
        self.txt_file_path = None
        self.PID = None
        self.class_name = None
        self.headers = ['Timestamp', 'Event_Marker', 'Audio_File', 'Transcription', 'SER_Emotion', 'SER_Confidence']
        self._balance = 0
        self.data_root = "subject_data"
        self._experiment_name = None
        self._trial_name = None
        self._subject_folder = None

        # Only held in RAM and not stored.
        self._subject_first_name = None 
        self._subject_last_name = None
        self._subject_email = None

    @property
    def subject_first_name(self) -> str:
        return self._subject_first_name
    
    @subject_first_name.setter
    def subject_first_name(self, value: str) -> None:
        self._subject_first_name = value

    @property
    def subject_last_name(self) -> str:
        return self._subject_last_name
    
    @subject_last_name.setter
    def subject_last_name(self, value: str) -> None:
        self._subject_last_name = value

    @property
    def subject_email(self) -> str:
        return self._subject_email
    
    @subject_email.setter
    def subject_email(self, value: str) -> None:
        self._subject_email = value

    @property
    def experiment_name(self) -> str:
        return self._experiment_name
    
    @experiment_name.setter
    def experiment_name(self, value: str) -> None:
        self._experiment_name = value

    @property
    def trial_name(self) -> str:
        return self._trial_name
    
    @trial_name.setter
    def trial_name(self, value: str) -> None:
        self._trial_name = value
    
    @property
    def subject_folder(self) -> str:
        return self._subject_folder
    
    @subject_folder.setter
    def subject_folder(self, value: str) -> None:
        self._subject_folder = value
    
    @property
    def subject_id(self) -> str:
        return self._subject_id

    @subject_id.setter
    def subject_id(self, value: str) -> None:
        self._subject_id = value

    def set_subject(self, subject_info: dict) -> None:
        """
            Set the subject's name, ID, and email, PID (if any), class name (if any) and initialize the CSV file.
            Args:
                subject_info (dict): Dictionary containing the subject's name, ID, and email.
                Expected format: {"name": str, "id": str, "email": str, "PID": str, "class_name": str} 
            Returns:
                None
        """
        self.subject_id = subject_info["id"]
        self.PID = subject_info["PID"]
        self.class_name = subject_info["class_name"]
        
        if not self.experiment_name or not self.trial_name:
            raise ValueError("Experiment name and trial name must be set before setting the subject.")
        
        else:
            # Create a folder named for the subject name and ID if it doesn't exist
            folder_name = self.subject_id
            self.subject_folder = os.path.join(self.data_root, self.experiment_name, self.trial_name, folder_name)

            if not os.path.exists(self.subject_folder):
                os.makedirs(self.subject_folder)

            current_date = datetime.now().strftime("%Y-%m-%d")
            csv_filename = f"{current_date}_{self.experiment_name}_{self.trial_name}_{self.subject_id}.csv"
            self.csv_file_path = os.path.join(self.subject_folder, csv_filename)

            # DEBUG
            print("Subject folder set: ", self.subject_folder)
            print("Subject data csv set: ", self.csv_file_path)
            
            self.create_csv(self.csv_file_path)
    
    def create_csv(self, csv_file_path: str) -> None:
        if not os.path.exists(csv_file_path):
            with open(csv_file_path, mode='w', newline='', encoding='utf-8') as csv_file:
                writer = csv.writer(csv_file)
                
                writer.writerow([f"Experiment Name: {self.experiment_name}"])
                writer.writerow([f"Trial Name: {self.trial_name}"])
                writer.writerow([f"Subject ID: {self.subject_id}"])
                writer.writerow([f"PID: {self.PID}"])
                writer.writerow([f"Class Name: {self.class_name}"])  
                writer.writerow(self.headers)  

    def append_data(self, data: dict) -> None:
        """
        Append data to the main CSV file, ignoring columns that are not relevant to the current data collection.
    
        Args:
            data (dict): Dictionary containing the data to be appended, where keys are column names and values are the corresponding data.
            Expected format: {'Timestamp': str, 'Event_Marker': str, 'Transcription': str, 'SER_Emotion': str, 'SER_Confidence': str}
        """
        try:
            with open(self.csv_file_path, mode='r', newline='', encoding='utf-8') as csvfile:
                
                reader = csv.reader(csvfile)

                # Skip the metadata rows (subject info)
                next(reader)  # Experiment Name
                next(reader)  # Trial Name
                next(reader)  # Subject ID
                next(reader)  # PID
                next(reader)  # Class Name

                while True:
                    headers = next(reader) 
                    if headers:  
                        break

                rows = list(reader)  # Get existing rows

                # debugging statements
                print(f"Headers: {headers}")
                print(f"Rows: {rows}")

        except FileNotFoundError:
            # If the file doesn't exist, create it with the headers from data
            print(f"CSV file not found. Enter subject information first.")

        # Filter the data to only include keys that are in the existing headers and have non-empty values
        filtered_data = {key: value for key, value in data.items() if key in headers and value != ""}

        # Prepare the row based on the order of the headers
        row = [filtered_data.get(header, "") for header in headers]

        with open(self.csv_file_path, mode='a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            writer.writerow(row)

        print(f"Data has been successfully appended to {self.csv_file_path}.")

    def load_data(self) -> list[dict]:
        """Load and return all data from the CSV file."""
        if not self.csv_file_path:
            raise ValueError("Subject has not been set. Call 'set_subject' first.")
        
        with open(self.csv_file_path, mode='r', newline='', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            return list(reader)

    def reset_subject(self) -> None:
        """Reset the subject details and clear the CSV file reference."""
        self.subject_id = None
        self.csv_file_path = None