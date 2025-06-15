#app/models/secondary_admin.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Time, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()

class User(Base):
    """Модель пользователя в базе данных организации"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(64), index=True, unique=True)
    password_hash = Column(String(128))
    role = Column(String(64), index=True)
    cabinet = Column(String(50), nullable=True)
    video = Column(String(100), nullable=True, default='0')
    style_type = Column(String(50), nullable=True, default='default')  # 'default' или 'custom'   
    marquee_text = Column(Text, nullable=True)  # Новое поле для бегущей строки   
    created_at = Column(DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'



class Service(Base):
    """Модель услуги в базе данных организации"""
    __tablename__ = 'services'

    id = Column(Integer, primary_key=True)
    name = Column(String(128), index=True, unique=True)
    start_number = Column(Integer, nullable=False)
    end_number = Column(Integer, nullable=False)
    cabinet = Column(Integer, nullable=True)
    last_ticket_number = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    tickets = relationship('Ticket', backref='service')
    schedules = relationship('ServiceSchedule', backref='service')
    statistics = relationship('TicketStatistics', backref='service', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Service {self.name}>'

class Ticket(Base):
    """Модель талона в базе данных организации"""
    __tablename__ = 'tickets'

    id = Column(Integer, primary_key=True)
    number = Column(Integer, nullable=False)
    issue_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String(64), index=True, default='waiting')
    service_id = Column(Integer, ForeignKey('services.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', backref='tickets')

    def __repr__(self):
        return f'<Ticket {self.number}>'

class Terminal(Base):
    """Модель терминала в базе данных организации"""
    __tablename__ = 'terminals'

    id = Column(Integer, primary_key=True)
    location = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Terminal {self.location}>'

class Display(Base):
    """Модель табло в базе данных организации"""
    __tablename__ = 'displays'

    id = Column(Integer, primary_key=True)
    location = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Display {self.location}>'

class ServiceAssignment(Base):
    """Модель назначения услуги пользователю"""
    __tablename__ = 'service_assignments'

    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    service = relationship('Service')
    user = relationship('User')

    def __repr__(self):
        return f'<ServiceAssignment {self.service_id}-{self.user_id}>'

class ServiceSchedule(Base):
    """Модель расписания услуги"""
    __tablename__ = 'service_schedules'

    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ServiceSchedule {self.service_id} {self.day_of_week}>'

class TicketStatistics(Base):
    """Модель статистики талонов"""
    __tablename__ = 'ticket_statistics'

    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey('services.id', ondelete='CASCADE'), nullable=False)
    date = Column(Date, nullable=False)
    issue_time = Column(Time, nullable=True)
    call_time = Column(Time, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<TicketStatistics {self.service_id} {self.date}>'
