from dataglen.serializers import SensorSerializer, FieldSerializer
from dataglen.models import Sensor, Field, ValidDataStorageByStream
from dataglen.data_views import data_write

from utils.errors import log_and_return_error, generate_exception_comments
from logger.views import log_a_success, log_an_error
from dateutil import parser

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import permissions

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.conf import settings
from django.utils import timezone

from rest_framework.authentication import TokenAuthentication

import logging, sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class SensorList(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format = None):
        request_arrival_time = timezone.now()
        # check if there's a source key mentioned in the request.
        # give details on the specific source key if mentioned, otherwise,
        # on all the sensors
        try:
            source_key = request.query_params['sourceKey']
        except KeyError:
            source_key = None
        try:
            if source_key:
                source = Sensor.objects.get(user=request.user,
                                            isTemplate=False,
                                            sourceKey=source_key)
                serializer = SensorSerializer(source)
                response = Response(serializer.data,
                                    status=status.HTTP_200_OK)
                log_a_success(request.user.id, request, response.status_code,
                              request_arrival_time, source_key=source_key)
                return response
            else:
                sources = Sensor.objects.filter(user=request.user,
                                                isTemplate=False)
                serializer = SensorSerializer(sources, many=True)
                response = Response(serializer.data, status=status.HTTP_200_OK)
                log_a_success(request.user.id, request, response.status_code,
                              request_arrival_time, source_key=source_key)
                return response
        except ObjectDoesNotExist as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request,
                                        request_arrival_time, settings.ERRORS.INVALID_SOURCE_KEY,
                                        settings.RESPONSE_TYPES.DRF, False,
                                        comments, source_key=source_key)
        # check for broad errors (ones we don't know yet)
        except:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request,
                                        request_arrival_time, settings.ERRORS.INTERNAL_SERVER_ERROR,
                                        settings.RESPONSE_TYPES.DRF, False,
                                        comments, source_key=source_key)

    def post(self, request, format=None):
        request_arrival_time = timezone.now()
        try:
            serializer = SensorSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=request.user)
                response = Response(serializer.data, status=status.HTTP_201_CREATED)
                log_a_success(request.user.id, request, response.status_code,
                              request_arrival_time, comments={'response': serializer.data})
                return response
            else:
                response = Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                log_an_error(request.user.id, request, str(serializer.errors), response.status_code,
                             settings.ERRORS.BAD_REQUEST.description, request_arrival_time, False)
                return response
        except IntegrityError:
            try:
                source = Sensor.objects.get(user=request.user,
                                            name=request.data["name"],
                                            isTemplate=False)
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.DUPLICATE_SOURCE, settings.RESPONSE_TYPES.DRF,
                                            False, comments,
                                            response_params=[('sourceKey', source.sourceKey)],
                                            source_key=source.sourceKey)
            except:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
        # check for broad errors (ones we don't expect)
        except:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

    def patch(self, request, format=None):
        request_arrival_time = timezone.now()
        try:
            key = request.data["sourceKey"]
            serializer = SensorSerializer(Sensor.objects.get(sourceKey=key),
                                          data=request.data,
                                          partial=True)
            if serializer.is_valid():
                serializer.save(user=request.user)
                response = Response(serializer.data, status=status.HTTP_201_CREATED)
                log_a_success(request.user.id, request, response.status_code,
                              request_arrival_time, source_key=key)
                return response
            else:
                response = Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                log_an_error(request.user.id, request, str(serializer.errors), response.status_code,
                             settings.ERRORS.BAD_REQUEST.description, request_arrival_time, False)
                return response
        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        except KeyError:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        # check for broad errors (ones we don't expect)
        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

    def delete(self, request, format=None):
        request_arrival_time = timezone.now()
        try:
            key = request.data["sourceKey"]
            source = Sensor.objects.get(user=request.user,
                                        sourceKey=key,
                                        isTemplate=False)
            source.delete()
            response = Response(status=status.HTTP_204_NO_CONTENT)
            log_a_success(request.user.id, request, response.status_code,
                          request_arrival_time, source_key=key)
            return response
        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        except KeyError:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        # check for broad errors (ones we don't expect)
        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)


