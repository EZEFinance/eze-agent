import schedule
import time
from datetime import datetime
import pytz
from src.rules import runner

utc = pytz.utc

def task_periodicly():
    runner()

schedule.every().hour.at(":00").do(task_periodicly)

while True:
    schedule.run_pending()
    time.sleep(1)
