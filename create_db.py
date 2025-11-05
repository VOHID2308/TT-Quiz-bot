from sqlalchemy import create_engine
from db_manager import Base

engine = create_engine("postgresql+psycopg2://postgres:7767@localhost/quiz_bot_db")
Base.metadata.create_all(engine)
