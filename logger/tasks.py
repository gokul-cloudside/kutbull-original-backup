from __future__ import absolute_import
from celery import shared_task
import logging
import traceback
import sys
from logger.models import DataWriteHistoryByUser, DataWriteHistoryBySource
from logger.models import ActionLogByUser, ActionLogBySource, ActionLogByError
from logger.models import IndependentErrors
from dataglen.models import InvalidDataStorageBySource
from cassandra.util import uuid_from_time
from cassandra.cqlengine.query import BatchQuery
from django.conf import settings
from django.db import connections
from solarrms.tasks import write_inverter_energy, write_plant_energy
# DO NOT CHANGE THIS IMPORT!
from kutbill.worker import *

# get a logger
logger = logging.getLogger('dataglen.views')
logger.setLevel(logging.DEBUG)
celery_logger = get_task_logger(__name__)

def write_logging_errors(func_name):
    try:
        logger.debug("%s,%s,%s",
                     func_name, traceback.format_exc(),
                     repr(traceback.extract_stack()))
    except:
        # fail silently
        return

@shared_task
def write_action_log_by_error_user_source(error, date, ts, user_id, action, ip_address,
                                          comments, success, response_code, source_key=None):
    """
    Write ActionLog by Error, User and optionally Source [if there is a key]
    (1) Data write errors - where there's an error, user and source available
    (2) User errors - where there's an error and user available
    """
    try:
        batch_query = BatchQuery()
        ActionLogByError.batch(batch_query).create(error=error,
                                                   date=date,
                                                   ts=ts,
                                                   user_id=user_id,
                                                   action=action,
                                                   uuid=uuid_from_time(ts),
                                                   success=success,
                                                   ip_address=ip_address,
                                                   comments=comments)
        ActionLogByUser.batch(batch_query).create(user_id=user_id,
                                                  success=success,
                                                  date=date,
                                                  ts=ts,
                                                  action=action,
                                                  uuid=uuid_from_time(ts),
                                                  source_key=source_key,
                                                  response_code=response_code,
                                                  ip_address=ip_address,
                                                  comments=comments)
        if source_key:
            ActionLogBySource.batch(batch_query).create(source_key=source_key,
                                                        success=success,
                                                        ts=ts,
                                                        action=action,
                                                        response_code=response_code,
                                                        ip_address=ip_address)
        batch_query.execute()
        return 0
    except:
        write_logging_errors(sys._getframe().f_code.co_name)
        return 1


@shared_task
def write_action_log_by_user_source(user_id, success, date, ts, action, response_code,
                                    ip_address, comments={}, source_key=None):
    """
        Write ActionLog by User and optionally Source [if there is a key]
        (1) Data write success action (in User and Source ActionLog only)
        (2) Write User action success (in User table only)
    """
    try:
        batch_query = BatchQuery()
        ActionLogByUser.batch(batch_query).create(user_id=user_id,
                                                  success=success,
                                                  date=date,
                                                  ts=ts,
                                                  action=action,
                                                  uuid=uuid_from_time(ts),
                                                  source_key=source_key,
                                                  response_code=response_code,
                                                  ip_address=ip_address,
                                                  comments=comments)
        if source_key:
            ActionLogBySource.batch(batch_query).create(source_key=source_key,
                                                        success=success,
                                                        ts=ts,
                                                        action=action,
                                                        response_code=response_code,
                                                        ip_address=ip_address,
                                                        comments=comments)
        batch_query.execute()
        return 0
    except:
        write_logging_errors(sys._getframe().f_code.co_name)
        return 1


@shared_task
def write_independent_error(error, ts, action, response_code, ip_address, comments):
    """
    Independent errors - where there is no User associated.
    """
    try:
        independent_error = IndependentErrors(error=error,
                                              date=ts.date(),
                                              ts=ts,
                                              action=action,
                                              uuid=uuid_from_time(ts),
                                              response_code=response_code,
                                              ip_address=ip_address,
                                              comments=comments)
        independent_error.save()
        return 0
    except:
        write_logging_errors(sys._getframe().f_code.co_name)
        return 1


@shared_task
def write_source_data_write_history(user_id, source_key, success, date, ts):
    """
    Write source data write history [Success or a Failure].
    """
    try:
        batch_query = BatchQuery()
        DataWriteHistoryByUser.batch(batch_query).create(user_id=user_id,
                                                         success=success,
                                                         date=date,
                                                         ts=ts,
                                                         source_key=source_key,
                                                         validated=success)
        DataWriteHistoryBySource.batch(batch_query).create(source_key=source_key,
                                                           success=success,
                                                           ts=ts,
                                                           user_id=user_id,
                                                           validated=success)
        batch_query.execute()
        return 0
    except:
        write_logging_errors(sys._getframe().f_code.co_name)
        return 1


@shared_task
def write_invalid_data_storage_by_source(source_key, insertion_time, data, error, comments):
    """
    Keep invalid data.
    """
    try:
        invalid_data = InvalidDataStorageBySource(source_key=source_key,
                                                  insertion_time=insertion_time,
                                                  data=data,
                                                  error=error,
                                                  comments=comments)
        invalid_data.save()
        return 0
    except Exception as exc:
        write_logging_errors(sys._getframe().f_code.co_name)
        return 1


@shared_task
def update_counters(user_id, source_key, ts, success, increment):
    try:
        identifiers = [str(user_id), source_key, settings.IDENTIFIER_FOR_ALL_USERS_DATA_SUM]
        timestamps = [(settings.DATA_COUNT_PERIODS.SECOND, ts.replace(microsecond=0)),
                      (settings.DATA_COUNT_PERIODS.MINUTE, ts.replace(second=0, microsecond=0)),
                      (settings.DATA_COUNT_PERIODS.HOUR, ts.replace(minute=0, second=0, microsecond=0)),
                      (settings.DATA_COUNT_PERIODS.DAILY, ts.replace(hour=0, minute=0, second=0, microsecond=0)),
                      (settings.DATA_COUNT_PERIODS.AGGREGATED, settings.EPOCH_TIME)]
        session = connections['cassandra'].connection.session
        # update all counters here
        # TODO it should be a batch query for counter updates. check if possible with Celery
        # TODO cannot be done with cqlengine because that would need a Model.objects.get call first -
        # TODO making the process inefficient.
        if session:
            if success:
                update_counters_statement = session.prepare("UPDATE dataglen_data.data_count_table SET valid_records = valid_records + ? WHERE timestamp_type = ? AND count_time_period = ? AND identifier = ? AND ts = ?")
            else:
                update_counters_statement = session.prepare("UPDATE dataglen_data.data_count_table SET invalid_records = invalid_records + ? WHERE timestamp_type = ? AND count_time_period = ? AND identifier = ? AND ts = ?")
            for identifier in identifiers:
                for entry in timestamps:
                    session.execute(update_counters_statement, [increment,
                                                                settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                entry[0],
                                                                identifier,
                                                                entry[1]])
        """if success:
            write_plant_energy(user_id, source_key, ts, increment)
            write_inverter_energy(user_id, source_key, ts, increment)"""
        return 0
    except:
        write_logging_errors(sys._getframe().f_code.co_name)
        return 1
