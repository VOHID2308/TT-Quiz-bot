import re
import random

def parse_text_to_quiz(text):
    """
    Kiritilgan matnni savol-javoblar ro'yxatiga tahlil qiladi.
    Savollar '1.', '2.', ... bilan boshlanadi.
    To'g'ri javob '*' bilan boshlanadi.
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    quizzes = []
    current_question_data = None
    
    QUESTION_START_REGEX = re.compile(r"^\d+\.\s*(.*)")
    
    for line in lines:
        match = QUESTION_START_REGEX.match(line)
        
        if match:
            if current_question_data:
                if current_question_data['options']:
                    quizzes.append(current_question_data)
            
            current_question_data = {
                'question': match.group(1).strip(),
                'options': [],
                'correct_answer': None
            }
        elif line.startswith('*'):
        
            if current_question_data:
                current_question_data['correct_answer'] = line[1:].strip()

        elif current_question_data and current_question_data['correct_answer'] is not None:
            current_question_data['options'].append(line)
    
    if current_question_data and current_question_data['correct_answer'] is not None:
        quizzes.append(current_question_data)
        
    return [q for q in quizzes if q['correct_answer']]

def format_question_for_db(question_data):
    """
    DBga saqlash uchun (db_manager ichida amalga oshiriladi, bu funksiyani o'chirib tashlaymiz
    va db_manager.py ichida barcha logikani yozamiz, chunki bizga variantlarni aralashtirish kerak).
    """
    pass