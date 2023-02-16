from dataglen.models import Sensor, Field
from .serializers import SourceSerializer, StreamSerializer, StreamDataValues, SourceDataValues, SourceDataValuesLatest
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render
from django.http import QueryDict
from action.models import ActionField
from config.models import ConfigField
from monitoring.models import SourceMonitoring
from logger.views import log_a_success, log_an_error
from utils.errors import log_and_return_error
from django.utils import timezone
from utils.errors import generate_exception_comments
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from rest_framework import authentication, permissions
from django.contrib.auth.decorators import login_required
from errors.models import ErrorField
from rest_framework import viewsets
import sys, logging, dateutil
from dataglen.models import ValidDataStorageByStream
from dataglen.data_views import data_write
import pytz
from dateutil import parser
from kutbill import settings
from dashboards.utils import is_owner
from rest_framework.exceptions import ParseError
from django.http import HttpResponseBadRequest, HttpResponseServerError
import json
from django.http import HttpResponse, JsonResponse
import httplib
import pandas as pd
from utils.views import send_solutions_infini_sms
from dataglen.models import Sensor
import datetime
from django.core.mail import send_mail

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)
from dataglen.data_views import get_all_sources_data, get_timeseries_data


class SMSManagerViewSet(viewsets.ViewSet):
    # TODO: for debug. Remove immediately.
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request):
        source_key = request.data.get('source_key', None)
        try:
            source = Sensor.objects.get(sourceKey=source_key)
            to_number = source.manager_phone
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if to_number is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        message = request.data.get('body', None)
        if message is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if send_solutions_infini_sms(to_number, message):
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class SourcesViewSet(viewsets.ViewSet):
    """
    Manage your data sources on the DataGlen platform.
    """
    # TODO: for debug. Remove immediately.
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'key'

    def list(self, request):
        """
            Returns a list of sources that are owned by you.
            ---
            request_serializer: SourceSerializer
            response_serializer: SourceSerializer
            responseMessages:
                - code : 200
                  message : Success
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        sources = Sensor.objects.filter(user=request.user,
                                        isTemplate=False)
        serializer = SourceSerializer(sources, many=True)
        response = Response(serializer.data, status=status.HTTP_200_OK)
        log_a_success(request.user.id, request, response.status_code,
                      request_arrival_time)
        return response

    def retrieve(self, request, key=None):
        """
            Get a source with the mentioned key.
            ---
            request_serializer: SourceSerializer
            response_serializer: SourceSerializer
            responseMessages:
                - code : 200
                  message : Success
                - code : 400
                  message : If the specified source key does not exist (INVALID_SOURCE_KEY).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        try:
            source = Sensor.objects.get(isTemplate=False,
                                        sourceKey=key)
            serializer = SourceSerializer(source)
            response = Response(serializer.data,
                                status=status.HTTP_200_OK)
            return response
        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request,
                                        request_arrival_time, settings.ERRORS.INVALID_SOURCE_KEY,
                                        settings.RESPONSE_TYPES.DRF, False,
                                        comments, source_key=key)
        # check for broad errors (ones we don't know yet)
        except:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request,
                                        request_arrival_time, settings.ERRORS.INTERNAL_SERVER_ERROR,
                                        settings.RESPONSE_TYPES.DRF, False,
                                        comments, source_key=key)

    def create(self, request):
        """
            Create a new data source.
            ---
            parameters:
                - name: body
                  type: WriteSourceSerializer
                  description: Details of the new source to be created.
                  required: True
                  paramType: body
            response_serializer: SourceSerializer
            responseMessages:
                - code : 201
                  message : Success. Accompanied with details of the new source.
                - code : 400
                  message : If any of the essential parameters are missing (BAD_REQUEST).
                - code : 409
                  message : If a source with the mentioned name already exists (DUPLICATE_SOURCE).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        # TODO: debugging
        logger.debug(request.META['HTTP_AUTHORIZATION'])
        logger.debug(request.META['CONTENT_TYPE'])
        logger.debug(request.META['CONTENT_LENGTH'])
        try:
            template = None
            serializer = SourceSerializer(data=request.data)
            if serializer.is_valid():
                # itemplate = request.data.get("isTemplate",None)
                template_name = request.data.get("templateName", None)
                if template_name is not None:
                    try:
                        template = Sensor.objects.get(name=template_name, isTemplate=True)
                        logger.debug(template)
                    except Sensor.DoesNotExist:
                        return HttpResponseBadRequest("Template name does not exist")
                else:
                    pass
                sensor = serializer.save(user=request.user)
                logger.debug(sensor)
                try:
                    if template:
                        fields = Field.objects.filter(source=template)
                        # copy all the fields
                        for field in fields:
                            existing_field_count = Field.objects.filter(source=sensor, name=field.name).count()
                            if existing_field_count == 0:
                                new_field = Field()
                                new_field.source = sensor
                                new_field.name = field.name
                                new_field.streamDataType = field.streamDataType
                                new_field.streamPositionInCSV = field.streamPositionInCSV
                                new_field.streamDataUnit = field.streamDataUnit
                                new_field.streamDateTimeFormat = field.streamDateTimeFormat
                                # save the field
                                new_field.save()

                        # copy action fields
                        actionfields = ActionField.objects.filter(source=template)
                        for field in actionfields:
                            existing_field_count = ActionField.objects.filter(source=sensor, name=field.name).count()
                            if existing_field_count == 0:
                                new_field = ActionField()
                                new_field.source = sensor
                                new_field.name = field.name
                                new_field.streamDataType = field.streamDataType
                                new_field.streamPositionInCSV = field.streamPositionInCSV
                                new_field.streamDataUnit = field.streamDataUnit
                                new_field.streamDateTimeFormat = field.streamDateTimeFormat
                                # save the field
                                new_field.save()

                        # copy config fields
                        configfields = ConfigField.objects.filter(source=template)
                        for field in configfields:
                            existing_field_count = ConfigField.objects.filter(source=sensor, name=field.name).count()
                            if existing_field_count == 0:
                                new_field = ConfigField()
                                new_field.source = sensor
                                new_field.name = field.name
                                new_field.streamDataType = field.streamDataType
                                new_field.streamPositionInCSV = field.streamPositionInCSV
                                new_field.streamDataUnit = field.streamDataUnit
                                new_field.streamDateTimeFormat = field.streamDateTimeFormat
                                # save the field
                                new_field.save()

                        # copy errors fields
                        errorfields = ErrorField.objects.filter(source=template)
                        for field in errorfields:
                            existing_field_count = ErrorField.objects.filter(source=sensor, name=field.name).count()
                            if existing_field_count == 0:
                                new_field = ErrorField()
                                new_field.source = sensor
                                new_field.name = field.name
                                new_field.streamDataType = field.streamDataType
                                new_field.streamPositionInCSV = field.streamPositionInCSV
                                new_field.streamDataUnit = field.streamDataUnit
                                new_field.streamDateTimeFormat = field.streamDateTimeFormat
                                # save the field
                                new_field.save()

                        sensor.templateName = template_name
                        sensor.save()
                except Exception as exception:
                    logger.debug(str(exception))
                    comments = generate_exception_comments(sys._getframe().f_code.co_name)
                    return log_and_return_error(request.user.id, request, request_arrival_time,
                                                settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                                False, comments)
                response = Response(serializer.data,
                                    status=status.HTTP_201_CREATED)
                log_a_success(request.user.id, request, response.status_code,
                              request_arrival_time, comments={'response': serializer.data})
                return response
            else:
                if len(serializer.errors.keys()) == 1 and serializer.errors.has_key('UID'):
                    UID_value = request.data.get('UID', None)
                    source = Sensor.objects.get(UID=UID_value,
                                                isTemplate=False)
                    # return HttpResponseBadRequest("ERROR:" + str(source))
                    comments = ''
                    return log_and_return_error(request.user.id, request, request_arrival_time,
                                                settings.ERRORS.DUPLICATE_SOURCE, settings.RESPONSE_TYPES.DRF,
                                                False, comments,
                                                response_params=[('sourceKey', source.sourceKey)],
                                                source_key=source.sourceKey)
                else:
                    response = Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    logger.debug(str(serializer.errors))
                    log_an_error(request.user.id, request, str(serializer.errors), response.status_code,
                                 settings.ERRORS.BAD_REQUEST.description, request_arrival_time, False)
                    return response

        except IntegrityError as e:
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
            except Exception as e:
                logger.debug(str(e))
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                            False, comments)


                # return HttpResponseBadRequest("ERROR:" + str(e))
        # check for broad errors (ones we don't expect)
        except ParseError as e:
            logger.debug(str(e))
            comments = {}
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.JSON_PARSE_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        except Exception as e:

            logger.debug(str(e))
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            # TODO: changed at present since there is an error in write_logging_errors() to read request.body RawPostDataException: You cannot access body after reading from request's data stream

            # logger.debug(comments)

            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

            # return HttpResponseBadRequest("ERROR:" + str(e))

    def partial_update(self, request, key=None):
        """
            Update an existing data source.
            ---
            parameters:
                - name: body
                  type: WriteSourceSerializer
                  description: Updated details of the source.
                  required: True
                  paramType: body
            response_serializer: SourceSerializer
            responseMessages:
                - code : 201
                  message : Success. Accompanied with updated details of the source.
                - code : 400
                  message : If any of the essential parameters are missing or invalid (BAD_REQUEST) or
                            If the specified source key does not exist (INVALID_SOURCE_KEY).
                - code : 409
                  message : If a source with the mentioned name already exists (DUPLICATE_SOURCE).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        try:
            serializer = SourceSerializer(Sensor.objects.get(sourceKey=key,
                                                             user=request.user),
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
        except ParseError:
            comments = {}
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.JSON_PARSE_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        # check for broad errors (ones we don't expect)
        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

    def destroy(self, request, key=None):
        """
            Delete a data source.
            ---
            responseMessages:
                - code : 204
                  message : Success. The source has been deleted.
                - code : 400
                  message : If the specified source key does not exist (INVALID_SOURCE_KEY).
                - code : 401
                  message : Not authenticated
        """
        # TODO : what all to do while deleting a source.
        request_arrival_time = timezone.now()
        try:
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
        # check for broad errors (ones we don't expect)
        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)


