from dataglen.models import *
from events.models import *
import requests, json, logging

logger = logging.getLogger('helpdesk.models')
logger.setLevel(logging.DEBUG)
SMS_LEN_LIMIT = 300
ADDITIONAL_TEXT = "..(check the dashboard for more details)."
#LONG_SMS_LEN = 300
def get_plant_users_emails(plant, role_list=None):
    emails = []
    organization_users = plant.organization_users.all()
    for organization_user in organization_users:
        try:
            if role_list:
                if organization_user.user.role.role in role_list:
                    emails.append(organization_user.user.email)
            else:
                emails.append(organization_user.user.email)
        except Exception as exc:
            continue
    return emails


def get_plant_events_emails(plant, events_list=None):

    try:
        if events_list:
            preferences = UserEventAlertsPreferences.objects.filter(identifier=plant.slug,
                                                                    event__in=Events.objects.filter(event_name__in=events_list),
                                                                    alert_active=True)
        else:
            preferences = UserEventAlertsPreferences.objects.filter(identifier=plant.slug,
                                                                    alert_active=True)
        emails = []
        for pref in preferences:
            if pref.email_id not in emails:
                emails.append(pref.email_id)
        return emails
    except Exception as exc:
        return []


def prepare_descriptions(to_be_created, event_type, plant, alarms_descriptions=None):
    try:
        if alarms_descriptions is None:
            alarms_descriptions = []
        sources = Sensor.objects.filter(sourceKey__in = to_be_created).values_list('name')
        names_list = [x[0] for x in sources]
        if event_type == "GATEWAY_POWER_OFF":
            pre_header = str(len(to_be_created)) + " data logger(s) powered off"
            impacted_devices_description = str(len(to_be_created)) + " data logger device(s) have been powered OFF, no data will be collected until they are powered back ON. " \
                                                                     "These are the device(s) "
            impacted_devices_list = ",".join(names_list)
            # One or more {} have {} at the plant {}, please check their {}.
            sms_text = " ".join([pre_header, "at", str(plant.name).replace(" ", "") + ".", "List of device(s):", impacted_devices_list])
            if len(sms_text) > SMS_LEN_LIMIT:
                sms_text = sms_text[0:SMS_LEN_LIMIT-len(ADDITIONAL_TEXT)] + ADDITIONAL_TEXT
            return "Data Logger(s) Powered Off", pre_header, impacted_devices_description, impacted_devices_list, sms_text


        elif event_type == "GATEWAY_DISCONNECTED":
            pre_header = str(len(to_be_created)) + " data logger(s) stopped sending data"
            impacted_devices_description = str(len(to_be_created)) + " data logger(s) have stopped sending data, please check the internet connection at the site. " \
                                                                     "These are the device(s) "
            impacted_devices_list = ",".join(names_list)
            # One or more {} have {} at the plant {}, please check their {}.
            sms_text = " ".join([pre_header, "at", str(plant.name).replace(" ", "") + ".", "List of device(s):", impacted_devices_list])
            if len(sms_text) > SMS_LEN_LIMIT:
                sms_text = sms_text[0:SMS_LEN_LIMIT-len(ADDITIONAL_TEXT)] + ADDITIONAL_TEXT
            return "Data Logger(s) Disconnected", pre_header, impacted_devices_description, impacted_devices_list, sms_text

        elif event_type == "INVERTERS_DISCONNECTED" :
            pre_header = str(len(to_be_created)) + " inverter(s) stopped sending data"
            impacted_devices_description = str(len(to_be_created)) + " inverter(s) have stopped sending data, while the internet connection at the site is available. " \
                                                                     "These are the inverter(s) "
            impacted_devices_list = ",".join(names_list)
            # One or more {} have {} at the plant {}, please check their {}.
            sms_text = " ".join([pre_header, "at", str(plant.name).replace(" ", "") + ".", "List of inverter(s):", impacted_devices_list])
            if len(sms_text) > SMS_LEN_LIMIT:
                sms_text = sms_text[0:SMS_LEN_LIMIT-len(ADDITIONAL_TEXT)] + ADDITIONAL_TEXT
            return "Inverter(s) Disconnected", pre_header, impacted_devices_description, impacted_devices_list, sms_text

        elif event_type == "AJBS_DISCONNECTED" :
            pre_header = str(len(to_be_created)) + " AJB(s) stopped sending data"
            impacted_devices_description = str(len(to_be_created)) + " ajb(s) have stopped sending data, while the internet connection at the site is available. " \
                                                                     "These are the AJB(s) "
            impacted_devices_list = ",".join(names_list)
            # One or more {} have {} at the plant {}, please check their {}.
            sms_text = " ".join([pre_header, "at", str(plant.name).replace(" ", "") + ".", "List of AJB(s):", impacted_devices_list])
            if len(sms_text) > SMS_LEN_LIMIT:
                sms_text = sms_text[0:SMS_LEN_LIMIT-len(ADDITIONAL_TEXT)] + ADDITIONAL_TEXT
            return "AJB(s) Disconnected", pre_header, impacted_devices_description, impacted_devices_list, sms_text

        elif event_type == "INVERTERS_ALARMS" :
            pre_header = str(len(to_be_created)) + " inverter(s) raised alarms"
            impacted_devices_description = str(len(to_be_created)) + " inverters(s) have raised internal alarms. " \
                                                                     "These are the inverter(s) "
            impacted_devices_list = ",".join(alarms_descriptions) #",".join(names_list)
            # One or more {} have {} at the plant {}, please check their {}.
            sms_text = " ".join([pre_header, "at", str(plant.name).replace(" ", "") + ".", "List of inverter(s):", ",".join(alarms_descriptions)])
            if len(sms_text) > SMS_LEN_LIMIT:
                sms_text = sms_text[0:SMS_LEN_LIMIT-len(ADDITIONAL_TEXT)] + ADDITIONAL_TEXT
            return "Inverter(s) Alarms", pre_header, impacted_devices_description, impacted_devices_list, sms_text

        elif event_type == "AJB_STRING_CURRENT_ZERO_ALARM" :
            pre_header = str(len(to_be_created)) + " AJB(s) strings stopped generating (0 current)"
            impacted_devices_description = str(len(to_be_created)) + " AJB(s) have faulty strings. " \
                                                                     "These are the AJB(s) "
            impacted_devices_list = ",".join(alarms_descriptions) #",".join(names_list)
            # One or more {} have {} at the plant {}, please check their {}.
            sms_text = " ".join([pre_header, "at", str(plant.name).replace(" ", "") + ".", "List of AJB(s):", ",".join(alarms_descriptions)])
            if len(sms_text) > SMS_LEN_LIMIT:
                sms_text = sms_text[0:SMS_LEN_LIMIT-len(ADDITIONAL_TEXT)] + ADDITIONAL_TEXT
            return "AJB(s) Alarms", pre_header, impacted_devices_description, impacted_devices_list, sms_text

    except Exception as exc:
        return None, None, None, None, None

