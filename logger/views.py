
from logger.tasks import write_invalid_data_storage_by_source, \
    write_action_log_by_error_user_source, \
    write_action_log_by_user_source, \
    write_source_data_write_history, \
    write_independent_error
from logger.tasks import write_logging_errors
import sys, logging


logger = logging.getLogger('logger.tasks')
logger.setLevel(logging.DEBUG)


def serialize_request(request):
    try:
        if request.method == 'POST':
            if request.POST:
                return str(dict(request.POST))
            else:
                return str(request.body)
        elif request.method == 'PATCH' or request.method == 'DELETE':
            return str(dict(request.data))
        else:
            return str(dict(request.GET))
    except Exception  as exc:
        logger.debug(str(exc))
        #write_logging_errors(sys._getframe().f_code.co_name)
        return ''


def add_request_response_in_comments(request, response, comments):
    try:
        comments['request'] = serialize_request(request)
        comments['response'] = response
        return comments
    except:
        write_logging_errors(sys._getframe().f_code.co_name)
        return comments


def log_a_success(user_id, request, response_code, ts, source_key=None, comments=None):
    return

    """
    Logs a successful action on the website. Writes into ActionLogByUser and
    ActionLogBySource (if there is a source_key mentioned). We do not log response
    text here.

    :param user_id: User id of the user
    :param request: Request object
    :param response_code: Response code
    :param ts: Timestamp of the request arrival
    :param source_key: Source key of the source (optional)
    :param comments: Any additional comments as a dictionary (<text>:<text>) (optional)
    :return: None
    """
    if comments is None:
        comments = {}
    write_action_log_by_user_source.delay(user_id, True, ts.date(),
                                          ts, request.get_full_path(),
                                          response_code, request.META['REMOTE_ADDR'],
                                          comments, source_key)


def log_an_error(user_id, request, response_payload, response_code,
                 error_text, ts, success, source_key=None, comments=None):
    return

    """
    Logs an error on the website for a known User
    (correspond to actions where User has to be logged in).
    Writes into ActionLogByError, ActionLogByUser
    and ActionLogBySource (if source_key is mentioned).

    :param user_id: User id of the user
    :param request: Request object
    :param response_payload: Response (payload) as a text
    :param response_code: Response code
    :param error_text: Error text
    :param ts: Timestamp of the request arrival
    :param success: If the called URL was a success or not (mostly False)
    :param source_key: Source key (optional)
    :param comments: Any additional comments as a dictionary (<text>:<text>) (optional)
    :return: None
    """
    if comments is None:
        comments = {}
    add_request_response_in_comments(request, response_payload, comments)
    write_action_log_by_error_user_source.delay(error_text, ts.date(),
                                                ts, user_id, request.get_full_path(),
                                                request.META['REMOTE_ADDR'],
                                                comments, success,
                                                response_code, source_key)


def log_an_independent_error(request, response_payload, response_code,
                             error_text, ts, comments=None):
    return

    """
    Logs an independent error where there's no user associated.
    Writes into IndependentError

    :param request: Request object
    :param response_payload: Response (payload) as a text
    :param response_code: Response code as a text
    :param error_text: Error text
    :param ts: Timestamp of the request arrival
    :param comments: Additional comments
    :return: None
    """
    if comments is None:
        comments = {}
    add_request_response_in_comments(request, response_payload, comments)
    write_independent_error.delay(error_text, ts, request.get_full_path(), response_code,
                                  request.META['REMOTE_ADDR'], comments)


def log_a_data_write_failure(user_id, request, response_payload, response_code,
                             error_text, ts, source_key, comments=None):
    """
    Logs a data write failure.
    Writes into InvalidDataStorageBySource,
    DataWriteHistoryByUser, DataWriteHistoryBySource,
    ActionLogByError, ActionLogByUser and ActionLogBySource tables.

    :param user_id: User id of the user
    :param request: Request object
    :param response_payload: Response (payload) as a text
    :param response_code: Response code
    :param error_text: Error object (from settings.ERRORS)
    :param ts: Timestamp of the request arrival
    :param source_key: Source key of the source (must be present)
    :param comments: Any additional comments as a dictionary (<text>:<text>) (optional)
    :return: None
    """
    if comments is None:
        comments = {}
    comments['response'] = response_payload
    # TODO all of these should be a BatchQuery()
    write_invalid_data_storage_by_source.delay(source_key, ts,
                                               serialize_request(request),
                                               error_text, comments)
    write_source_data_write_history.delay(user_id, source_key,
                                          False, ts.date(), ts)
    write_action_log_by_error_user_source.delay(error_text, ts.date(), ts,
                                                user_id, request.get_full_path(),
                                                request.META['REMOTE_ADDR'],
                                                comments, False,
                                                response_code,
                                                source_key=source_key)

