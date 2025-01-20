from aws_handler import AWSHandler
from csv_handler import CSVHandler

class SubjectManager:
    def __init__(self) -> None:
        self._subject_data = {
            'ID': '',
            'Date': '',
            'Name': '',
            'Email': '',
            'student_data': {},
            'Test_Transcriptions': [], 
            'VR_Transcriptions': [],  
            'SER_Baseline': [],
            'Event_Markers': []
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