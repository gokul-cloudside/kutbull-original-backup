import base64
import json
from django.conf import settings

UPLOAD_URL = "https://api.postmarkapp.com/email/withTemplate"
POSTMARKAPP_KEY = "737c3ca2-b418-460f-81fd-82ba1d9aebb4"
if settings.CASSANDRA_UPDATE:
    # TODO change KEY as previous once google server is live
    POSTMARKAPP_KEY = "737c3ca2-b418-460f-81fd-82ba1d9aebb4"
NEW_ALARM_TEMPLATE_ID = 1664546
CLOSE_ALARM_TEMPLATE_UD = 1674862
REPORT_TEMPLATE_ID = 1670601


# API ERROR CODES
class STATUS_CODES():
    SUCCESSFUL_DATA_REQUEST = 200
    SUCCESSFUL_REQUEST = 201
    BAD_REQUEST = 400
    UNAUTHENTICATED_REQUEST = 401
    DUPLICATE_REQUEST = 409
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503
    CONNECTION_FAILURE = -1

import requests, unirest

# upload data function
def upload_data(email_data, logger):
    upload_url = UPLOAD_URL
    try:
        response = requests.post(upload_url,
                                 headers={'X-Postmark-Server-Token': POSTMARKAPP_KEY,
                                          'Content-Type' : 'application/json'},
                                 json=email_data)

        if response.status_code != STATUS_CODES.SUCCESSFUL_DATA_REQUEST:
            logger.debug(",".join(["ERROR", str(email_data), str(response.status_code)]))
            return response.status_code
        #logger.info(",".join(["SUCCESS", source_name, str(source_data)]))
        return STATUS_CODES.SUCCESSFUL_DATA_REQUEST

    except requests.ConnectionError as ce:
        logger.error(",".join(["CONNECTION_ERROR", str(email_data), str(ce)]))
        return STATUS_CODES.CONNECTION_FAILURE


def callback_function(response):
    return

def unirest_data_upload(email_data):
    thread = unirest.post(UPLOAD_URL,
                          headers={'X-Postmark-Server-Token': POSTMARKAPP_KEY,
                                   'Content-Type': 'application/json'},
                          params=json.dumps(email_data), callback=callback_function)
    return 0

def send_new_alarm(ticket_id, plant_name, preheader, client_name,
                   impacted_devices_description, impacted_devices_list,
                   ticket_url,ticket_type,
                   support_email, to_with_alert, logger, template_id=None, new_alarm=True):
    try:
        from dgusers.models import AlertsCategory
        to, alert_id = to_with_alert
        if template_id is None:
            template_id = NEW_ALARM_TEMPLATE_ID
        template_data = {}
        template_data["ticket_id"] = ticket_id
        template_data["plant_name"] = plant_name
        template_data["preheader"] = preheader
        template_data["client_name"] = client_name
        template_data["impacted_devices_description"] = impacted_devices_description
        template_data["impacted_devices_list"] = impacted_devices_list
        template_data["ticket_url"] = ticket_url
        template_data["ticket_type"] = ticket_type
        template_data["support_email"] = support_email
        template_data["sender_name"] = "DataGlen Team"
        postmark_data = {}
        postmark_data['From'] = "alerts@dataglen.com"
        postmark_data['To'] = to
        postmark_data['TemplateId'] = template_id
        postmark_data['TemplateModel'] = template_data
        if new_alarm:
            AlertsCategory.update_email_time(alert_id)
        return unirest_data_upload(postmark_data)
    except Exception as exc:
        logger.debug(str(exc))
        return None

def send_close_alarm(ticket_id, plant_name, preheader, client_name,
                     impacted_devices_description, impacted_devices_list,
                     ticket_url,ticket_type,
                     support_email, to, logger):
    send_new_alarm(ticket_id, plant_name, preheader, client_name,
                   impacted_devices_description, impacted_devices_list,
                   ticket_url, ticket_type,
                   support_email, to, logger, template_id=CLOSE_ALARM_TEMPLATE_UD, new_alarm=False)

def send_alarm_close(email_data, to, logger):
    postmark_data = {}
    postmark_data['From'] = "alerts@dataglen.com"
    postmark_data['To'] = to
    postmark_data['TemplateId'] = CLOSE_ALARM_TEMPLATE_UD
    postmark_data['TemplateModel'] = email_data
    return upload_data(postmark_data, logger)


def send_email_report(template_data, file_name, file_path, to, logger, template_id=None):
    if template_id is None:
        template_id = REPORT_TEMPLATE_ID

    try:
        csv_file = open(file_path, 'rb')
        csv_file = csv_file.read()
        csv_file_encode = base64.encodestring(csv_file)
    except Exception as exc:
        logger.debug(str(exc))
        return False

    try:
        postmark_data = {}
        postmark_data['From'] = "alerts@dataglen.com"
        postmark_data['To'] = to
        postmark_data['TemplateId'] = template_id
        postmark_data['TemplateModel'] = template_data
        postmark_data['Attachments'] = [{"Name": file_name,
                                         "Content": csv_file_encode,
                                         "ContentType": "application/vnd.ms-excel"}]
        return upload_data(postmark_data, logger)
    except Exception as exc:
        logger.debug(str(exc))
        return False

CLEANMAX_DAILY_REPORT_EXCELS_AND_PDFS = 5834442
def send_email_report_cleanmax(template_data, file_paths, to, logger, template_id=None,cc=None):
    if template_id is None:
        template_id = CLEANMAX_DAILY_REPORT_EXCELS_AND_PDFS
    attachments=[]
    for file_path in file_paths:
        try:
            print file_path
            d={}
            csv_file = open(file_path, 'rb')
            csv_file = csv_file.read()
            # print csv_file
            csv_file_encode = base64.encodestring(csv_file)
            # csv_file.close()
            file_name=file_path.split('/')[-1]
            # print "FIle name is ",file_name

            d["Name"] = file_name
            d["Content"]= csv_file_encode
            if d["Name"].split('.')[-1]=='pdf':
                d["ContentType"]= "application/pdf"
            else:
                d["ContentType"]= "application/vnd.ms-excel"
            # print "printing dict ",d
            attachments.append(d)
        except Exception as exc:
            logger.debug(str(exc))
            # return "problem",False

    try:
        postmark_data = {}
        postmark_data['From'] = "alerts@dataglen.com"
        postmark_data['To'] = to
        if cc:
            postmark_data['Cc'] = cc
        postmark_data['TemplateId'] = template_id
        postmark_data['TemplateModel'] = template_data
        postmark_data['Attachments'] = attachments
        print upload_data(postmark_data, logger)
    except Exception as exc:
        logger.debug("Exception in send_email_report_cleanmax : "+str(exc))
        print False





