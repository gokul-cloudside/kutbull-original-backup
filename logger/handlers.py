from logging import Handler
from django.utils import timezone
import json, datetime, random, logging

clog = logging.getLogger("dataglen.rest_views")
clog.setLevel(logging.DEBUG)

class DBHandler(Handler, object):
    """
    This handler will add logs to a database model defined in settings.py
    """
    model_name = None

    def __init__(self, model=""):
        super(DBHandler,self).__init__()
        self.model_name = model

    def emit(self,record):
        # big try block here to exit silently if exception occurred
        try:
            # instantiate the model
            try:
                model = self.get_model(self.model_name)
            except:
                # silently
                return

            log_entry = model(ts=timezone.now(),
                              level=record.levelname,
                              message=self.format(record))
            # test if msg is json and apply to log record object
            try:
                data = json.loads(record.msg)
                for key,value in data.items():
                    if hasattr(log_entry,key):
                        try:
                            setattr(log_entry,key,value)
                        except:
                            pass
            except Exception as exception:
                clog.info(exception)
                pass

            log_entry.save()
        except Exception as exception:
            clog.info("EXCEPTION IN HANDLER: %s", exception)
            pass

    def get_model(self, name):
        names = name.split('.')
        mod = __import__('.'.join(names[:-1]), fromlist=names[-1:])
        return getattr(mod, names[-1])