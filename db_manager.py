import json
import random

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy import BigInteger

from sqlalchemy.sql import func
from datetime import datetime, date
from config import DATABASE_URL

engine = create_engine(DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


from sqlalchemy import BigInteger

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    username = Column(String)
    full_name = Column(String)
    total_correct_global = Column(Integer, default=0)

class Test(Base):
    __tablename__ = 'tests'
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text)

class Question(Base):
    __tablename__ = 'questions'
    id = Column(BigInteger, primary_key=True, index=True)
    test_id = Column(BigInteger, ForeignKey('tests.id'))
    question_text = Column(Text)
    options_json = Column(Text)
    correct_label = Column(String)

class QuizResult(Base):
    __tablename__ = "quiz_results"

    id = Column(BigInteger, primary_key=True)  
    user_id = Column(BigInteger)              
    test_id = Column(BigInteger)
    score = Column(BigInteger)
    total_questions = Column(BigInteger)
    date_taken = Column(DateTime)
    month_year = Column(String, index=True)


def init_db():
    """Barcha jadvallarni yaratadi (agar mavjud bo'lmasa)."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """DB sessiyasini yaratadi va qaytaradi."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_or_create_user(db, telegram_id, update_info):
    """Foydalanuvchini topadi yoki yangi yaratadi."""
    user = db.query(User).filter(User.id == telegram_id).first()
    if not user:
        user = User(
            id=telegram_id,
            username=update_info.username,
            full_name=update_info.full_name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def update_global_score(db, user_id, correct_count):
    """Global to'g'ri javoblar sonini yangilaydi."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.total_correct_global += correct_count
        db.commit()

def save_quiz_result(db, user_id, test_id, score, total_q):
    """Quiz natijasini saqlaydi (Global va Oylik)."""
    
    month_key = datetime.utcnow().strftime("%Y-%m")
    result = QuizResult(
        user_id=user_id,
        test_id=test_id,
        score=score,
        total_questions=total_q,
        month_year=month_key
    )
    db.add(result)
    
    update_global_score(db, user_id, score)
    
    db.commit()

def get_leaderboards(db):
    """Global va Oylik reytinglarni qaytaradi."""
    
    global_lb = db.query(User.id, User.total_correct_global).order_by(User.total_correct_global.desc()).limit(10).all()
    

    current_month = datetime.utcnow().strftime("%Y-%m")
    monthly_results = db.query(
        QuizResult.user_id, 
        func.sum(QuizResult.score).label('monthly_score')
    ).filter(QuizResult.month_year == current_month).group_by(QuizResult.user_id).all()
    
    monthly_lb_data = []
    for user_id, score in monthly_results:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            monthly_lb_data.append({
                'id': user_id,
                'username': user.username or f"ID:{user_id}",
                'score': score
            })
    
    monthly_lb_data.sort(key=lambda x: x['score'], reverse=True)
    
    return global_lb, monthly_lb_data


def save_test_to_db(db, test_name, parsed_questions):
    """Testni DB ga saqlaydi."""
    test = Test(name=test_name)
    db.add(test)
    db.flush()

    q_list_to_save = []
    for q_data in parsed_questions:
        all_options = [q_data['correct_answer']] + q_data['options']
        random.shuffle(all_options)
        
        options_map = {chr(65 + i): opt for i, opt in enumerate(all_options)} # A, B, C...
        
        correct_label = next(key for key, value in options_map.items() if value == q_data['correct_answer'])
        
        q_list_to_save.append(Question(
            test_id=test.id,
            question_text=q_data['question'],
            options_json=json.dumps(options_map),
            correct_label=correct_label
        ))
        
    db.bulk_save_objects(q_list_to_save)
    db.commit()
    return test.id

def get_test_questions_from_db(db, test_name):
    """DB dan test savollarini oladi (A, B, C... formatda)."""
    test = db.query(Test).filter(Test.name == test_name).first()
    if not test:
        return None, None
        
    questions_data = db.query(Question).filter(Question.test_id == test.id).all()
    
    processed_qs = []
    for q in questions_data:
        options = json.loads(q.options_json)
        processed_qs.append({
            'question': q.question_text,
            'options': [opt for key, opt in options.items() if key != q.correct_label],
            'correct_answer': options[q.correct_label]
        })
        
    return processed_qs, test.id

def delete_test_by_name(db, test_name):
    test = db.query(Test).filter(Test.name == test_name).first()
    if not test:
        return False

    db.query(Question).filter(Question.test_id == test.id).delete()
    db.query(QuizResult).filter(QuizResult.test_id == test.id).delete()

    db.delete(test)
    db.commit()
    return True
