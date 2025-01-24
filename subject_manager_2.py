import csv
import os
from aws_handler import AWSHandler
from datetime import datetime

class SubjectManager:
    def __init__(self) -> None:
        # Attributes to hold subject's name and ID
        self._subject_name = None
        self._subject_id = None
        self.csv_file_path = None
        self.txt_file_path = None
        self.PID = None
        self.class_name = None
        self.headers = ['Timestamp', 'Event_Marker', 'Audio_File', 'Transcription', 'SER_Emotion', 'SER_Confidence']
        self._balance = 0
        
    @property 
    def balance(self):
        return self._balance
    
    @balance.setter
    def balance(self, value):
        self._balance = value

    @property
    def subject_name(self) -> str:
        return self._subject_name

    @subject_name.setter
    def subject_name(self, value: str) -> None:
        self._subject_name = value

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
        self.subject_name = subject_info["name"]
        self.subject_id = subject_info["id"]
        self.subject_email = subject_info["email"]
        self.PID = subject_info["PID"]
        self.class_name = subject_info["class_name"]
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        self.csv_file_path = f"subject_files/{current_date}_{self.subject_name}_{self.subject_id}.csv"
        # self.txt_file_path = f"subject_files/{current_date}_{self.subject_name}_{self.subject_id}_final_balance.txt"

        if not os.path.exists(self.csv_file_path):
            with open(self.csv_file_path, mode='w', newline='', encoding='utf-8') as csv_file:
                writer = csv.writer(csv_file)
                
                # writer.writerow([f"Experiment Name: {self.experiment_name}"])
                # writer.writerow([f"Trial Name: {self.trial_name}"])
                writer.writerow([f"Subject Name: {self.subject_name}"])
                writer.writerow([f"Subject ID: {self.subject_id}"])
                writer.writerow([f"Email: {self.subject_email}"])
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
                next(reader)  # Subject Name
                next(reader)  # Subject ID
                next(reader)  # Email
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
        self.subject_name = None
        self.subject_id = None
        self.csv_file_path = None

    # def write_balance(self, balance: str) -> None:
    #     with open(self.txt_file_path, mode='w', encoding='utf-8') as file:
    #         file.write(self.subject_name)
    #         file.write("\n")
    #         file.write(self.subject_id)
    #         file.write("\n")
    #         file.write(balance)