import json
import re

class TestManager:
    def __init__(self):
        try:
            with open('SER_questions.json') as f:
                self.questions = json.load(f)
        except FileNotFoundError:
            self.ser_questions = {}
            print("SER_questions.json not found")

        try:
            with open('task_1_data.json') as f:
                self.task_1_questions = json.load(f)
        except FileNotFoundError:
            self.task_1_questions = {}
            print("task_1_data.json not found")

        try:
            with open('task_2_data.json') as f:
                self.task_2_questions = json.load(f)
        except FileNotFoundError:
            self.task_2_questions = {}
            print("task_2_data.json not found")

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