class StreamsViewSet(viewsets.ViewSet):
    """
    Manage your streams
    """

    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'stream_name'

    def list(self, request, source_key=None):
        """
            Get a list of streams for a source.
            ---
            response_serializer: StreamSerializer
            responseMessages:
                - code : 200
                  message : Success
                - code : 400
                  message : If the source key mentioned is invalid (INVALID_SOURCE_KEY).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        try:
            try:
                source = Sensor.objects.get(sourceKey=source_key)
            except ObjectDoesNotExist:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            streams = Field.objects.filter(source=source, isActive=True)
            serializer = StreamSerializer(streams, many=True)
            response = Response(serializer.data)
            log_a_success(request.user.id, request, response.status_code,
                          request_arrival_time, source_key=source_key)
            return response
        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        # check for broad errors (ones we don't know yet)
        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

    def retrieve(self, request, stream_name=None, source_key=None):
        """
            Get a stream with the mentioned key.
            ---
            response_serializer: StreamSerializer
            responseMessages:
                - code : 200
                  message : Success
                - code : 400
                  message : If the specified source key does not exist (INVALID_SOURCE_KEY) or
                            If the specified stream name does not exist (INVALID_DATA_STREAM).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        try:
            source = Sensor.objects.get(sourceKey=source_key)
        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        try:
            stream = Field.objects.get(source=source,
                                       name=stream_name)
            serializer = StreamSerializer(stream,
                                          many=False)
            response = Response(serializer.data)
            log_a_success(request.user.id, request, response.status_code,
                          request_arrival_time, source_key=source_key)
            return response
        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_DATA_STREAM, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        # check for broad errors (ones we don't know yet)
        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

    def partial_update(self, request, stream_name=None, source_key=None):
        """
            Update an existing data stream.
            ---
            parameters:
                - name: body
                  type: WriteStreamSerializer
                  description: Updated details of the stream.
                  required: True
                  paramType: body
            response_serializer: StreamSerializer
            responseMessages:
                - code : 201
                  message : Success
                - code : 401
                  message : Not authenticated
                - code : 400
                  message : If the specified key does not exist (INVALID_SOURCE_KEY) or
                            If the specified key does not exist (INVALID_DATA_STREAM).
        """

        request_arrival_time = timezone.now()
        try:
            source = Sensor.objects.get(sourceKey=source_key, user=request.user)
        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

        try:
            stream = Field.objects.get(source=source,
                                       name=stream_name)
            serializer = StreamSerializer(stream,
                                          data=request.data,
                                          partial=True)
            if serializer.is_valid():
                serializer.save(user=request.user)
                response = Response(serializer.data, status=status.HTTP_201_CREATED)
                log_a_success(request.user.id, request, response.status_code,
                              request_arrival_time, source_key=source_key)
                return response
            else:
                response = Response(serializer.errors,
                                    status=status.HTTP_400_BAD_REQUEST)
                log_an_error(request.user.id, request, str(serializer.errors), response.status_code,
                             settings.ERRORS.BAD_REQUEST.description, request_arrival_time, False)
                return response
        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_DATA_STREAM, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        except ParseError:
            comments = {}
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.JSON_PARSE_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        # check for broad errors (ones we don't know yet)
        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

    def create(self, request, source_key=None):
        """
            Create a new data stream.
            ---
            parameters:
                - name: body
                  type: WriteStreamSerializer
                  description: Details of the new stream to be created.
                  required: True
                  paramType: body
            response_serializer: StreamSerializer
            responseMessages:
                - code : 201
                  message : Success. Accompanied with details of the new stream.
                - code : 400
                  message : If the source key mentioned is invalid (INVALID_SOURCE_KEY) or
                            If any of the essential parameters are missing/invalid (BAD_REQUEST).
                - code : 409
                  message : If a stream with the mentioned name OR position already exists (DUPLICATE_STREAM).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        # get the source first
        try:
            source = Sensor.objects.get(sourceKey=source_key,
                                        user=request.user)
        except ObjectDoesNotExist as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        # save the new stream
        try:
            serializer = StreamSerializer(data=request.data)
            if serializer.is_valid():
                if source.dataFormat == "CSV":
                    try:
                        assert (serializer['streamPositionInCSV'].value)
                    except AssertionError:
                        comments = generate_exception_comments(sys._getframe().f_code.co_name)
                        return log_and_return_error(request.user.id, request, request_arrival_time,
                                                    settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                                    False, comments)
                serializer.save(source=source)
                response = Response(serializer.data, status=status.HTTP_201_CREATED)
                log_a_success(request.user.id, request, response.status_code,
                              request_arrival_time, source_key=source.sourceKey)
                return response
            else:
                response = Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                log_an_error(request.user.id, request, str(serializer.errors), response.status_code,
                             settings.ERRORS.BAD_REQUEST.description, request_arrival_time, False)
                return response
        except IntegrityError as exception:
            try:
                field = Field.objects.get(source=source,
                                          name=request.data["name"])
            except ObjectDoesNotExist:
                try:
                    field = Field.objects.get(source=source,
                                              streamPositionInCSV=request.data["streamPositionInCSV"])
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
                                        response_params=[('name', field.name),
                                                         ('streamPositionInCSV', field.streamPositionInCSV)],
                                        source_key=source.sourceKey)

        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        # check for broad errors (ones we don't expect)
        except ParseError:
            comments = {}
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.JSON_PARSE_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

    def destroy(self, request, stream_name=None, source_key=None):
        """
            Delete a data stream.
            ---
            responseMessages:
                - code : 204
                  message : Success. The source has been deleted.
                - code : 400
                  message : If the specified source key does not exist (INVALID_SOURCE_KEY) or
                            If the specified stream name does not exist (INVALID_DATA_STREAM).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        try:
            source = Sensor.objects.get(sourceKey=source_key, user=request.user)
        except ObjectDoesNotExist as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        try:
            stream = Field.objects.get(source=source,
                                       name=stream_name)
            stream.delete()
            response = Response(status=status.HTTP_204_NO_CONTENT)
            log_a_success(request.user.id, request, response.status_code,
                          request_arrival_time, source_key=source_key)
            return response
        except ObjectDoesNotExist as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_DATA_STREAM, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        # check for broad errors (ones we don't expect)
        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)


