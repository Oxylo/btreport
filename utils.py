import os
from datetime import datetime


def timestamp2str(ts):
    """ Converts Timestamp object to str containing date and time
    """
    date = ts.date().strftime("%Y-%m-%d")
    time = ts.time().strftime("%H:%M:%S")
    return ' '.join([date, time])


def get_now():
    """ Return current datetime as str
    """
    return timestamp2str(datetime.now())


def dir_exists(foldername):
    """ Return True if folder exists, else False
    """
    return os.path.isdir(foldername)
