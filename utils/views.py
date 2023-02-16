from kutbill import settings
from logger.models import DataCountTable
import logging
import twilio
import twilio.rest
import requests
import json

logger = logging.getLogger('dataglen.views')
logger.setLevel(logging.DEBUG)


# Create your views here. - it's a list of source keys
def get_live_chart_data(identifiers):
    try:
        valid_records_second = {}
        invalid_records_second = {}

        for identifier in identifiers:
            # include the data for live charts as well
            records = DataCountTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                    count_time_period=settings.DATA_COUNT_PERIODS.MINUTE,
                                                    identifier=identifier).limit(settings.LIVE_CHART_LEN)
            for record in records:
                try:
                    # returning UTC data
                    valid_records_second[getattr(record, 'ts')] += getattr(record, 'valid_records', 0)
                    invalid_records_second[getattr(record, 'ts')] += getattr(record, 'invalid_records', 0)
                except KeyError:
                    valid_records_second[getattr(record, 'ts')] = getattr(record, 'valid_records', 0)
                    invalid_records_second[getattr(record, 'ts')] = getattr(record, 'invalid_records', 0)

        assert(len(valid_records_second.keys()) == len(invalid_records_second.keys()))

        valid_records = []
        invalid_records = []

        for key, value in sorted((valid_records_second.iteritems())):
            valid_records.append([int(key.strftime("%s")) * 1000, value])

        if len(valid_records) > settings.LIVE_CHART_LEN:
            valid_records = valid_records[-settings.LIVE_CHART_LEN:]

        for key, value in sorted((invalid_records_second.iteritems())):
            invalid_records.append([int(key.strftime("%s")) * 1000, value])

        if len(invalid_records) > settings.LIVE_CHART_LEN:
            invalid_records = invalid_records[-settings.LIVE_CHART_LEN:]

        # additional data for charts
        return [{"key": "Total Valid Records", "values": valid_records},
                {"key": "Total Invalid Records", "values": invalid_records}]
    except:
        return [{"key": "Total Valid Records", "values": []},
                {"key": "Total Invalid Records", "values": []}]


def send_twilio_message(to_number, body):
    try:
        client = twilio.rest.TwilioRestClient(
            settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        return client.messages.create(
            body=body,
            to=to_number,
            from_=settings.TWILIO_PHONE_NUMBER
        )
    except twilio.TwilioRestException as e:
        raise


def send_solutions_infini_sms(to_number, body):
    try:
        params = {}
        params['method'] = 'sms'
        params['api_key'] = settings.SMS_KEY
        params['to'] = to_number
        params['sender'] = settings.SMS_SENDER
        params['message'] = body
        params['format'] = 'json'
        params['custom'] = 1.2
        params['flash'] = 0
        url = settings.SMS_URL
        response = requests.post(url, data=params, verify=False)
        resp_dict = json.loads(response.content)
        #print str(resp_dict["status"])
        if str(resp_dict["status"]) == 'OK':
            return True
        else:
            return False
    except Exception as exception:
        #logger.debug(str(exception))
        raise