class FieldList(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        request_arrival_time = timezone.now()
        try:
            source_key = request.query_params["key"]
            try:
                source = Sensor.objects.get(sourceKey=source_key)
            except ObjectDoesNotExist:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            fields = Field.objects.filter(sensor=source)
            serializer = FieldSerializer(fields, many=True)
            response = Response(serializer.data)
            log_a_success(request.user.id, request, response.status_code,
                          request_arrival_time, source_key=source_key)
            return response
        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        except KeyError:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        # check for broad errors (ones we don't know yet)
        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

    def post(self, request, format=None):
        request_arrival_time = timezone.now()
        try:
            key = request.data["key"]
            try:
                sensor = Sensor.objects.get(sourceKey=key)
            except ObjectDoesNotExist as exception:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            serializer = FieldSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(sensor=sensor)
                response = Response(serializer.data, status=status.HTTP_201_CREATED)
                log_a_success(request.user.id, request, response.status_code,
                              request_arrival_time, source_key=sensor.sourceKey)
                return response
            else:
                response = Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                log_an_error(request.user.id, request, str(serializer.errors), response.status_code,
                             settings.ERRORS.BAD_REQUEST.description, request_arrival_time, False)
                return response
        except IntegrityError as exception:
            try:
                field = Field.objects.get(source=sensor,
                                          name=request.data["name"])
            except ObjectDoesNotExist:
                try:
                    field = Field.objects.get(source=sensor,
                                              streamPositionInCSV=request.data["position"])
                except:
                    comments = generate_exception_comments(sys._getframe().f_code.co_name)
                    return log_and_return_error(request.user.id, request, request_arrival_time,
                                                settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                                False, comments)
            except:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.DUPLICATE_STREAM, settings.RESPONSE_TYPES.DRF,
                                        False, comments,
                                        response_params=[('name', field.name)], source_key=sensor.sourceKey)

        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        except KeyError:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        # check for broad errors (ones we don't expect)
        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

    def delete(self, request, format=None):
        request_arrival_time = timezone.now()
        try:
            key = request.data["key"]
            name = request.data["name"]
            try:
                source = Sensor.objects.get(sourceKey=key)
            except ObjectDoesNotExist as exception:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            stream = Field.objects.get(sensor=source,
                                       name=name)
            stream.delete()
            response = Response(status=status.HTTP_204_NO_CONTENT)
            log_a_success(request.user.id, request, response.status_code,
                          request_arrival_time, source_key=key)
            return response
        except ObjectDoesNotExist as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_DATA_STREAM, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        except KeyError:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        # check for broad errors (ones we don't expect)
        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

class DataWrite(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        request_arrival_time = timezone.now()
        try:
            try:
                start_time = request.GET["start"]
                st = parser.parse(start_time)
                end_time = request.GET["end"]
                et = parser.parse(end_time)
                key = request.GET["key"]
            except KeyError:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                            False, comments)

            try:
                source = Sensor.objects.get(sourceKey=key)
            except ObjectDoesNotExist as exception:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                            False, comments)

            try:
                streams = request.data["streams"].split(",")
            except KeyError:
                streams = Field.objects.filter(sensor=source).values_list('name').order_by('name')

            streams_data = []
            streams_name = []
            data_len = None
            for stream_num in range(len(streams)):
                stream = streams[stream_num][0]
                stream_data = ValidDataStorageByStream.objects.filter(source_key=key,
                                                                      stream_name=stream,
                                                                      timestamp_in_data__gte=st,
                                                                      timestamp_in_data__lte=et).limit(0).values_list('stream_value')
                if stream_num == 0:
                    data_len = len(stream_data)
                else:
                    assert(data_len == len(stream_data))
                streams_name.append(stream)
                streams_data.append([item for sublist in stream_data for item in sublist])
            json_data = {'streams': streams_name, 'data': zip(*streams_data)}
            response = Response(json_data, status=status.HTTP_200_OK)
            log_a_success(request.user.id, request, response.status_code,
                          request_arrival_time, source_key=key)
            return response

        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

    def post(self, request, format=None):
        request_arrival_time = timezone.now()
        try:
            source_key = request.META['HTTP_KEY']
            return data_write(request,
                              request_arrival_time,
                              source_key,
                              settings.RESPONSE_TYPES.DRF)
        except:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
