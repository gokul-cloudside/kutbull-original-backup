from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from dataglen.models import Sensor
from dataglen.models import ValidDataStorageByStream
from dateutil import parser

from django.utils import timezone
from utils.errors import log_and_return_error, log_and_return_independent_error, generate_exception_comments

import json, datetime, sys, logging

logger = logging.getLogger('dataglen.views')
# TODO: Change the logging status to an appropriate level at the time of deployment
logger.setLevel(logging.DEBUG)

@login_required
@csrf_exempt
def scatter_data(request):
    request_arrival_time = timezone.now()
    if request.user.is_authenticated():
        if request.method == "POST":
            try:
                # extract the parameters from the GET request
                # TODO : change this to a form if possible
                source_key = request.POST['source_key']
                x_axis = request.POST['x_axis']
                x_type = request.POST['x_type']
                y_axis = request.POST['y_axis']
                y_type = request.POST['y_type']
                start_time = request.POST['start_time']
                start_time = datetime.datetime.strptime(start_time, "%Y/%m/%d %H:%M")
                end_time = request.POST['end_time']
                end_time = datetime.datetime.strptime(end_time, "%Y/%m/%d %H:%M")

                # check the source key
                try:
                    source = Sensor.objects.get(sourceKey=source_key,
                                                isTemplate=False)
                except:
                    return log_and_return_error(request.user.id, request, request_arrival_time,
                                                settings.ERRORS.INVALID_DATA,
                                                settings.RESPONSE_TYPES.DJANGO, False,
                                                {'function_name': sys._getframe().f_code.co_name})

                x_data = ValidDataStorageByStream.objects.filter(source_key=source_key,
                                                                 stream_name=x_axis,
                                                                 timestamp_in_data__gte=start_time,
                                                                 timestamp_in_data__lte=end_time).limit(0).values_list('stream_value')
                y_data = ValidDataStorageByStream.objects.filter(source_key=source_key,
                                                                 stream_name=y_axis,
                                                                 timestamp_in_data__gte=start_time,
                                                                 timestamp_in_data__lte=end_time).limit(0).values_list('stream_value')

                try:
                    assert(len(x_data) == len(y_data))
                except:
                    return log_and_return_error(request.user.id, request, request_arrival_time,
                                                settings.ERRORS.STREAMS_INCONSISTENCY,
                                                settings.RESPONSE_TYPES.DJANGO, False,
                                                {'function_name': sys._getframe().f_code.co_name})

                if x_type == "TIMESTAMP":
                    x_data = [[int(parser.parse(value[0]).strftime("%s")) * 1000] for value in x_data]
                    #x_data = [[int(datetime.datetime.strptime(value[0], "%Y-%m-%d %H:%M:%S").strftime("%s")) * 1000] for value in x_data]
                if y_type == "TIMESTAMP":
                    y_data = [[int(parser.parse(value[0]).strftime("%s")) * 1000] for value in y_data]
                    #y_data = [[int(datetime.datetime.strptime(value[0], "%Y-%m-%d %H:%M:%S").strftime("%s")) * 1000] for value in y_data]

                # extract and cast the data
                f_data = []
                for i in range(len(x_data)):
                    f_data.append({'x': x_data[i][0],
                                   'y': y_data[i][0]})

                # return the values
                return HttpResponse(json.dumps(f_data),
                                    content_type="application/json")

            except:
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