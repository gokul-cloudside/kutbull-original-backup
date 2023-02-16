import logging

logger = logging.getLogger('cronjobs.views')
# TODO: Change the logging status to an appropriate level at the time of deployment
logger.setLevel(logging.DEBUG)

# Custom logger for using log database
class LogRouter(object):
    def db_for_read(self, model, **hints):
        logger.debug("LogRouter db_for_read called : %s", model._meta.app_label)
        if model._meta.app_label == 'logger':
            logger.debug("Returning logger")
            return 'logger'
        logger.debug("LogRouter db_for_read called : %s", model._meta.app_label)
        logger.debug("Returning None")
        return None

    def db_for_write(self, model, **hints):
        logger.debug("LogRouter db_for_write called : %s", model._meta.app_label)
        if model._meta.app_label == 'logger':
            logger.debug("Returning logger")
            return 'logger'
        logger.debug("LogRouter db_for_write called : %s", model._meta.app_label)
        logger.debug("Returning None")
        return None

    def allow_migrate(self, db, model):
        if db == 'logger':
            logger.debug("Returning logger")
            return model._meta.app_label == 'logger'
        elif model._meta.app_label == 'logger':
            logger.debug("Returning False")
            return False
        logger.debug("LogRouter allow_migrate called : app:%s,db:%s", model._meta.app_label, db)
        logger.debug("Returning None")
        return None