def prepare_descriptions_close(to_be_closed, event_type, plant):
    try:
        sources = Sensor.objects.filter(sourceKey__in = to_be_closed).values_list('name')
        names_list = [x[0] for x in sources]
        if event_type == "GATEWAY_POWER_OFF":
            pre_header = str(len(to_be_closed)) + " gateway(s) powered ON"
            impacted_devices_description = str(len(to_be_closed)) + " gateway device(s) have been powered ON." \
                                                                     "These are the gateway(s) "
            impacted_devices_list = ",".join(names_list)
            # One or more {} have {} at the plant {}, please check their {}.
            sms_text = " ".join([pre_header, "at", str(plant.name).replace(" ", "") + ".", "List of gateway(s):", impacted_devices_list])
            if len(sms_text) > SMS_LEN_LIMIT:
                sms_text = sms_text[0:SMS_LEN_LIMIT-len(ADDITIONAL_TEXT)] + ADDITIONAL_TEXT
            return "Gateway(s) Powered ON", pre_header, impacted_devices_description, impacted_devices_list, sms_text

        elif event_type == "GATEWAY_DISCONNECTED":
            pre_header = str(len(to_be_closed)) + " gateway(s) started sending data"
            impacted_devices_description = str(len(to_be_closed)) + " gateway device(s) have started sending data. " \
                                                                     "These are the gateway(s) "
            impacted_devices_list = ",".join(names_list)
            # One or more {} have {} at the plant {}, please check their {}.
            sms_text = " ".join([pre_header, "at", str(plant.name).replace(" ", "") + ".", "List of gateway(s):", impacted_devices_list])
            if len(sms_text) > SMS_LEN_LIMIT:
                sms_text = sms_text[0:SMS_LEN_LIMIT-len(ADDITIONAL_TEXT)] + ADDITIONAL_TEXT
            return "Gateway(s) Connected", pre_header, impacted_devices_description, impacted_devices_list, sms_text

        elif event_type == "INVERTERS_DISCONNECTED" :
            pre_header = str(len(to_be_closed)) + " inverter(s) started sending data"
            impacted_devices_description = str(len(to_be_closed)) + " inverter(s) have started sending data. " \
                                                                     "These are the inverter(s) "
            impacted_devices_list = ",".join(names_list)
            # One or more {} have {} at the plant {}, please check their {}.
            sms_text = " ".join([pre_header, "at", str(plant.name).replace(" ", "") + ".", "List of inverter(s):", impacted_devices_list])
            if len(sms_text) > SMS_LEN_LIMIT:
                sms_text = sms_text[0:SMS_LEN_LIMIT-len(ADDITIONAL_TEXT)] + ADDITIONAL_TEXT
            return "Inverter(s) Connected", pre_header, impacted_devices_description, impacted_devices_list, sms_text

        elif event_type == "AJBS_DISCONNECTED" :
            pre_header = str(len(to_be_closed)) + " AJB(s) started sending data"
            impacted_devices_description = str(len(to_be_closed)) + " ajb(s) have started sending data. " \
                                                                     "These are the AJB(s) "
            impacted_devices_list = ",".join(names_list)
            # One or more {} have {} at the plant {}, please check their {}.
            sms_text = " ".join([pre_header, "at", str(plant.name).replace(" ", "") + ".", "List of AJB(s):", impacted_devices_list])
            if len(sms_text) > SMS_LEN_LIMIT:
                sms_text = sms_text[0:SMS_LEN_LIMIT-len(ADDITIONAL_TEXT)] + ADDITIONAL_TEXT
            return "AJB(s) Connected", pre_header, impacted_devices_description, impacted_devices_list, sms_text

        elif event_type == "INVERTERS_ALARMS" :
            pre_header = str(len(to_be_closed)) + " inverter(s) stopped sending alarms"
            impacted_devices_description = str(len(to_be_closed)) + " inverters(s) stopped sending internal alarms. " \
                                                                     "These are the inverter(s) "
            impacted_devices_list = ",".join(names_list)
            # One or more {} have {} at the plant {}, please check their {}.
            sms_text = " ".join([pre_header, "at", str(plant.name).replace(" ", "") + ".", "List of inverter(s):", impacted_devices_list])
            if len(sms_text) > SMS_LEN_LIMIT:
                sms_text = sms_text[0:SMS_LEN_LIMIT-len(ADDITIONAL_TEXT)] + ADDITIONAL_TEXT
            return "Inverter(s) Alarms", pre_header, impacted_devices_description, impacted_devices_list, sms_text

        elif event_type == "AJB_STRING_CURRENT_ZERO_ALARM" :
            pre_header = str(len(to_be_closed)) + " AJB(s) strings got fixed"
            impacted_devices_description = str(len(to_be_closed)) + " AJB(s) strings have been fixed. " \
                                                                     "These are the AJB(s) "
            impacted_devices_list = ",".join(names_list)
            # One or more {} have {} at the plant {}, please check their {}.
            sms_text = " ".join([pre_header, "at", str(plant.name).replace(" ", "") + ".", "List of AJB(s):", impacted_devices_list])
            if len(sms_text) > SMS_LEN_LIMIT:
                sms_text = sms_text[0:SMS_LEN_LIMIT-len(ADDITIONAL_TEXT)] + ADDITIONAL_TEXT
            return "AJB(s) Alarms", pre_header, impacted_devices_description, impacted_devices_list, sms_text

    except Exception as exc:
        return None, None, None, None, None


def send_infini_sms(to_number_with_alert, body, new_alarm=True):
    from dgusers.models import AlertsCategory
    to_number, alert_id = to_number_with_alert
    logger.debug("#".join([str(to_number), str(body)]))
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
            if new_alarm:
                AlertsCategory.update_sms_time(alert_id)
            return True
        else:
            logger.debug("False status for sending SMS message: " + str(resp_dict["status"]))
            return False
    except Exception as exception:
        logger.debug(str(exception))
        raise

def send_infini_sms_internal(to_number, body, new_alarm=True):
    logger.debug("#".join([str(to_number), str(body)]))
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
    except Exception as exception:
        logger.debug(str(exception))

    return


# def check_inconsistencies():
#     from helpdesk.models import Ticket
#     tickets = Ticket.objects.filter(status=1)
#     for t in tickets:
#         associations = t.associations.filter(active=True).values_list('identifier', flat=True)
#         if len(associations) != len(set(associations)):
#             print t, t.created
