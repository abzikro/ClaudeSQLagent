import json
import os
from utils import resource_path


class QuestionDatabase:
    def __init__(self):
        self.db_file = resource_path("Data/answered_questions.json")
        self.questions = self.load_questions()

    def load_questions(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                return json.load(f)
        return {}

    def save_questions(self):
        with open(self.db_file, 'w') as f:
            json.dump(self.questions, f, indent=2)

    def add_question(self, question, sql_code):
        self.questions[question] = sql_code
        self.save_questions()

    def get_questions(self):
        return self.questions

    def get_sql_for_question(self, question):
        return self.questions.get(question)