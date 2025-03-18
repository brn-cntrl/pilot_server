import json
import re

class TestManager:
    def __init__(self) -> None:
        print("Test Manager initialized...")
        try:
            with open('test_files/SER_questions.json') as f:
                self._ser_questions = json.load(f)
                print("SER_questions.json loaded successfully")

        except FileNotFoundError:
            self._ser_questions = {}
            print("SER baseline file, SER_questions.json not found")

        try:
            with open('test_files/task_1_data.json') as f:
                self._task_1_questions = json.load(f)
                print("Stressor task file, task_1_data.json loaded successfully")

        except FileNotFoundError:
            self._task_1_questions = {}
            print("task_1_data.json not found")

        try:
            with open('test_files/task_2_data.json') as f:
                self._task_2_questions = json.load(f)
                print("Stressor task 2 file, task_2_data.json loaded successfully")

        except FileNotFoundError:
            self._task_2_questions = {}
            print("task_2_data.json not found")

        self._test_1_taken = False
        self._test_2_taken = False
        self._current_question_index = 0  
        self._current_test_index = 0
        self._current_ser_question_index = 0
        self._current_answer = None
    
    @property
    def current_answer(self):
        return self._current_answer
    
    @current_answer.setter
    def current_answer(self, answer):
        self._current_answer = answer
    
    @property
    def test_1_taken(self):
        return self._test_1_taken
    
    @test_1_taken.setter
    def test_1_taken(self, test_1_taken):
        self._test_1_taken = test_1_taken

    @property
    def test_2_taken(self):
        return self._test_2_taken
    
    @test_2_taken.setter
    def test_2_taken(self, test_2_taken):
        self._test_2_taken = test_2_taken
        
    @property
    def ser_questions(self):
        return self._ser_questions
    
    @ser_questions.setter
    def ser_questions(self, ser_questions):
        self._ser_questions = ser_questions

    @property
    def task_1_questions(self):
        return self._task_1_questions
    
    @task_1_questions.setter
    def task_1_questions(self, task_1_questions):
        self._task_1_questions = task_1_questions

    @property
    def task_2_questions(self):
        return self._task_2_questions
    
    @task_2_questions.setter
    def task_2_questions(self, task_2_questions):
        self._task_2_questions = task_2_questions
    
    @property
    def current_question_index(self):
        return self._current_question_index
    
    @current_question_index.setter
    def current_question_index(self, index):
        self._current_question_index = index
    
    @property
    def current_test_index(self):
        return self._current_test_index
    
    @current_test_index.setter
    def current_test_index(self, index):
        self._current_test_index = index
    
    @property
    def current_ser_question_index(self):
        return self._current_ser_question_index
    
    @current_ser_question_index.setter
    def current_ser_question_index(self, index):
        self._current_ser_question_index = index
    
    def get_task_questions(self, index):
        task_questions = [self.task_1_questions, self.task_2_questions]

        if index >= len(task_questions):
            return None
        
        return task_questions[index]
    
    def get_ser_question(self, index):      
        if index >= len(self.ser_questions):
            return None
        
        return self.ser_questions[index]
    
    # def increment_ser_question_index(self):
    #     self.current_ser_question_index += 1

    # def increment_question_index(self):
    #     self.current_question_index += 1
    
    # def increment_test_index(self):
    #     self.current_test_index += 1

    def get_next_question(self, task_number, index):
        if task_number == 1:
            return self.task_1_questions[index]
        elif task_number == 2:
            return self.task_2_questions[index]
        else:
            return "Tests completed"
        
    def get_next_test(self, test_index):
        if test_index >= len(self.questions):
            return "Tests completed"
        return self.questions[test_index]

    def preprocess_text(self, text):
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        return text.strip()

    def check_answer(self, transcription, correct_answers):
        print(f"Transcription: {transcription}")
        transcription = self.preprocess_text(transcription)

        return any(word in correct_answers for word in transcription.split())