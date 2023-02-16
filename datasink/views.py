import time
from dateutil import parser
from cassandra import WriteTimeout
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime,timedelta
from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseBadRequest
import httplib
#from apps import *
from dataviz.models import JPlug_Data_Table
from forms import JPlug_Upload_Form

import pytz
import logging
import re


NAME_FIELD_SEPARATOR = "_"

FREQUENCY_POS = 0
VOLTAGE_POS = 1
ACTIVE_POS = 2
ENERGY_POS = 3
COST_POS = 4
CURRENT_POS = 5
REACTIVE_POS = 6
APPARENT_POS = 7
POWER_FACTOR_POS = 8
ANGLE_POS = 9
TIME_STRING_POS = 10
TIME_POS = 11
DATE_POS = 12
MAC_ADDRESS_POS = 14
PREMISE_LOAD_NAME_POS = 15
PACKET_COUNTER_POS = 16

# Matches either a '+'
# NOTE - DO NOT INCLUDE % in this list as we need that for removing %2B
REGEX_UNWANTED_SYMBOLS = re.compile('[+]')
REGEX_2B = re.compile('%2B', re.IGNORECASE)

# since the plugs support seconds-level accuracy, we add this slack while comparing
# the reported timestamp with the server's clock.
TIME_SLACK = timedelta(seconds=1)

#TODO - we must handle mutliple timezones
IST = pytz.timezone('Asia/Kolkata')
IST_TIMEZONE_DIFF = timedelta(seconds=19800)

logger = logging.getLogger(__name__)
# TODO - 1 - change it to an appropriate level at the time of deployment
logger.setLevel(logging.DEBUG)

# Number of attempts to make with the db
MAX_READ_ATTEMPTS = 5
MAX_WRITE_ATTEMPTS = 5

CASSANDRA_BREATHING_SPACE = 1  # in seconds


# Create your views here.
@csrf_exempt
def index(request):

    allowed_methods = ['POST']
    if request.method != 'POST':
        logger.info('Rejecting request because the request method is invalid: ' + request.method)
        return HttpResponseNotAllowed(allowed_methods)

    form = JPlug_Upload_Form(request.POST)

    if not form.is_valid():
        logger.info('submitted form is not valid: ' + str(form.errors))
        return HttpResponseBadRequest(reason="Invalid Form." + str(form.errors))

    mac_address = form.cleaned_data['macaddress']

    # remove + character
    payload = re.sub(REGEX_UNWANTED_SYMBOLS, '', form.cleaned_data['datapoint'])
    # remove %2B
    payload = re.sub(REGEX_2B, '', payload)

    data_fields = payload.split(' ')

    if len(data_fields) < 17:
        logger.info('Rejecting record as it does not contain all the data fields:' + payload)
        return HttpResponseBadRequest(reason="Does not contain all the data fields.")

    [my_premise, my_load] = data_fields[PREMISE_LOAD_NAME_POS].strip().split(NAME_FIELD_SEPARATOR)
    reported_time = data_fields[DATE_POS].strip() + ' ' + data_fields[TIME_POS].strip()
    dt_reported_time = datetime.strptime(reported_time, '%d/%m/%y %H:%M:%S')

    # TODO - we must handle multiple timezones
    localized_dt_reported_time = IST.localize(dt_reported_time)
    # assuming the server is set to IST
    localized_current_time = IST.localize(datetime.now())
    if localized_dt_reported_time > (localized_current_time + TIME_SLACK):
        logger.info('Rejecting record as the timestamp is in the future: ' +
                    localized_current_time.strftime('%Y-%m-%d %H:%M:%S') + ' less than ' +
                    localized_dt_reported_time.strftime('%Y-%m-%d %H:%M:%S'))
        return HttpResponseBadRequest(reason="Reported timestamp is in the future.")

    try:
        my_active = float(data_fields[ACTIVE_POS])
        my_apparent = float(data_fields[APPARENT_POS])
        my_cost = float(data_fields[COST_POS])
        my_current = float(data_fields[CURRENT_POS])
        my_energy = float(data_fields[ENERGY_POS])
        my_frequency = float(data_fields[FREQUENCY_POS])
        # TODO -1  - double check whether the outer mac address and this one exact same values
        # field_mac_address = data_fields[MAC_ADDRESS_POS]
        my_angle = float(data_fields[ANGLE_POS])
        my_power_factor = float(data_fields[POWER_FACTOR_POS])
        my_reactive = float(data_fields[REACTIVE_POS])
        my_voltage = float(data_fields[VOLTAGE_POS])

    except ValueError:
        logger.info('Rejecting record as it contains invalid data values: ' + payload)
        return HttpResponseBadRequest(reason="Invalid Data Values.")

    # log the data
    msg = mac_address + ": " + payload
    # Insert the new record into the database
    logger.debug('Inserting: ' + msg)

    attempts = 0
    writing_done = False
    while not writing_done and attempts < MAX_WRITE_ATTEMPTS:
        try:
            # Note cassandra does not impose uniqueness constraint.
            # If a record with the same premise, load and sample_time exists,
            # it will be overwritten.
            data_record = JPlug_Data_Table(premise=my_premise,
                                           load=my_load,
                                           sample_time=localized_dt_reported_time,
                                           active=my_active,
                                           angle=my_angle,
                                           apparent=my_apparent,
                                           cost=my_cost,
                                           current=my_current,
                                           energy=my_energy,
                                           frequency=my_frequency,
                                           insertion_time=localized_current_time,
                                           mac=mac_address,
                                           power_factor=my_power_factor,
                                           reactive=my_reactive,
                                           voltage=my_voltage)
            data_record.save()
            writing_done = True
        except WriteTimeout:
            attempts += 1
            logger.info("Write timed out. " + "Attempt: " + str(attempts))
            time.sleep(attempts * CASSANDRA_BREATHING_SPACE)

    if not writing_done and attempts >= MAX_READ_ATTEMPTS:
        # TODO we must preserve the data in a file.
        logger.info("Executing status_table_update_prepared_statement  timed out")
        return HttpResponse("Server issues", content_type='text/plain',
                            status=httplib.INTERNAL_SERVER_ERROR)

    return HttpResponse("File accepted", content_type="text/plain", status=httplib.OK)



