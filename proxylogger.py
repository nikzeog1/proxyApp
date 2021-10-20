import uuid
import logging


class AppFilter(logging.Filter):

    def __init__(self):
        self.id = uuid.uuid4()

    def filter(self, record):
        record.unique_id = self.id
        return True
