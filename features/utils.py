from django.test import TestCase

import logging

logger = logging.getLogger('widgets.models')
logger.setLevel(logging.DEBUG)


HEADER_NAMES = {
    'expected_energy': "Expected Generation",
    'actual_energy': "Actual Generation",
    'updated': "Last Updated",
    'event_type': "Event",
    'created': "Created At",
    'solar_status': "Inverter Status",
    'solar_status_description': "Description",
    'start_time': "Opened",
    'alarm_start_time': "Alarm Raised",
    'update_time': "Last Updated",
    'alarm_update_time': "Alarm Updated",
    'alarm_code': "Error Code",
    'status': 'Current Status',
    'alarm_status': 'Alarm Status',
    'end_time': 'End Time',
    'alarm_end_time': 'Alarm Stopped',
    'closed': 'Closed At',
    'active': 'Active',
    'association_active': 'Association',
    'identifier_name': 'Device Name',
    'residual': 'Soiling Loss',
    'delta_energy': 'Generation Difference',
    'mean_energy': 'Mean Generation',
    'delta_current': 'Current Difference',
    'mean_current': 'Mean Current',
    'alarm_description': 'Error Details'

}

INCLUDE_LIST = ['identifier_name', 'created', 'solar_status', 'solar_status_description', 'alarm_code',
                'alarm_description','closed', 'residual', 'delta_energy', 'mean_energy', 'delta_current', 'mean_current']

def get_value(key, data):
    for entry in data:
        try:
            if entry[key] is not None:
                return entry[key]
        except:
            continue
        return "string type"

# Create your tests here.
def get_header_information(data, key_to_header_mappings=None):
    try:
        keys = []
        for entry in data:
            keys = set(keys).union(set(entry.keys()))
        keys = set(INCLUDE_LIST).intersection(keys)
        keys = sorted(keys, key=INCLUDE_LIST.index)
        # if len(data) == 0:
        #     return {}
        # else :
        #     keys = data[0].keys()

        # try:
        #     for entry in data:
        #         assert(keys == entry.keys())
        # except AssertionError:
        #     logger.debug("assertion error")
        #     return {}

        if key_to_header_mappings:
            mappings = key_to_header_mappings
        else:
            mappings = HEADER_NAMES

        header_data = []
        for key in keys:
            if key not in INCLUDE_LIST:
                continue
            try:
                header_data.append({"header": mappings[key], "key": key, "type": type(get_value(key, data)).__name__})
            except:
                header_data.append({"header": key, "key": key, "type": 'string'})
        # for key in keys:
        #     try:
        #         for entry in data:
        #             if entry[key] is not None:
        #                 header_data.append({"header": mappings[key], "key": key, "type": type(entry[key]).__name__})
        #                 break
        #     except KeyError:
        #         header_data.append({"header": key, "key": key, "type": 'string'})
        #     except Exception as exc:
        #         logger.debug(str(exc))
        #         return {}
    except :
        return {}

    return header_data
