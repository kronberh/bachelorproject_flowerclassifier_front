from enum import Enum

class AnswerAwarenessStruct():
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name

class AnswerCompleteness(Enum):
    NAME = AnswerAwarenessStruct(0, 'Only name')
    SHORT = AnswerAwarenessStruct(1, 'Short description')
    FULL = AnswerAwarenessStruct(2, 'Full description')