class MultipleSourcesDataRecords(viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        request_arrival_time = timezone.now()
        try:
            st = request.query_params.get("start")
            et = request.query_params.get("end")
            logger.debug(st)
            logger.debug(et)
            starttime = parser.parse(st)
            endtime = parser.parse(et)
            json = request.query_params.get("format", False) == "json"
            ffill_val = request.query_params.get("fill", False) == "ffill"
            union = request.query_params.get("merge", False) == "union"
            sources = {}
            for source in request.query_params.keys():
                if source not in ["start", "end", "format", "fill"]:
                    sources[source] = request.query_params.get(source).split(",")
            data = get_all_sources_data(sources, starttime, endtime, union=True, json=json, ffill=ffill_val)
            if data != -1:
                return Response(data, status=status.HTTP_200_OK)
            else:
                raise Exception
        except:
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                        False, {})


class TimeSeriesDataRecords(viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        request_arrival_time = timezone.now()
        try:
            st = request.query_params.get("start")
            et = request.query_params.get("end")
            try:
                archived = request.query_params.get("archived")
                if archived is None:
                    archived = False
                else:
                    archived = True
            except:
                archived = False

            starttime = parser.parse(st)
            endtime = parser.parse(et)
            logger.debug(archived)
            try:
                exclude_streams = request.query_params.get("exclude_streams").split(",")
            except:
                exclude_streams = []
            data = get_timeseries_data(request.user, starttime, endtime,
                                       exclude_streams=exclude_streams,
                                       archived=archived)

            if data != -1:
                return Response(data, status=status.HTTP_200_OK)
            else:
                raise Exception
        except:
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                        False, {})


