import uuid
import logging


class Logger:

    """Initialises a logger"""

    logger = logging.getLogger(__name__)
    syslog = logging.FileHandler('testing.log')
    formatter = logging.Formatter('%(unique_id)s  %(asctime)s  %(message)s')
    syslog.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(syslog)


class AppFilter(logging.Filter):

    def __init__(self):
        """ Initializes logging Filter with unique_id"""
        self.id = uuid.uuid4()

    def filter(self, record):
        record.unique_id = self.id
        return True
