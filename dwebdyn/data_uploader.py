import requests
from dwebdyn.settings import STATUS_CODES
import logging

logger = logging.getLogger('dwebdyn.data_uploader')
logger.setLevel(logging.DEBUG)

SERVER_URL = "http://www.dataglen.com"
REGISTRATION_URL = "/api/sources/"


# upload data function
def upload_data(source_name, api_key, source_key, source_data):
    upload_url = SERVER_URL + REGISTRATION_URL + source_key.strip() + "/" + "data/"
    try:
        response = requests.post(upload_url,
                                 headers={'Authorization': 'Token ' + api_key},
                                 json=source_data)

        if response.status_code != STATUS_CODES.SUCCESSFUL_DATA_REQUEST:
            logger.debug(",".join(["ERROR", source_name, str(source_data), str(response.status_code)]))
            return response.status_code
        #logger.info(",".join(["SUCCESS", source_name, str(source_data)]))
        return STATUS_CODES.SUCCESSFUL_DATA_REQUEST

    except requests.ConnectionError as ce:
        logger.error(",".join(["CONNECTION_ERROR", source_name, str(source_data), str(ce)]))
        return STATUS_CODES.CONNECTION_FAILURE


def upload_error(source_name, api_key, source_key, error_data):
    upload_url = SERVER_URL + REGISTRATION_URL + source_key.strip() + "/" + "events/"
    try:
        response = requests.post(upload_url,
                                 headers={'Authorization': 'Token ' + api_key},
                                 json=error_data)

        if response.status_code != STATUS_CODES.SUCCESSFUL_REQUEST:
            logger.debug(",".join(["ERROR", source_name, str(error_data), str(response.status_code)]))
            return response.status_code
        logger.info(",".join(["SUCCESS", source_name, str(error_data)]))
        return STATUS_CODES.SUCCESSFUL_DATA_REQUEST

    except requests.ConnectionError as ce:
        logger.error(",".join(["CONNECTION_ERROR", source_name, str(error_data), str(ce)]))
        return STATUS_CODES.CONNECTION_FAILURE
