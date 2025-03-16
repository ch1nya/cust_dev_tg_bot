from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

Base = declarative_base()

class Respondent(Base):
    __tablename__ = 'respondents'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)
    profession = Column(String)
    trait = Column(String)
    profile = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    interviews = relationship("Interview", back_populates="respondent")

class Interview(Base):
    __tablename__ = 'interviews'
    
    id = Column(Integer, primary_key=True)
    respondent_id = Column(Integer, ForeignKey('respondents.id'))
    hypothesis = Column(String)
    responses = Column(JSON)  # Список ответов в формате JSON
    analysis = Column(JSON)   # Результаты анализа
    created_at = Column(DateTime, default=datetime.utcnow)
    
    respondent = relationship("Respondent", back_populates="interviews")

class DatabaseManager:
    def __init__(self, db_path="sessions.db"):
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def create_respondent(self, name: str, age: int, profession: str, 
                         trait: str, profile: dict) -> Respondent:
        """Создание нового респондента"""
        respondent = Respondent(
            name=name,
            age=age,
            profession=profession,
            trait=trait,
            profile=profile
        )
        self.session.add(respondent)
        self.session.commit()
        return respondent

    def create_interview(self, respondent_id: int, hypothesis: str) -> Interview:
        """Создание нового интервью"""
        interview = Interview(
            respondent_id=respondent_id,
            hypothesis=hypothesis,
            responses=[]
        )
        self.session.add(interview)
        self.session.commit()
        return interview

    def add_response(self, interview_id: int, response: str):
        """Добавление ответа к интервью"""
        interview = self.session.query(Interview).get(interview_id)
        if interview:
            responses = interview.responses or []
            responses.append({
                "text": response,
                "timestamp": datetime.utcnow().isoformat()
            })
            interview.responses = responses
            self.session.commit()

    def update_analysis(self, interview_id: int, analysis: dict):
        """Обновление результатов анализа интервью"""
        interview = self.session.query(Interview).get(interview_id)
        if interview:
            interview.analysis = analysis
            self.session.commit()

    def get_respondent(self, respondent_id: int) -> Respondent:
        """Получение респондента по ID"""
        return self.session.query(Respondent).get(respondent_id)

    def get_interview(self, interview_id: int) -> Interview:
        """Получение интервью по ID"""
        return self.session.query(Interview).get(interview_id)

    def get_respondent_interviews(self, respondent_id: int) -> list:
        """Получение всех интервью респондента"""
        return self.session.query(Interview).filter_by(respondent_id=respondent_id).all()

    def get_all_respondents(self) -> list:
        """Получение всех респондентов"""
        return self.session.query(Respondent).all()

if __name__ == "__main__":
    # Пример использования
    db = DatabaseManager()
    
    # Создание тестового респондента
    test_profile = {
        "name": "Иван Петров",
        "pain_points": ["Сложная отчетность", "Много ручной работы"],
        "communication_style": "Говорит медленно, часто переспрашивает",
        "traps": ["Уходит в детали", "Ссылается на опыт"]
    }
    
    respondent = db.create_respondent(
        name="Иван Петров",
        age=35,
        profession="бухгалтер",
        trait="скептик",
        profile=test_profile
    )
    
    # Создание интервью
    interview = db.create_interview(
        respondent_id=respondent.id,
        hypothesis="Бухгалтеры тратят много времени на ручной ввод данных"
    )
    
    # Добавление ответов
    db.add_response(interview.id, "Да, это отнимает много времени")
    
    # Обновление анализа
    db.update_analysis(interview.id, {
        "confirmation_rate": 0.8,
        "key_insights": ["Подтверждена проблема с ручным вводом"]
    }) 