class DataRecordsSet(viewsets.ViewSet):
    """
    Manage your data records
    """
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = "data"

    def list(self, request, source_key=None):
        """
            Get a list of data records for a source and a set of streams. In a single call, 1000 latest records will be sent.
            ---
            parameters:
                - name: startTime
                  type: dateTime
                  required: True
                  description: Start time of data lookup. It should be in ISO 8601 format. If there's no timezone mentioned, the default timezone will be of the source.
                  paramType: query
                - name: endTime
                  type: dateTime
                  description: End time of data lookup. It should be in ISO 8601 format. If there's no timezone mentioned, the default timezone will be of the source.
                  required: True
                  paramType: query
                - name: streamNames
                  type: string
                  description: A comma separated list of stream names that should be included in the data. If this parameter is not specified, all streams will be included.
                  required: False
                  paramType: query
                - name: timezone
                  type: string
                  required: False
                  description: This is used to fetch the timestamps in UTC if mentioned in the request, otherwise returns the response in ISO format.
                  paramType: query
                - name: latest
                  type: string
                  required: False
                  description: This parameter is used to fetch the latest record.
                  paramType: query
                - name: current
                  type: string
                  required: False
                  description: This parameter is used to fetch the current record.
                  paramType: query
            response_serializer: SourceDataValues
            responseMessages:
                - code : 200
                  message : Success
                - code : 400
                  message : If essential parameters are not specified in the request or dates are not mentioned in the correct format (BAD_REQUEST) or
                            If the source key mentioned is invalid (INVALID_SOURCE_KEY) or
                            If there is an invalid stream present in streamsNames (INVALID_DATA_STREAM)
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        try:
            source = Sensor.objects.get(sourceKey=source_key)
        except ObjectDoesNotExist as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

        latest = request.query_params.get("latest", "FALSE")
        time_zone = request.query_params.get("timezone", None)
        aggregated_streams = request.query_params.get("aggregated_streams", "FALSE")

        try:
            if time_zone:
                if time_zone.upper() == 'UTC':
                    tz = pytz.timezone(pytz.utc.zone)
                else:
                    tz = pytz.timezone(time_zone)
            else:
                tz = pytz.timezone(source.dataTimezone)
        except:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.SOURCE_CONFIGURATION_ISSUE, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

        source_streams = [item for sublist in Field.objects.filter(source=source).order_by('name').values_list('name')
                          for item in sublist]
        try:
            streams = request.query_params["streamNames"].split(",")
            streams = [stream.strip().lstrip() for stream in streams]
            for stream in streams:
                assert (stream in source_streams)
        except AssertionError:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_DATA_STREAM, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        except KeyError:
            streams = source_streams

        df_all = pd.DataFrame()
        if latest.upper() == 'FALSE':
            try:
                try:
                    st = request.query_params["startTime"]
                    et = request.query_params["endTime"]

                    # convert into datetime objects
                    st = parser.parse(st)
                    if st.tzinfo is None:
                        st = tz.localize(st)
                    et = parser.parse(et)
                    if et.tzinfo is None:
                        et = tz.localize(et)

                except:
                    comments = generate_exception_comments(sys._getframe().f_code.co_name)
                    return log_and_return_error(request.user.id, request, request_arrival_time,
                                                settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                                False, comments)

                streams_data_dicts = []
                for stream_num in range(len(streams)):
                    stream = streams[stream_num]
                    stream_data = ValidDataStorageByStream.objects.filter(source_key=source_key,
                                                                          stream_name=stream,
                                                                          timestamp_in_data__gte=st,
                                                                          timestamp_in_data__lte=et).limit(
                        settings.CASSANDRA_READ_RECORDS_LIMIT).values_list('stream_value', 'timestamp_in_data')
                    # populate data
                    values = [item[0] for item in stream_data]
                    # populate timestamps
                    timestamps = [item[1].replace(tzinfo=pytz.utc).astimezone(tz).isoformat() for item in stream_data]
                    if len(timestamps) > 2:
                        startTime = timestamps[-1]
                        endTime = timestamps[0]
                    elif len(timestamps) == 1:
                        startTime = endTime = timestamps[0]
                    else:
                        startTime = endTime = None

                    if startTime:
                        streams_data_dicts.append({'name': stream,
                                                   'count': len(values),
                                                   'startTime': startTime,
                                                   'endTime': endTime,
                                                   'timestamps': timestamps,
                                                   'values': values})
                    else:
                        streams_data_dicts.append({'name': stream,
                                                   'count': len(values),
                                                   'timestamps': timestamps,
                                                   'values': values})

                    # Make data frame for every stream               
                    try:
                        df_stream = pd.DataFrame(pd.Series(values), columns=[stream])
                        df_stream['timestamp'] = timestamps
                    except Exception as exception:
                        logger.debug(str(exception))
                    if df_all.empty:
                        df_all = df_stream
                    else:
                        df_new = pd.merge(df_all, df_stream, on='timestamp', how='outer')
                        df_all = df_new

                        # list of stream names
                reply = SourceDataValues(data={'sourceKey': source_key,
                                               'streams': streams_data_dicts})

                if aggregated_streams.upper() == 'TRUE':
                    try:
                        response = Response(json.loads(df_all.to_json(orient='records')),
                                            status=status.HTTP_200_OK)
                        return response
                    except:
                        return log_and_return_error(request.user.id, request, request_arrival_time,
                                                    settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                                    False, comments=None)

                else:
                    if reply.is_valid():
                        response = Response(reply.data,
                                            status=status.HTTP_200_OK)
                        log_a_success(request.user.id, request, response.status_code,
                                      request_arrival_time, comments=None)
                        return response
                    else:
                        comments = generate_exception_comments(sys._getframe().f_code.co_name)
                        return log_and_return_error(request.user.id, request, request_arrival_time,
                                                    settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                                    False, comments)


            except Exception as exception:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                logger.debug(comments)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                            False, comments)

        elif latest.upper() == 'TRUE':
            current = request.query_params.get("current", "FALSE")
            try:
                current_data = SourceMonitoring.objects.filter(source_key=source_key)
                time_out_interval = source.timeoutInterval
                if request_arrival_time.tzinfo is None:
                    request_arrival_time = tz.localize(request_arrival_time)
                monitoring_time = request_arrival_time - datetime.timedelta(seconds=time_out_interval)

                if current.upper() == 'TRUE':
                    if len(current_data) == 0:
                        reply = SourceDataValuesLatest(data={'sourceKey': source_key,
                                                             'streams': []})
                    else:
                        streams_data_dicts = []
                        for stream_num in range(len(streams)):
                            stream = streams[stream_num]
                            stream_data = ValidDataStorageByStream.objects.filter(source_key=source_key,
                                                                                  stream_name=stream,
                                                                                  timestamp_in_data__gte=monitoring_time).limit(
                                1).values_list('stream_value', 'timestamp_in_data')
                            # populate data
                            values = [item[0] for item in stream_data]
                            # populate timestamps
                            timestamps = [item[1].replace(tzinfo=pytz.utc).astimezone(tz).isoformat() for item in
                                          stream_data]
                            if len(values) > 0:
                                streams_data_dicts.append({'name': stream,
                                                           'timestamp': timestamps[0],
                                                           'value': values[0]})
                            # Make data frame for every stream
                            try:
                                df_stream = pd.DataFrame(pd.Series(values), columns=[stream])
                                df_stream['timestamp'] = timestamps
                            except Exception as exception:
                                logger.debug(str(exception))
                            if df_all.empty:
                                df_all = df_stream
                            else:
                                df_new = pd.merge(df_all, df_stream, on='timestamp', how='outer')
                                df_all = df_new

                        reply = SourceDataValuesLatest(data={'sourceKey': source_key,
                                                             'streams': streams_data_dicts})

                else:
                    streams_data_dicts = []
                    for stream_num in range(len(streams)):
                        stream = streams[stream_num]
                        stream_data = ValidDataStorageByStream.objects.filter(source_key=source_key,
                                                                              stream_name=stream).limit(1).values_list(
                            'stream_value', 'timestamp_in_data')
                        # populate data
                        values = [item[0] for item in stream_data]
                        # populate timestamps
                        timestamps = [item[1].replace(tzinfo=pytz.utc).astimezone(tz).isoformat() for item in
                                      stream_data]
                        if len(values) > 0:
                            streams_data_dicts.append({'name': stream,
                                                       'timestamp': timestamps[0],
                                                       'value': values[0]})
                        # Make data frame for every stream
                        try:
                            df_stream = pd.DataFrame(pd.Series(values), columns=[stream])
                            df_stream['timestamp'] = timestamps
                        except Exception as exception:
                            logger.debug(str(exception))
                        if df_all.empty:
                            df_all = df_stream
                        else:
                            df_new = pd.merge(df_all, df_stream, on='timestamp', how='outer')
                            df_all = df_new

                    reply = SourceDataValuesLatest(data={'sourceKey': source_key,
                                                         'streams': streams_data_dicts})

                if aggregated_streams.upper() == 'TRUE':
                    try:
                        response = Response(json.loads(df_all.to_json(orient='records')),
                                            status=status.HTTP_200_OK)
                        return response
                    except:
                        return log_and_return_error(request.user.id, request, request_arrival_time,
                                                    settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                                    False, comments=None)
                else:
                    if reply.is_valid():
                        response = Response(reply.data,
                                            status=status.HTTP_200_OK)
                        log_a_success(request.user.id, request, response.status_code,
                                      request_arrival_time, comments=None)
                        return response
                    else:
                        comments = generate_exception_comments(sys._getframe().f_code.co_name)
                        return log_and_return_error(request.user.id, request, request_arrival_time,
                                                    settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                                    False, comments)

            except Exception as exception:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                logger.debug(comments)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                            False, comments)

        else:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

    def create(self, request, source_key=None):
        """
            Write a new data record. Payload should be in the semantics as specified in the sensor configuration.
            ---
            parameters:
                - name : body
                  type: body
                  required: True
                  description: Actual body.
                  paramType: body
            responseMessages:
                - code : 200
                  message : Success. New record has been written into the database.
                - code : 400
                  message : If any of the essential parameters are missing (BAD_REQUEST ) or
                            If the data provided in the request body is not proper as per the data units of streams (INVALID_DATA) or
                            If the source key mentioned is invalid (INVALID_SOURCE_KEY) or
                            If the source is inactive (SOURCE_INACTIVE) or
                            If there is an error retrieving the payload (ERROR_RETRIEVING_PAYLOAD) or
                            If there is an error splitting multiple records (ERROR_SPLITTING_RECORDS) or
                            If there is an error in parsing multiple streams (ERROR_SPLITTING_STREAMS).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        try:
            try:
                if request.META['CONTENT_TYPE'] == "text/plain":  # it's a temporary fix for a bug in swagger-ui TODO
                    request.POST = QueryDict(request.body)
            except:
                pass

            # owner = False
            owner, client = is_owner(request.user)
            '''logger.debug(owner)
            logger.debug(client)
            logger.debug(type(client))
            logger.debug(client.dataglenclient.get_sensors())'''
            if owner is True:
                return data_write(request,
                                  request_arrival_time,
                                  source_key,
                                  settings.RESPONSE_TYPES.DRF, allowed_sources=client.dataglenclient.get_sensors())
            else:
                return data_write(request,
                                  request_arrival_time,
                                  source_key,
                                  settings.RESPONSE_TYPES.DRF)

        except Exception as exc:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            logger.debug(str(exc))
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)


