#app/tablo/init.py

from flask import Blueprint

tablo = Blueprint('tablo', __name__, template_folder='templates')

from . import routes
