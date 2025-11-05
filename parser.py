# parser.py
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
    
    # RegEx: Savol raqami (1., 2., ...) bilan boshlanishi kerak
    QUESTION_START_REGEX = re.compile(r"^\d+\.\s*(.*)")
    
    for line in lines:
        match = QUESTION_START_REGEX.match(line)
        
        if match:
            # Yangi savol boshlandi
            if current_question_data:
                # Oldingi savolni saqlash
                if current_question_data['options']:
                    quizzes.append(current_question_data)
            
            # Yangi savol holatini boshlash
            current_question_data = {
                'question': match.group(1).strip(), # Savol matni
                'options': [], # Bu yerda faqat noto'g'ri javoblar saqlanadi
                'correct_answer': None
            }
        elif line.startswith('*'):
            # To'g'ri javob
            if current_question_data:
                current_question_data['correct_answer'] = line[1:].strip()
        elif current_question_data and current_question_data['correct_answer'] is not None:
            # Notog'ri javob
            current_question_data['options'].append(line)
    
    # Oxirgi savolni qo'shish
    if current_question_data and current_question_data['correct_answer'] is not None:
        quizzes.append(current_question_data)
        
    # Agar to'g'ri javob topilmagan savol bo'lsa, uni tashlab yuborish
    return [q for q in quizzes if q['correct_answer']]

def format_question_for_db(question_data):
    """
    DBga saqlash uchun (db_manager ichida amalga oshiriladi, bu funksiyani o'chirib tashlaymiz
    va db_manager.py ichida barcha logikani yozamiz, chunki bizga variantlarni aralashtirish kerak).
    """
    pass # Logika db_manager.py ga ko'chirildi