#app/main_admin/init.py
from flask import Blueprint

main_admin = Blueprint('main_admin', __name__, template_folder='templates')

from . import routes