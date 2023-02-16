from dataglen.models import Sensor, Field
from config.models import ConfigField
from .serializers import ConfigFieldSerializer
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render
from django.http import QueryDict
import json, datetime

from logger.views import log_a_success, log_an_error
from utils.errors import log_and_return_error
from django.utils import timezone
from django.conf import settings
from utils.errors import generate_exception_comments
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from rest_framework import authentication, permissions
from django.contrib.auth.decorators import login_required

from rest_framework import viewsets
import sys, logging, dateutil
from dataglen.models import ValidDataStorageByStream
from dataglen.data_views import data_write
from logger.views import log_a_success
from utils.errors import log_and_return_error, log_and_return_independent_error, \
    log_and_return_bad_data_write_request, \
    generate_exception_comments
from cassandra.cqlengine.query import BatchQuery
from dateutil import parser


logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)


class ConfigStreamsViewSet(viewsets.ViewSet):
    """
    Manage your config streams
    """
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'config_stream_name'

    def list(self, request, source_key=None):
        """
            Get a list of config streams for a source.
            ---
            response_serializer: ConfigFieldSerializer
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
                source = Sensor.objects.get(sourceKey=source_key, user=request.user)
            except ObjectDoesNotExist:
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(request.user.id, request, request_arrival_time,
                                            settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                            False, comments)
            config_streams = ConfigField.objects.filter(source=source)
            serializer = ConfigFieldSerializer(config_streams, many=True)
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


    def retrieve(self, request, config_stream_name=None, source_key=None):
        """
            Get a config stream with the mentioned key.
            ---
            response_serializer: ConfigFieldSerializer
            responseMessages:
                - code : 200
                  message : Success
                - code : 400
                  message : If the source key mentioned is invalid (INVALID_SOURCE_KEY) or
                            If the specified config stream does not exist (INVALID_CONFIG_DATA_STREAM).
                - code : 401
                  message : Not authenticated
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
            config_stream = ConfigField.objects.get(source=source,
                                                    name=config_stream_name)
            serializer = ConfigFieldSerializer(config_stream,
                                          many=False)
            response = Response(serializer.data)
            log_a_success(request.user.id, request, response.status_code,
                          request_arrival_time, source_key=source_key)
            return response
        except ObjectDoesNotExist:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_CONFIG_DATA_STREAM, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        # check for broad errors (ones we don't know yet)
        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

    def create(self, request, source_key=None):
        """
            Create a new config data stream.
            ---
            parameters:
                - name: body
                  type: WriteConfigFieldSerializer
                  description: Details of the new stream to be created.
                  required: True
                  paramType: body
            response_serializer: ConfigFieldSerializer
            responseMessages:
                - code : 201
                  message : Success. Accompanied with details of the new stream.
                - code : 400
                  message : If the source key mentioned is invalid (INVALID_SOURCE_KEY) or
                            If any of the essential parameters are missing/invalid (BAD_REQUEST) 
                - code : 409
                  message : If a stream with the mentioned name OR position already exists (DUPLICATE_CONFIG_STREAM).
                - code : 401
                  message : Not authenticated
        """
        request_arrival_time = timezone.now()
        # get the source first
        try:
            source = Sensor.objects.get(sourceKey=source_key)
        except ObjectDoesNotExist as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_SOURCE_KEY, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        # save the new stream
        try:
            serializer = ConfigFieldSerializer(data=request.data)
            if serializer.is_valid():
                if source.dataFormat == "CSV":
                    try:
                        assert(serializer['streamPositionInCSV'].value)
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
                field = ConfigField.objects.get(source=source,
                                                name=request.data["name"])
            except ObjectDoesNotExist:
                try:
                    field = ConfigField.objects.get(source=source,
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
                                        settings.ERRORS.DUPLICATE_CONFIG_STREAM, settings.RESPONSE_TYPES.DRF,
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
        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)


    def destroy(self, request, config_stream_name=None, source_key=None):
        """
            Delete a config data stream.
            ---
            responseMessages:
                - code : 204
                  message : Success. The source has been deleted.
                - code : 400
                  message : If the source key mentioned is invalid (INVALID_SOURCE_KEY) or
                            If the specified config stream does not exist (INVALID_CONFIG_DATA_STREAM).
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
            config_stream = ConfigField.objects.get(source=source,
                                                    name=config_stream_name)
            config_stream.delete()
            response = Response(status=status.HTTP_204_NO_CONTENT)
            log_a_success(request.user.id, request, response.status_code,
                          request_arrival_time, source_key=source_key)
            return response
        except ObjectDoesNotExist as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INVALID_CONFIG_DATA_STREAM, settings.RESPONSE_TYPES.DRF,
                                        False, comments)
        # check for broad errors (ones we don't expect)
        except Exception as exception:
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(request.user.id, request, request_arrival_time,
                                        settings.ERRORS.INTERNAL_SERVER_ERROR, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

