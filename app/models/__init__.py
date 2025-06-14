#app/models/init.py
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.models.models_app import Admin
from app.models.secondary_admin import (
    Base, User, Service, Ticket, Terminal,
    Display, ServiceAssignment, ServiceSchedule, TicketStatistics
)

__all__ = [
    'Admin', 'Base', 'User', 'Service', 'Ticket',
    'Terminal', 'Display', 'ServiceAssignment',
    'ServiceSchedule', 'TicketStatistics'
]
