#app/terminal/init.py
from flask import Blueprint

terminal = Blueprint('terminal', __name__, template_folder='templates')

from . import services, tickets, routes
