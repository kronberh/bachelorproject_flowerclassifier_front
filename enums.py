from enum import Enum

class AnswerCompletenessStruct():
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name

class AnswerCompleteness(Enum):
    NAME = AnswerCompletenessStruct(0, 'Only name')
    SHORT = AnswerCompletenessStruct(1, 'Short description')
    FULL = AnswerCompletenessStruct(2, 'Full description')