# from cqlengine import columns
# from cqlengine.models import Model
# from django.conf import settings
# from django.template import RequestContext, loader
# from dataviz.models import JPlug_Data_Table
# from datetime import timedelta
# from django.core.urlresolvers import reverse
# from django.http import HttpResponseRedirect
# from cassandra.cluster import Cluster
# from django.db import connection
# from cassandra.auth import PlainTextAuthProvider
# import os
# from __init__ import *
# from django.shortcuts import render
# from django.core.files import File
# import re
# import logging




    # # check whether this data already exists in the JPlug data table
    # # we check this to ensure the status table is updated correctly with the
    # # number of records
    # attempts = 0
    # reading_done = False
    # results = None
    # while not reading_done and attempts < MAX_READ_ATTEMPTS:
    #     try:
    #         results = cassandra_session.execute(data_table_read_prepared_statement,
    #                                             [premise, load, localized_dt_reported_time])
    #         reading_done = True
    #     except ReadTimeout:
    #         attempts += 1
    #         logger.info("Read timed out. " + "Attempt: " + attempts)
    #         time.sleep(attempts * CASSANDRA_BREATHING_SPACE)
    #
    # if not reading_done and attempts >= MAX_READ_ATTEMPTS:
    #     logger.info("Executing data_table_read_prepared_statement  timed out")
    #     return HttpResponse("Server issues", content_type='text/plain',
    #                         status=httplib.INTERNAL_SERVER_ERROR)
    #
    # if len(results) > 0:
    #     logger.debug('Record already exists in the JPlug_Data_Table: ' + msg)
    #     # let us return a response here so jplug can continue with its work
    #     # TODO - 1 - Ensure it is ok to send a OK message for duplicate records
    #

    # reading_done = False
    # results = None
    # while not reading_done and attempts < MAX_READ_ATTEMPTS:
    #     try:
    #         results = cassandra_session.execute(status_table_read_prepared_statement, [premise, load])
    #         reading_done = True
    #     except ReadTimeout:
    #         attempts += 1
    #         logger.info("Read timed out. " + "Attempt: " + attempts)
    #         time.sleep(attempts * CASSANDRA_BREATHING_SPACE)
    #
    # if not reading_done and attempts >= MAX_READ_ATTEMPTS:
    #     logger.info("Executing status_table_read_prepared_statement  timed out")
    #     return HttpResponse("Server issues", content_type='text/plain',
    #                         status=httplib.INTERNAL_SERVER_ERROR)


# # let us check whether the premise and load are in JPlug status table
#     # This is a new record for the status table.
#     if results is None or len(results) == 0:
#         logger.debug('Premise and load do not exist in the JPlug_Status_Table: ' + msg)
#         data_count = 1
#         localized_last_sample_time = localized_dt_reported_time + IST_TIMEZONE_DIFF
#         alarms_raised = 0
#     else:
#         logger.debug('Premise and load already exist in the JPlug_Status_Table: ' + msg)
#         record = results[0]
#         localized_last_sample_time = IST.localize(record.last_sample_time) + IST_TIMEZONE_DIFF
#         data_count = record.data_count + 1
#         alarms_raised = record.alarms_raised
#
#         # check whether the reported sample is newer
#         if localized_dt_reported_time > localized_last_sample_time:
#             localized_last_sample_time = localized_dt_reported_time
#             alarms_raised = 0

# return HttpResponse("Not sufficient data",content_type = "text/plain",status=200)
#                 return response
#                 except NameError,e:
#             name_error_reason = str(e)
#             data_name_error = name_error_reason + ' ' + data
#                     fileobj = open(os.path.join(settings.MEDIA_ROOT, 'NAME_ERROR.txt'), 'ab')
#
#                     fileobj.write(data_name_error)
#                     fileobj.close()
#             response = HttpResponse("Not sufficient data",content_type = "text/plain",status=200)
#                 return response
    #
    #         else:  # data with lesser fields
    #
    #
    #     fileobj = open(os.path.join(settings.MEDIA_ROOT, 'INSUFFICIENT_DATA.txt'), 'ab')
    #
    #             fileobj.write(data)
    #             fileobj.close()
    #     response = HttpResponse("Not sufficient data",content_type = "text/plain",status=200)
    #
    #         return response
    #
    #
    # else:
    #
    #     #form = JPlug_Data_Table_Form()
    #
    # return HttpResponse("No Data")
