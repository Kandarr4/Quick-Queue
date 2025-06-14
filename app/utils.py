import pytz
from datetime import datetime


def get_local_time():
    tz = pytz.timezone('Asia/Oral')  # Time zone for West Kazakhstan (UTC+5)
    return datetime.now(tz)