class MultipleDataRecordsSet(viewsets.ViewSet):
    """
    Manage your data records for multiple sources
    """
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request):
        """
            Write new data records for multiple sources together in a single call. Payload should be in the semantics as specified in the sensor configuration.
            ---
            parameters:
                - name : body
                  type: body
                  required: True
                  description: Actual body.
                  paramType: body
            responseMessages:
                - code : 200
                  message : Success. New records have been written into the database.
                - code : 400
                  message : If any of the essential parameters are missing (BAD_REQUEST ) or
                            If the data provided in the request body is not proper as per the data units of streams (INVALID_DATA) or
                            If the source key mentioned is invalid (INVALID_SOURCE_KEY) or
                            If the source is inactive (SOURCE_INACTIVE) or
                            If there is an error retrieving the payload (ERROR_RETRIEVING_PAYLOAD) or
                            If there is an error splitting multiple records (ERROR_SPLITTING_RECORDS) or
                            If there is an error in parsing multiple streams (ERROR_SPLITTING_STREAMS).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        try:
            try:
                if request.META['CONTENT_TYPE'] == "text/plain":  # it's a temporary fix for a bug in swagger-ui TODO
                    request.POST = QueryDict(request.body)
            except:
                pass

            # owner = False
            response = {}
            owner, client = is_owner(request.user)
            raw_data = request.data
            logger.debug("RD:" + str(type(raw_data)))
            # all_sources_payload = json.loads(str(raw_data))
            for source_key, payload in raw_data.iteritems():
                logger.debug(source_key)
                logger.debug(payload)
                try:
                    if owner is True:
                        payload_response = data_write(request,
                                                      request_arrival_time,
                                                      source_key,
                                                      settings.RESPONSE_TYPES.DRF,
                                                      allowed_sources=client.dataglenclient.get_sensors(),
                                                      external_payload=payload)
                    # TODO: Handle actuation enabled sources for multiple sources write.
                    else:
                        payload_response = data_write(request,
                                                      request_arrival_time,
                                                      source_key, payload,
                                                      settings.RESPONSE_TYPES.DRF,
                                                      external_payload=payload)
                    logger.debug(payload_response)
                    if type(payload_response) == dict:
                        response[source_key] = payload_response
                    else:
                        response[source_key] = {'status': payload_response.code,
                                                'error': payload_response.description}
                except Exception as exc:
                    logger.debug("Error while writing for source: " + source_key + ": " + str(exc))
                    continue
            # return a response
            response_obj = JsonResponse(response, status=httplib.OK)
            return response_obj
        except Exception as exc:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            logger.debug(str(exc))
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

from helpdesk.data_uploader import unirest_data_upload
class ContactUsViewSet(viewsets.ViewSet):
    def create(self, request):
        try:
            to_email = ",".join(settings.contact_email)
            from_email = settings.from_email
            name = request.data.get('name', None)
            email = request.data.get('email', None)
            phone_number = request.data.get('phone_number', None)
            plan_name = request.data.get('plan_name', None)
            company_name = request.data.get('company_name', None)
            email_data = {}
            email_data["From"] = from_email
            email_data["To"] = to_email
            email_data["TemplateId"] = 2481281
            email_data_template = {}
            email_data_template["plan_name"] = plan_name
            email_data_template["name"] = name
            email_data_template["email"] = email
            email_data_template["phone_number"] = phone_number
            email_data_template["company_name"] = company_name
            email_data["TemplateModel"] = email_data_template
            try:
                if email_data:
                    unirest_data_upload(email_data)
                    return Response("DataGlen has been notified about your query and interest. You'll be contacted soon", status=status.HTTP_201_CREATED)
                else:
                    return Response("NO_EMAIL_SENT", status=status.HTTP_400_BAD_REQUEST)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("ERROR_IN_SENDING_EMAIL", status=status.HTTP_400_BAD_REQUEST)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required()
def docs(request):
    return render(request, 'rest/index.html')
