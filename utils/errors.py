from django.http import HttpResponse, JsonResponse
from rest_framework import status

from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from rest_framework.response import Response
import traceback

from logger.views import log_a_data_write_failure, log_an_error, log_an_independent_error
from logger.tasks import update_counters


def generate_exception_comments(function_name):
    """
    Captures exception details and generate a comments dictionary for logs.
    Call this function right after capturing the exception.

    :param function_name: Name of the function where exception was raised
    :return: A dictionary with two keys ('exception' and 'function_name')
    """
    comments = {}
    comments['exception'] = traceback.format_exc()
    comments['stack'] = repr(traceback.extract_stack())
    comments['function_name'] = function_name
    return comments


def generate_error_response(request, response_type, error,
                            error_code, use_template,
                            response_params):
    """
    Generates an error response of HttpResponse (Django) type or of Response (Django Rest Framework) type.
    It either renders an error template (for errors encountered in GUI) or creates a response with a dictionary.
    The dictionary at least contains an 'error' key with error description. Additional (key:value) pairs can be
    passed to be included in the response.

    :param request: Http request received. Either from Django/Django REST framework.
    :param response_type: Either to create a DRF response (Response) or a Django JsonResponse. (settings.RESPONSE_TYPES)
    :param error: Error object (from settings.ERROR)
    :param error_code: status_code to be set in the response.
    :param use_template: (True/False) If the error template (dataglen/message.html) should be used or plain response.
    :param response_params: A list (key:value) of additional parameters to be defined in the response
    :return: Returns a response
    """
    if use_template:
        response = render(request, 'dataglen/message.html', {'code': error.code,
                                                             'description': error.description})
        return response, response.getvalue()
    else:
        response_dict = {}
        response_dict['error'] = error.description
        for entry in response_params:
            response_dict[entry[0]] = entry[1]
        if response_type == settings.RESPONSE_TYPES.DRF:
            response = Response(response_dict, status=error_code)
            return response, str(response_dict)
        elif response_type == settings.RESPONSE_TYPES.DJANGO:
            response = JsonResponse(response_dict, status=error_code)
            return response, response.getvalue()


def log_and_return_error(user_id, request, ts, error,
                         response_type, use_template, comments,
                         response_params=None, source_key=None):
    """
    Generates a response, writes error logs into ActionLogByError, ActionLogByUser and ActionLogBySource
    (if source_key is mentioned) and returns the response.

    :param user_id: User id of the user
    :param request: Http request received. Either from Django/Django REST framework.
    :param ts: Timestamp at which the request was received
    :param error: Error instance (settings.ERRORS)
    :param response_type: Either to create a DRF response (Response) or a Django Response (HttpResponse)
    :param use_template: If to use error template while rendering a response. Or plain JSON (further categorization
    :param comments: Comments to be stored with the log
    :param response_params: A list (key:value) of additional parameters to be defined in the response
    :param source_key: source_key if the error is associated to a source.
    :return: Returns an Http Response of type (as defined in the call).
    """
    if response_params is None:
        response_params = {}

    response, text_response = generate_error_response(request, response_type, error,
                                                      error.code, use_template, response_params)
    # action log by error, user and source
    log_an_error(user_id, request, text_response, response.status_code, error.description, ts,
                 False, source_key=source_key, comments=comments)
    return response


def log_and_return_independent_error(request, ts, error, response_type,
                                     use_template, comments, response_params=None):

    """
    Generates a response, writes error logs into IndependentError and returns the response.

    :param request: Http request received. Either from Django/Django REST framework.
    :param ts: Timestamp at which the request was received
    :param error: Error instance (settings.ERRORS)
    :param response_type: Either to create a DRF response (Response) or a Django Response (HttpResponse)
    :param use_template: If to use error template while rendering a response. Or plain JSON (further categorization
    :param comments: Comments to be stored with the log
    :param response_params: A list (key:value) of additional parameters to be defined in the response
    :return: Returns an Http Response of type (as defined in the call).
    """
    if response_params is None:
        response_params = {}

    response, text_response = generate_error_response(request, response_type, error, error.code,
                                                      use_template, response_params)
    log_an_independent_error(request, text_response, response.status_code,
                             error.description, ts, comments)
    return response


def log_and_return_bad_data_write_request(request, response_type, ts, error, source):
    """
    Generates an error response, logs it into InvalidDataStorageBySource, DataWriteHistoryByUser,
    DataWriteHistoryBySource, ActionLogByError, ActionLogByUser and ActionLogBySource tables and returns a response.
    The error response may contain error details of a user defined error_message in Sensor settings.

    :param request: Http request received. Either from Django/Django REST framework.
    :param response_type: Specifying response type that needs to be generated (Django to DRF). settings.RESPONSE_TYPES
    :param ts: Timestamp at which the request was received
    :param error: Error instance (settings.ERRORS)
    :param source: An instance of the Sensor class.
    :return: Returns an Http Response of type (as defined in the call).
    """
    response = None
    if response_type == settings.RESPONSE_TYPES.DJANGO:
        if source.textMessageWithError:
            # TODO should we create a dict here as well?
            response = HttpResponse(source.textMessageWithError,
                                    status=status.HTTP_400_BAD_REQUEST)
        else:
            response = JsonResponse({'error': error.description},
                                    status=status.HTTP_400_BAD_REQUEST)
        # writes the invalid data, action logs and data write history
        log_a_data_write_failure(source.user.id, request, response.getvalue(),
                                 response.status_code, error.description,
                                 ts, source.sourceKey)

    elif response_type == settings.RESPONSE_TYPES.DRF:
        if source.textMessageWithError:
            response = Response(source.textMessageWithError,
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            response = Response({'error': error.description},
                                status=status.HTTP_400_BAD_REQUEST)
        # writes the invalid data, action logs and data write history
        log_a_data_write_failure(source.user.id, request, response.data,
                                 response.status_code, error.description,
                                 ts, source.sourceKey)

    update_counters(source.user.id, source.sourceKey, ts, False, 1)
    return response