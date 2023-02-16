from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from dataglen.data_views import data_write

from dataglen.models import Sensor
from logger.views import log_a_success
from utils.errors import log_and_return_error, log_and_return_independent_error, \
    generate_exception_comments

from logger.models import DataCountTable

import logging, json, sys


logger = logging.getLogger('dataglen.views')
# TODO: Change the logging status to an appropriate level at the time of deployment
logger.setLevel(logging.DEBUG)

def serializer_data(data, fields):
    # TODO what's the better way of doing this
    # create a new temporary array
    final_data = []
    for entry in data:
        temp_data = []
        # iterate through integer fields
        for field_name, field_value in entry.ifields.iteritems():
            if field_name in fields:
                temp_data.append((field_name, int(field_value)))
        # iterate through float fields
        for field_name, field_value in entry.ffields.iteritems():
            if field_name in fields:
                temp_data.append((field_name, float(field_value)))
        # iterate through text fields
        for field_name, field_value in entry.tfields.iteritems():
            if field_name in fields:
                temp_data.append((field_name, str(field_value)))
        if len(fields) == len(temp_data):
            final_data.append(sorted(temp_data))
    return final_data

# uploading data w/o any authentication
@csrf_exempt
def upload(request, source_key):
    request_arrival_time = timezone.now()
    if request.method == "POST":
        return data_write(request,
                   request_arrival_time,
                   source_key,
                   settings.RESPONSE_TYPES.DJANGO)
    else:
        return log_and_return_independent_error(request, request_arrival_time,
                                                settings.ERRORS.METHOD_NOT_ALLOWED,
                                                settings.RESPONSE_TYPES.DJANGO, False,
                                                {'function_name': sys._getframe().f_code.co_name})

def total_records(request):
    request_arrival_time = timezone.now()
    try:
        if request.method == "GET":
            total_entries = DataCountTable.objects.get(identifier=settings.IDENTIFIER_FOR_ALL_USERS_DATA_SUM,
                                                  timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                  count_time_period=settings.DATA_COUNT_PERIODS.AGGREGATED)
            response = JsonResponse({'records_count': total_entries.valid_records})
            log_a_success(request.user.id, request, response.status_code,
                          request_arrival_time)
            return response
        else:
            return log_and_return_independent_error(request, request_arrival_time,
                                                    settings.ERRORS.METHOD_NOT_ALLOWED,
                                                    settings.RESPONSE_TYPES.DJANGO, False,
                                                    {'function_name': sys._getframe().f_code.co_name})
    except:
        comments = generate_exception_comments(sys._getframe().f_code.co_name)
        return log_and_return_error(request.user.id, request, request_arrival_time,
                                    settings.ERRORS.INTERNAL_SERVER_ERROR,
                                    settings.RESPONSE_TYPES.DJANGO, False,
                                    comments)

@login_required()
def data_profile(request):
    request_arrival_time = timezone.now()
    if request.user.is_authenticated():
        if request.method == 'GET':
            try:
                valid_records = []
                discarded_records = []
                # get a list of sources
                sources = Sensor.objects.filter(user=request.user,
                                                isTemplate=False)
                # for each source, append valid and discarded records counts
                for source in sources:
                    #TODO this will get changed to settings.TIMESTAMP_TYPES.BASED_ON
                    try:
                        counts = DataCountTable.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.AGGREGATED,
                                                               identifier=source.sourceKey)
                    except:
                        continue
                    valid_records.append({"name": source.name, "children": [{"name": source.name,
                                                                            "size": int(counts.valid_records)}]})
                    discarded_records.append({"name": source.name, "children": [{"name": source.name,
                                                                                "size": int(counts.invalid_records)}]})
                valid_data = {"name": "valid", "children": valid_records}
                discarded_data = {"name": "invalid", "children": discarded_records}
                json_data = {'valid': valid_data, 'invalid': discarded_data}
                # TODO convert this to JSON later
                response = HttpResponse(json.dumps(json_data), content_type="application/json")
                log_a_success(request.user.id, request, response.status_code, request_arrival_time)
                return response
            except Exception as exception:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INTERNAL_SERVER_ERROR,
                                            settings.RESPONSE_TYPES.DJANGO, False,
                                            comments)
        else:
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.METHOD_NOT_ALLOWED,
                                        settings.RESPONSE_TYPES.DJANGO, False,
                                        {'function_name': sys._getframe().f_code.co_name})
    else:
        return log_and_return_independent_error(request, request_arrival_time,
                                                settings.ERRORS.UNAUTHORIZED_ACCESS,
                                                settings.RESPONSE_TYPES.DJANGO, False,
                                                {'function_name': sys._getframe().f_code.co_name})
