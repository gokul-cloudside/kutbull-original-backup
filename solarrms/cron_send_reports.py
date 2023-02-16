import pytz
import datetime
import calendar
import smtplib, email, email.encoders, email.mime.text, email.mime.base
import logging
import re
import pandas as pd
import os

from dashboards.models import DataglenClient
from dgusers.models import UserRole
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from dateutil import parser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from features.models import RoleAccess
from helpdesk.dg_functions import get_plant_tickets_date
from solarrms.solar_reports import get_monthly_report_to_attach_in_email, get_monthly_report_to_attach_in_email_for_atria,\
    excel_creation_for_user_customised_daily_performance_report, get_monthly_report_values
from solarrms.models import SolarPlant, PlantCompleteValues, PlantSummaryDetails
from solarrms.solarutils import manipulateColumnNames, excelConversion
from solarrms.new_solar_reports import get_monthly_plant_report
from solarrms.api_views import fix_generation_units, fix_capacity_units, feature_to_df_mappings
from events.models import UserEventAlertsPreferences, Events
from postmarker.core import PostmarkClient
from helpdesk.data_uploader import POSTMARKAPP_KEY
from utils.views import send_solutions_infini_sms


logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

def update_tz(dt, tz_name):
    try:
        tz = pytz.timezone(tz_name)
        if dt.tzinfo:
            return dt.astimezone(tz)
        else:
            return tz.localize(dt)
    except:
        return dt



def send_detailed_report_with_attachment(plant,recepient_email):
    try:
        value = None
        plant_meta_source = plant.metadata.plantmetasource
        values = PlantCompleteValues.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                    count_time_period=86400,
                                                    identifier=plant_meta_source.sourceKey).limit(1)
        if len(values)>0:
            value = values[0]

        # get today's ticket details
        try:
            date = timezone.now()
            tz = pytz.timezone(plant.metadata.plantmetasource.dataTimezone)
            if date.tzinfo is None:
                date = tz.localize(date)
            date = date.replace(hour=0, minute=0,second=0, microsecond=0)
        except Exception as exception:
            print("Error in getting todays date : " + str(exception))

        t_stats = get_plant_tickets_date(plant, date, date+datetime.timedelta(hours=24))
        if t_stats != -1:
            unacknowledged_tickets = len(t_stats['open_unassigned_tickets'])
            open_tickets = len(t_stats['open_assigned_tickets'])
            closed_tickets = len(t_stats['tickets_closed_resolved'])

        else:
            unacknowledged_tickets = 0
            open_tickets = 0
            closed_tickets = 0

        dataglen_logo = "<img src= " + "http://www.comsnets.org/archive/2016/assets/images/partners/dataglen.jpg"
        group_logo = plant.dataglengroup.groupLogo if plant.dataglengroup.groupLogo else plant.groupClient.clientLogo
        client_logo = "<img src= " + str(group_logo)
        dataglen_logo_html = dataglen_logo + " style='max-width: 100%;width: 135px;'>"
        client_logo_html = client_logo + " style='max-width: 100%;width: 135px;' align='right'>"
        email_body = "<!doctype html><html> <head> <meta name='viewport' content='width=device-width' /> <meta http-equiv='Content-Type' content='text/html; charset=UTF-8' /> <title>DataGlen Generation Report</title> <style> /* ------------------------------------- GLOBAL RESETS ------------------------------------- */ img { border: none; -ms-interpolation-mode: bicubic; max-width: 100%; } body { background-color: #f6f6f6; font-family: sans-serif; -webkit-font-smoothing: antialiased; font-size: 14px; line-height: 1.4; margin: 0; padding: 0; -ms-text-size-adjust: 100%; -webkit-text-size-adjust: 100%; } table { border-collapse: separate; mso-table-lspace: 0pt; mso-table-rspace: 0pt; width: 100%; } table td { font-family: sans-serif; font-size: 14px; vertical-align: top; } /* ------------------------------------- BODY & CONTAINER ------------------------------------- */ .body { background-color: #f6f6f6; width: 100%; } /* Set a max-width, and make it display as block so it will automatically stretch to that width, but will also shrink down on a phone or something */ .container { display: block; Margin: 0 auto !important; /* makes it centered */ max-width: 580px; padding: 10px; width: 580px; } /* This should also be a block element, so that it will fill 100% of the .container */ .content { box-sizing: border-box; display: block; Margin: 0 auto; max-width: 580px; padding: 10px; } /* ------------------------------------- HEADER, FOOTER, MAIN ------------------------------------- */ .main { background: #fff; border-radius: 3px; width: 100%; } .wrapper { box-sizing: border-box; padding: 20px; } .footer { clear: both; padding-top: 10px; text-align: center; width: 100%; } .footer td, .footer p, .footer span, .footer a { color: #999999; font-size: 12px; text-align: center; } /* ------------------------------------- TYPOGRAPHY ------------------------------------- */ h1, h2, h3, h4 { color: #000000; font-family: sans-serif; font-weight: 400; line-height: 1.4; margin: 0; Margin-bottom: 30px; } h1 { font-size: 35px; font-weight: 300; text-align: center; text-transform: capitalize; } p, ul, ol { font-family: sans-serif; font-size: 14px; font-weight: normal; margin: 0; Margin-bottom: 15px; } p li, ul li, ol li { list-style-position: inside; margin-left: 5px; } a { color: #3498db; text-decoration: underline; } /* ------------------------------------- BUTTONS ------------------------------------- */ .btn { box-sizing: border-box; width: 100%; } .btn > tbody > tr > td { padding-bottom: 15px; } .btn table { width: auto; } .btn table td { background-color: #ffffff; border-radius: 5px; text-align: center; } .btn a { background-color: #ffffff; border: solid 1px #3498db; border-radius: 5px; box-sizing: border-box; color: #3498db; cursor: pointer; display: inline-block; font-size: 14px; font-weight: bold; margin: 0; padding: 12px 25px; text-decoration: none; text-transform: capitalize; } .btn-primary table td { background-color: #3498db; } .btn-primary a { background-color: #3498db; border-color: #3498db; color: #ffffff; } /* ------------------------------------- OTHER STYLES THAT MIGHT BE USEFUL ------------------------------------- */ .last { margin-bottom: 0; } .first { margin-top: 0; } .align-center { text-align: center; } .align-right { text-align: right; } .align-left { text-align: left; } .clear { clear: both; } .mt0 { margin-top: 0; } .mb0 { margin-bottom: 0; } .preheader { color: transparent; display: none; height: 0; max-height: 0; max-width: 0; opacity: 0; overflow: hidden; mso-hide: all; visibility: hidden; width: 0; } .powered-by a { text-decoration: none; } hr { border: 0; border-bottom: 1px solid #f6f6f6; Margin: 20px 0; } /* ------------------------------------- RESPONSIVE AND MOBILE FRIENDLY STYLES ------------------------------------- */ @media only screen and (max-width: 620px) { table[class=body] h1 { font-size: 28px !important; margin-bottom: 10px !important; } table[class=body] p, table[class=body] ul, table[class=body] ol, table[class=body] td, table[class=body] span, table[class=body] a { font-size: 16px !important; } table[class=body] .wrapper, table[class=body] .article { padding: 10px !important; } table[class=body] .content { padding: 0 !important; } table[class=body] .container { padding: 0 !important; width: 100% !important; } table[class=body] .main { border-left-width: 0 !important; border-radius: 0 !important; border-right-width: 0 !important; } table[class=body] .btn table { width: 100% !important; } table[class=body] .btn a { width: 100% !important; } table[class=body] .img-responsive { height: auto !important; max-width: 100% !important; width: auto !important; }} /* ------------------------------------- PRESERVE THESE STYLES IN THE HEAD ------------------------------------- */ @media all { .ExternalClass { width: 100%; } .ExternalClass, .ExternalClass p, .ExternalClass span, .ExternalClass font, .ExternalClass td, .ExternalClass div { line-height: 100%; } .apple-link a { color: inherit !important; font-family: inherit !important; font-size: inherit !important; font-weight: inherit !important; line-height: inherit !important; text-decoration: none !important; } .btn-primary table td:hover { background-color: #34495e !important; } .btn-primary a:hover { background-color: #34495e !important; border-color: #34495e !important; } } </style> </head> <body class=''> <table border='0' cellpadding='0' cellspacing='0' class='body'> <tr> <td>&nbsp;</td> <td class='container'> <div class='content'> <!-- START CENTERED WHITE CONTAINER --> <span class='preheader'>Generation report for the current month.</span> <table class='main'> <tr> " +  client_logo_html + " <!-- put image here --> </tr> <!-- START MAIN CONTENT AREA --> <tr> <td class='wrapper'> <table border='0' cellpadding='0' cellspacing='0'> <tr> <td> <p>Hi there! </p> <p>We have attached generation performance report for your plant " + str(plant.name) + " " + str(plant.location) + " with this email. </p> <p>Please feel free to reach out to us if you have any queries.</p> <p>Thank you!</p> </td> </tr> </table> </td> </tr> <!-- END MAIN CONTENT AREA --> </table> <!-- START FOOTER --> <div class='footer'> <table border='0' cellpadding='0' cellspacing='0'> <tr> <td class='content-block'> <span class='apple-link'>DataGlen Technologies Private Limited, 2017</span> </td> </tr> </table> </div> <!-- END FOOTER --> <!-- END CENTERED WHITE CONTAINER --></div> </td> <td>&nbsp;</td> </tr> </table> </body></html>"

        report_account_email = 'alerts@dataglen.com'
        from_email = 'reports@dataglen.com'
        recipient = recepient_email
        subject = ' [DATAGLEN] Generation Report: ' + str(date.date())

        email_server_host = 'smtp.gmail.com'
        port = 587
        email_username = report_account_email
        email_password = '8HUrL*JQ'

        msg = MIMEMultipart('html')
        msg['From'] = from_email
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(email_body, 'html'))

        current_time = timezone.now()
        starttime = current_time.replace(day=1)
        starttime = update_tz(starttime, plant.metadata.plantmetasource.dataTimezone)
        try:
            file_name = "_".join([str(plant.slug), str(calendar.month_name[starttime.month]), str(starttime.year), 'monthly_report']).replace(" ", "_") +  ".xls"
        except:
            file_name = "_".join([str(plant.slug),'monthly_report']).replace(" ", "_") +  ".xls"

        path = '/var/tmp/monthly_report/'
        fp = open(path+file_name , 'rb')
        file1=email.mime.base.MIMEBase('application','vnd.ms-excel')
        file1.set_payload(fp.read())
        fp.close()
        email.encoders.encode_base64(file1)
        file1.add_header('Content-Disposition','attachment;filename=' + file_name)

        msg.attach(file1)

        server = smtplib.SMTP(email_server_host, port)
        server.ehlo()
        server.starttls()
        server.login(email_username, email_password)
        server.sendmail(from_email, recipient, msg.as_string())
        server.close()

    except Exception as exception:
        print("Error in sending daily report: " + str(exception))

def send_sms_report(plant, phone):
    try:
        try:
            current_time = timezone.now()
            current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exc:
            logger.debug(str(exc))
            current_time = timezone.now()

        date = current_time.replace(hour=0,minute=0,second=0,microsecond=0)
        plant_summary = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                           count_time_period=86400,
                                                           identifier=str(plant.slug),
                                                           ts=date)
        if len(plant_summary)>0:
            performance_ratio_value = round(float(plant_summary[0].performance_ratio),2)
            today_energy_value = str(plant_summary[0].generation)+' Units'
        else:
            performance_ratio_value = 0.0
            today_energy_value = '0.0 Units'
        sms_message = 'Hi,\nDaily Performance Report of your plant at '+ str(plant.location)+':\nEnergy Generation : '+ str(today_energy_value) +' ,\nPerformance Ratio : ' + str(performance_ratio_value) + ' ,\nThank you'
        send_solutions_infini_sms(phone, sms_message)
    except Exception as exception:
        print str(exception)

def send_daily_performance_reports():
    try:
        event = Events.objects.get(event_name="DAILY_REPORT")
        plants = SolarPlant.objects.all()
        for plant in plants:
            try:
                get_monthly_report_to_attach_in_email(plant)
                user_alerts = UserEventAlertsPreferences.objects.filter(event=event, identifier=str(plant.slug))
                for alert in user_alerts:
                    # send email
                    if alert.email_id:
                        #send_detailed_report_with_attachment(plant, alert.email_id)
                        send_daily_performance_report_post_mark_app(plant, plant.groupClient,alert.email_id)
                    # send sms
                    if alert.phone_no:
                        send_sms_report(plant, alert.phone_no)
            except Exception as exception:
                print("Error in sending daily performance report : " + str(exception))
    except Exception as exception:
        print (str(exception))


def send_detailed_report_with_attachment_for_renew(plant,recepient_email):
    try:
        value = None
        plant_meta_source = plant.metadata.plantmetasource
        values = PlantCompleteValues.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                    count_time_period=86400,
                                                    identifier=plant_meta_source.sourceKey).limit(1)
        if len(values)>0:
            value = values[0]

        # get today's ticket details
        try:
            date = timezone.now()
            tz = pytz.timezone(plant.metadata.plantmetasource.dataTimezone)
            if date.tzinfo is None:
                date = tz.localize(date)
            date = date.replace(hour=0, minute=0,second=0, microsecond=0)
        except Exception as exception:
            print("Error in getting todays date : " + str(exception))

        t_stats = get_plant_tickets_date(plant, date, date+datetime.timedelta(hours=24))
        if t_stats != -1:
            unacknowledged_tickets = len(t_stats['open_unassigned_tickets'])
            open_tickets = len(t_stats['open_assigned_tickets'])
            closed_tickets = len(t_stats['tickets_closed_resolved'])

        else:
            unacknowledged_tickets = 0
            open_tickets = 0
            closed_tickets = 0

        dataglen_logo = "<img src= " + "http://www.comsnets.org/archive/2016/assets/images/partners/dataglen.jpg"
        group_logo = plant.dataglengroup.groupLogo if plant.dataglengroup.groupLogo else plant.groupClient.clientLogo
        client_logo = "<img src= " + str(group_logo)
        dataglen_logo_html = dataglen_logo + " style='max-width: 100%;width: 135px;'>"
        client_logo_html = client_logo + " style='max-width: 100%;width: 135px;' align='right'>"
        email_body = "<!doctype html><html> <head> <meta name='viewport' content='width=device-width' /> <meta http-equiv='Content-Type' content='text/html; charset=UTF-8' /> <title>DataGlen Generation Report</title> <style> /* ------------------------------------- GLOBAL RESETS ------------------------------------- */ img { border: none; -ms-interpolation-mode: bicubic; max-width: 100%; } body { background-color: #f6f6f6; font-family: sans-serif; -webkit-font-smoothing: antialiased; font-size: 14px; line-height: 1.4; margin: 0; padding: 0; -ms-text-size-adjust: 100%; -webkit-text-size-adjust: 100%; } table { border-collapse: separate; mso-table-lspace: 0pt; mso-table-rspace: 0pt; width: 100%; } table td { font-family: sans-serif; font-size: 14px; vertical-align: top; } /* ------------------------------------- BODY & CONTAINER ------------------------------------- */ .body { background-color: #f6f6f6; width: 100%; } /* Set a max-width, and make it display as block so it will automatically stretch to that width, but will also shrink down on a phone or something */ .container { display: block; Margin: 0 auto !important; /* makes it centered */ max-width: 580px; padding: 10px; width: 580px; } /* This should also be a block element, so that it will fill 100% of the .container */ .content { box-sizing: border-box; display: block; Margin: 0 auto; max-width: 580px; padding: 10px; } /* ------------------------------------- HEADER, FOOTER, MAIN ------------------------------------- */ .main { background: #fff; border-radius: 3px; width: 100%; } .wrapper { box-sizing: border-box; padding: 20px; } .footer { clear: both; padding-top: 10px; text-align: center; width: 100%; } .footer td, .footer p, .footer span, .footer a { color: #999999; font-size: 12px; text-align: center; } /* ------------------------------------- TYPOGRAPHY ------------------------------------- */ h1, h2, h3, h4 { color: #000000; font-family: sans-serif; font-weight: 400; line-height: 1.4; margin: 0; Margin-bottom: 30px; } h1 { font-size: 35px; font-weight: 300; text-align: center; text-transform: capitalize; } p, ul, ol { font-family: sans-serif; font-size: 14px; font-weight: normal; margin: 0; Margin-bottom: 15px; } p li, ul li, ol li { list-style-position: inside; margin-left: 5px; } a { color: #3498db; text-decoration: underline; } /* ------------------------------------- BUTTONS ------------------------------------- */ .btn { box-sizing: border-box; width: 100%; } .btn > tbody > tr > td { padding-bottom: 15px; } .btn table { width: auto; } .btn table td { background-color: #ffffff; border-radius: 5px; text-align: center; } .btn a { background-color: #ffffff; border: solid 1px #3498db; border-radius: 5px; box-sizing: border-box; color: #3498db; cursor: pointer; display: inline-block; font-size: 14px; font-weight: bold; margin: 0; padding: 12px 25px; text-decoration: none; text-transform: capitalize; } .btn-primary table td { background-color: #3498db; } .btn-primary a { background-color: #3498db; border-color: #3498db; color: #ffffff; } /* ------------------------------------- OTHER STYLES THAT MIGHT BE USEFUL ------------------------------------- */ .last { margin-bottom: 0; } .first { margin-top: 0; } .align-center { text-align: center; } .align-right { text-align: right; } .align-left { text-align: left; } .clear { clear: both; } .mt0 { margin-top: 0; } .mb0 { margin-bottom: 0; } .preheader { color: transparent; display: none; height: 0; max-height: 0; max-width: 0; opacity: 0; overflow: hidden; mso-hide: all; visibility: hidden; width: 0; } .powered-by a { text-decoration: none; } hr { border: 0; border-bottom: 1px solid #f6f6f6; Margin: 20px 0; } /* ------------------------------------- RESPONSIVE AND MOBILE FRIENDLY STYLES ------------------------------------- */ @media only screen and (max-width: 620px) { table[class=body] h1 { font-size: 28px !important; margin-bottom: 10px !important; } table[class=body] p, table[class=body] ul, table[class=body] ol, table[class=body] td, table[class=body] span, table[class=body] a { font-size: 16px !important; } table[class=body] .wrapper, table[class=body] .article { padding: 10px !important; } table[class=body] .content { padding: 0 !important; } table[class=body] .container { padding: 0 !important; width: 100% !important; } table[class=body] .main { border-left-width: 0 !important; border-radius: 0 !important; border-right-width: 0 !important; } table[class=body] .btn table { width: 100% !important; } table[class=body] .btn a { width: 100% !important; } table[class=body] .img-responsive { height: auto !important; max-width: 100% !important; width: auto !important; }} /* ------------------------------------- PRESERVE THESE STYLES IN THE HEAD ------------------------------------- */ @media all { .ExternalClass { width: 100%; } .ExternalClass, .ExternalClass p, .ExternalClass span, .ExternalClass font, .ExternalClass td, .ExternalClass div { line-height: 100%; } .apple-link a { color: inherit !important; font-family: inherit !important; font-size: inherit !important; font-weight: inherit !important; line-height: inherit !important; text-decoration: none !important; } .btn-primary table td:hover { background-color: #34495e !important; } .btn-primary a:hover { background-color: #34495e !important; border-color: #34495e !important; } } </style> </head> <body class=''> <table border='0' cellpadding='0' cellspacing='0' class='body'> <tr> <td>&nbsp;</td> <td class='container'> <div class='content'> <!-- START CENTERED WHITE CONTAINER --> <span class='preheader'>Generation report for the current month.</span> <table class='main'> <tr> " +  client_logo_html + " <!-- put image here --> </tr> <!-- START MAIN CONTENT AREA --> <tr> <td class='wrapper'> <table border='0' cellpadding='0' cellspacing='0'> <tr> <td> <p>Hi there! </p> <p>We have attached generation performance report for your plant " + str(plant.name) + " " + str(plant.location) + " with this email. </p> <p>Please feel free to reach out to us if you have any queries.</p> <p>Thank you!</p> </td> </tr> </table> </td> </tr> <!-- END MAIN CONTENT AREA --> </table> <!-- START FOOTER --> <div class='footer'> <table border='0' cellpadding='0' cellspacing='0'> <tr> <td class='content-block'> <span class='apple-link'>DataGlen Technologies Private Limited, 2017</span> </td> </tr> </table> </div> <!-- END FOOTER --> <!-- END CENTERED WHITE CONTAINER --></div> </td> <td>&nbsp;</td> </tr> </table> </body></html>"

        report_account_email = 'alerts@dataglen.com'
        from_email = 'reports@dataglen.com'
        recipient = recepient_email
        subject = ' DGR - ' + str(plant.name) + ' : '+ str(date.date())

        email_server_host = 'smtp.gmail.com'
        port = 587
        email_username = report_account_email
        email_password = '8HUrL*JQ'

        msg = MIMEMultipart('alternative')
        msg['From'] = from_email
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(email_body, 'html'))

        current_time = timezone.now()
        starttime = (current_time-datetime.timedelta(days=1)).replace(day=1)
        starttime = update_tz(starttime, plant.metadata.plantmetasource.dataTimezone)
        try:
            file_name = "_".join([str(plant.slug), str(calendar.month_name[starttime.month]), str(starttime.year), 'monthly_report']).replace(" ", "_") +  ".xls"
        except:
            file_name = "_".join([str(plant.slug),'monthly_report']).replace(" ", "_") +  ".xls"

        path = '/var/tmp/monthly_report/new/'
        fp = open(path+file_name , 'rb')
        file1=email.mime.base.MIMEBase('application','vnd.ms-excel')
        file1.set_payload(fp.read())
        fp.close()
        email.encoders.encode_base64(file1)
        file1.add_header('Content-Disposition','attachment;filename=' + file_name)

        msg.attach(file1)

        server = smtplib.SMTP(email_server_host, port)
        server.ehlo()
        server.starttls()
        server.login(email_username, email_password)
        server.sendmail(from_email, recipient, msg.as_string())
        server.close()

    except Exception as exception:
        print("Error in sending daily report: " + str(exception))

def send_daily_performance_reports_for_renew():
    try:
        print(timezone.now())
        event = Events.objects.get(event_name="DAILY_REPORT")
        client = DataglenClient.objects.filter(slug='renew-power')
        plants = SolarPlant.objects.filter(groupClient=client)
        for plant in plants:
            try:
                print("Sending report for : " + str(plant.slug))
                get_monthly_plant_report(plant)
                user_alerts = UserEventAlertsPreferences.objects.filter(event=event, identifier=str(plant.slug))
                for alert in user_alerts:
                    if alert.email_id:
                        #send_detailed_report_with_attachment_for_renew(plant, alert.email_id)
                        send_daily_performance_report_post_mark_app_for_renew(plant, plant.groupClient,alert.email_id)
            except Exception as exception:
                print("Error in sending daily performance report : " + str(exception))
    except Exception as exception:
        print (str(exception))


def send_daily_performance_reports_for_atria():
    try:
        print(timezone.now())
        event = Events.objects.get(event_name="DAILY_REPORT")
        client = DataglenClient.objects.filter(slug='atria-power')
        plants = SolarPlant.objects.filter(groupClient=client)
        for plant in plants:
            try:
                print("Sending report for : " + str(plant.slug))
                get_monthly_report_to_attach_in_email_for_atria(plant)
                user_alerts = UserEventAlertsPreferences.objects.filter(event=event, identifier=str(plant.slug))
                for alert in user_alerts:
                    if alert.email_id:
                        #send_detailed_report_with_attachment_for_renew(plant, alert.email_id)
                        send_daily_performance_report_post_mark_app_for_atria(plant, plant.groupClient,alert.email_id)
            except Exception as exception:
                print("Error in sending daily performance report : " + str(exception))
    except Exception as exception:
        print (str(exception))

from helpdesk.data_uploader import send_email_report
def send_daily_performance_report_post_mark_app(plant, client, email_id):
    try:
        template_data = {}
        try:
            current_time = timezone.now()
            current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exc:
            logger.debug(str(exc))
            current_time = timezone.now()

        date = current_time.replace(hour=0,minute=0,second=0,microsecond=0)
        plant_summary = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                           count_time_period=86400,
                                                           identifier=str(plant.slug),
                                                           ts=date)
        template_data['date'] = str(date.date())
        template_data['client_name'] = client.name
        template_data['name'] = str(email_id).split('@')[0]
        template_data['plant_name'] = str(plant.name)
        template_data['plant_dc_capacity'] = str(plant.capacity) + ' kWp'
        template_data['plant_location'] = str(plant.location)
        if len(plant_summary)>0:
            template_data['energy_generation'] = fix_generation_units(plant_summary[0].generation)
            template_data['performance_ratio'] = str(round(float(plant_summary[0].performance_ratio)*100,2)) + ' %'
            template_data['CUF'] = str(round(float(plant_summary[0].cuf)*100,2)) + ' %'
            template_data['specific_yield'] = round(plant_summary[0].specific_yield,2)
        template_data['support_email'] = "support@dataglen.com"
        template_data['sender_name'] = "DataGlen Team"
        template_data['portal_download_link'] = "http://dataglen.com/"
        template_data['contact_email'] = "support@dataglen.com"
        print template_data
        current_time = timezone.now()
        starttime = current_time.replace(day=1)
        starttime = update_tz(starttime, plant.metadata.plantmetasource.dataTimezone)
        try:
            file_name = "_".join([str(plant.slug), str(calendar.month_name[starttime.month]), str(starttime.year), 'monthly_report']).replace(" ", "_") +  ".xls"
        except:
            file_name = "_".join([str(plant.slug),'monthly_report']).replace(" ", "_") +  ".xls"
        file_path = '/var/tmp/monthly_report/' + file_name
        to = email_id
        send_email_report(template_data, file_name, file_path, to, logger, template_id=None)
    except Exception as exception:
        print str(exception)


from solarrms.views import PDFReportSummary
from helpdesk.data_uploader import send_email_report_cleanmax
from django.contrib.auth.models import User
from dgusers.models import UserRole, SOLAR_USER_ROLE
from organizations.models import OrganizationUser, Organization

# sends email to each user with daily pdf report of all plants associated with that user
def send_daily_pdf_report(email_id, date_string=None):
    try:
        list_file_path=[]
        try:
            user = User.objects.get(email=email_id)
            client = user.role.dg_client
            user_name = (user.first_name).capitalize() + " " + (user.last_name).capitalize()
        except Exception as ex:
            logger.debug("user not found in send_daily_performance_report_post_mark_app_test_for_cleanmax. \
            PDF reports are customised for user hence wont generate any reports,exiting : %s, %s"%(email_id,ex))
            return
            # user_name = (str(email_id).split('@')[0]).capitalize()

        # plants = SolarPlant.objects.filter(groupClient=client)
        owner_user_id = user.role.dg_client.owner.organization_user.user.id
        organization_set = Organization.objects.filter(users=user.id)
        plants = SolarPlant.objects.filter(organization_ptr__in=organization_set)

        # organization_set = Organization.objects.filter(users=owner_user_id)
        # plants = SolarPlant.objects.filter(organization_ptr__in=organization_set)
        # For faster debugging limit plants
        # plants = plants[0:1]
        pdfs = PDFReportSummary()

        template_data = {}

        template_data['client_name'] = client.name
        template_data['name'] = user_name
        plant_name = []
        plant_dc_capacity = []
        plant_location = []
        energy_generation = []
        performance_ratio = []
        CUF = []
        specific_yield = []
        if date_string:
            try:
                parsed_date = parser.parse(date_string)
            except Exception as ex:
                logger.debug("Wrong Date format: %s" % str(ex))
                parsed_date=None
        else:
            parsed_date = None
        for plant in plants:
            try:
                if parsed_date is None:
                    current_time = timezone.now()
                    current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                    parsed_date = current_time
                else:
                    tzinfo = pytz.timezone(plant.metadata.plantmetasource.dataTimezone)
                    current_time = tzinfo.localize(parsed_date)
            except Exception as exc:
                logger.debug(str(exc))
                current_time = timezone.now()
            timestamp_to_generate_report = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            plant_summary = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',count_time_period=86400,identifier=str(plant.slug),ts=timestamp_to_generate_report)
            template_data['date'] = str(parsed_date.strftime("%d %b %Y"))
            plant_name.append(str(plant.name))
            plant_dc_capacity.append(str(plant.capacity) + ' kWp')
            plant_location.append(str(plant.location))
            if len(plant_summary) > 0:
                energy_generation.append(fix_generation_units(plant_summary[0].generation))
                performance_ratio.append(str(round(float(plant_summary[0].performance_ratio) * 100, 2)) + ' %')
                CUF.append(str(round(float(plant_summary[0].cuf) * 100, 2)) + ' %')
                specific_yield.append(round(plant_summary[0].specific_yield, 2))

            print template_data

            # Get Excel Report
            # starttime = current_time.replace(day=1)
            # starttime = update_tz(starttime, plant.metadata.plantmetasource.dataTimezone)
            # try:
            #     file_name = "_".join([str(plant.slug), str(calendar.month_name[starttime.month]), str(starttime.year),
            #                           'monthly_report']).replace(" ", "_") + ".xls"
            # except:
            #     file_name = "_".join([str(plant.slug), 'monthly_report']).replace(" ", "_") + ".xls"
            # file_path = '/var/tmp/monthly_report/' + file_name
            # list_file_path.append(file_path)
            to = email_id

            # Get PDF Reports
            file_name_pdf = pdfs.get_pdf_content(timestamp_to_generate_report.strftime("%Y-%m-%d"), plant, user)
            list_file_path.append(file_name_pdf)

        try:
            for i in range(len(plants)):
                template_data['plant_name' + str(i)] = plant_name[i]
                template_data['plant_dc_capacity' + str(i)] = plant_dc_capacity[i]
                template_data['plant_location' + str(i)] = plant_location[i]
                if energy_generation:
                    template_data['energy_generation' + str(i)] = energy_generation[i]
                if performance_ratio:
                    template_data['performance_ratio' + str(i)] = performance_ratio[i]
                if CUF:
                    template_data['CUF' + str(i)] = CUF[i]
                if specific_yield:
                    template_data['specific_yield' + str(i)] = specific_yield[i]
        except Exception as e:
            logger.debug("Length Mismatch in mail sending cleanmax"+str(e))
        template_data['support_email'] = "support@dataglen.com"
        template_data['sender_name'] = "DataGlen Team"
        template_data['portal_download_link'] = "https://solar.dataglen.com/"
        template_data['contact_email'] = "support@dataglen.com"
        # email_id = "upendra@dataglen.com"
        if client.name == "CleanMax Solar":
            # send_email_report_cleanmax(template_data, list_file_path, email_id, logger, template_id=None,\
            #                            cc="sunilkrghai@dataglen.com,upendra@dataglen.com,narsing@dataglen.com")
            send_email_report_cleanmax(template_data, list_file_path, email_id, logger, template_id=None)
            print "Sent email to====>>>> %s",email_id

        else:
            send_email_report_cleanmax(template_data, list_file_path, email_id, logger, template_id=None)
    except Exception as exception:
        print str(exception)
        logger.debug("EXCEPTION IN send_daily_pdf_report" + str(exception))

def cron_send_daily_pdf_reports_cleanmax():
    try:
        client = DataglenClient.objects.get(name="Cleanmax solar")
        users = UserRole.objects.filter(dg_client=client, daily_report=True)
        dt = datetime.datetime.now()
        yesterday_dt = dt - datetime.timedelta(days=1)
        dt_str = yesterday_dt.strftime("%Y-%m-%d")

        for user_role in users:
            # organization_set = Organization.objects.filter(users=user_role.user.id)
            # plants = SolarPlant.objects.filter(organization_ptr__in=organization_set)
            # print("sending daily pdf report for email ==== %s"%user_role.user.email), user_role.role, len(plants)
            logger.debug("sending daily pdf report for email ==== %s"%user_role.user.email)
            send_daily_pdf_report(user_role.user.email, dt_str)
    except Exception as ex:
        print ex
        logger.debug("Exception in cron_send_daily_pdf_reports_cleanmax %s" % str(ex))


from solarrms.views import PDFReportSummaryMonthly
from helpdesk.data_uploader import send_email_report_cleanmax
def send_monthly_performance_report_post_mark_app_for_cleanmax(client, email_id, date_obj=None):
    try:
        template_data = {}
        to = "upendra@dataglen.com"
        list_file_path=[]
        plants = SolarPlant.objects.filter(groupClient=client)
        pdfs = PDFReportSummaryMonthly()
        list_of_plant_names = []

        user = User.objects.filter(email=email_id)
        if user:
            user_name = (user[0].first_name).capitalize() + " " + (user[0].last_name).capitalize()
        else:
            user_name = (str(email_id).split('@')[0]).capitalize()
        template_data['client_name'] = client.name
        template_data['name'] = user_name

        if date_obj is None:
            date_obj = timezone.now()

        for plant in plants:
            list_of_plant_names.append(plant.name)
            file_name_pdf = pdfs.get_pdf_content(date_obj.strftime("%d-%m-%Y"), plant,"")
            list_file_path.append(file_name_pdf)
        template_data['support_email'] = "support@dataglen.com"
        template_data['sender_name'] = "DataGlen Team"
        template_data['portal_download_link'] = "https://solar.dataglen.com/"
        template_data['contact_email'] = "support@dataglen.com"
        template_data['plant_names'] = str(", ".join(list_of_plant_names))
        template_data['month_name'] = date_obj.strftime("%B-%Y")

        file_name = ""
        send_email_report_cleanmax(template_data, file_name, list_file_path, to, logger, template_id=8647966)
    except Exception as exception:
        print str(exception)
        logger.debug("EXCEPTION IN monthly pdf cron  " + str(exception))


def send_daily_performance_report_post_mark_app_for_renew(plant, client, email_id):
    try:
        template_data = {}
        try:
            current_time = timezone.now()
            current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exc:
            logger.debug(str(exc))
            current_time = timezone.now()

        date = current_time.replace(hour=0,minute=0,second=0,microsecond=0) - datetime.timedelta(days=1)
        plant_summary = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                           count_time_period=86400,
                                                           identifier=str(plant.slug),
                                                           ts=date)
        template_data['date'] = str(date.date())
        template_data['client_name'] = client.name
        template_data['name'] = str(email_id).split('@')[0]
        template_data['plant_name'] = str(plant.name)
        template_data['plant_dc_capacity'] = str(plant.capacity) + ' kWp'
        template_data['plant_location'] = str(plant.location)
        if len(plant_summary)>0:
            template_data['energy_generation'] = fix_generation_units(plant_summary[0].generation)
            template_data['performance_ratio'] = str(round(float(plant_summary[0].performance_ratio)*100,2)) + ' %'
            template_data['CUF'] = str(round(float(plant_summary[0].cuf)*100,2)) + ' %'
            template_data['specific_yield'] = round(plant_summary[0].specific_yield,2)
        template_data['support_email'] = "support@dataglen.com"
        template_data['sender_name'] = "DataGlen Team"
        template_data['portal_download_link'] = "http://dataglen.com/"
        template_data['contact_email'] = "support@dataglen.com"
        print template_data
        current_time = timezone.now()
        starttime = current_time.replace(day=1)
        starttime = update_tz(starttime, plant.metadata.plantmetasource.dataTimezone)
        try:
            file_name = "_".join([str(plant.slug), str(calendar.month_name[starttime.month]), str(starttime.year), 'monthly_report']).replace(" ", "_") +  ".xls"
        except:
            file_name = "_".join([str(plant.slug),'monthly_report']).replace(" ", "_") +  ".xls"
        file_path = '/var/tmp/monthly_report/new/' + file_name
        to = email_id
        send_email_report(template_data, file_name, file_path, to, logger, template_id=None)
    except Exception as exception:
        print str(exception)

def send_daily_performance_report_post_mark_app_for_atria(plant, client, email_id):
    try:
        template_data = {}
        try:
            current_time = timezone.now()
            current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exc:
            logger.debug(str(exc))
            current_time = timezone.now()

        date = current_time.replace(hour=0,minute=0,second=0,microsecond=0) - datetime.timedelta(days=1)
        plant_summary = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                           count_time_period=86400,
                                                           identifier=str(plant.slug),
                                                           ts=date)
        template_data['date'] = str(date.date())
        template_data['client_name'] = client.name
        template_data['name'] = str(email_id).split('@')[0]
        template_data['plant_name'] = str(plant.name)
        template_data['plant_dc_capacity'] = str(plant.capacity) + ' kWp'
        template_data['plant_location'] = str(plant.location)
        if len(plant_summary)>0:
            template_data['energy_generation'] = fix_generation_units(plant_summary[0].generation)
            template_data['performance_ratio'] = str(round(float(plant_summary[0].performance_ratio)*100,2)) + ' %'
            template_data['CUF'] = str(round(float(plant_summary[0].cuf)*100,2)) + ' %'
            template_data['specific_yield'] = round(plant_summary[0].specific_yield,2)
        template_data['support_email'] = "support@dataglen.com"
        template_data['sender_name'] = "DataGlen Team"
        template_data['portal_download_link'] = "http://dataglen.com/"
        template_data['contact_email'] = "support@dataglen.com"
        print template_data
        current_time = timezone.now()
        starttime = current_time.replace(day=1)
        starttime = update_tz(starttime, plant.metadata.plantmetasource.dataTimezone)
        try:
            file_name = "_".join([str(plant.slug), str(calendar.month_name[starttime.month]), str(starttime.year), 'monthly_report']).replace(" ", "_") +  ".xls"
        except:
            file_name = "_".join([str(plant.slug),'monthly_report']).replace(" ", "_") +  ".xls"
        file_path = '/var/tmp/monthly_report/atria/' + file_name
        to = email_id
        send_email_report(template_data, file_name, file_path, to, logger, template_id=None)
    except Exception as exception:
        print str(exception)

def client_level_generation_sms():
    print "start client_level_generation_sms"
    user_role = UserRole.objects.filter(sms=True)
    for ur in user_role:
        try:
            org_list = ur.user.organizations_organizationuser.all().values_list('organization_id', flat=True)
            splants = SolarPlant.objects.filter(organization_ptr__in=org_list)
            total_generation = 0.0
            total_plant = 0
            total_plant_capacity = 0.0
            phone_number = ur.phone_number
            current_time = timezone.now()
            for plant in splants:
                try:
                    current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                except Exception as exc:
                    print "exception %s" % exc
                    current_time = timezone.now()
                date = current_time.replace(hour=0, minute=0, second=0, microsecond=0)

                plant_summary = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                   count_time_period=86400,
                                                                   identifier=str(plant.slug),
                                                                   ts=date)
                if len(plant_summary) > 0:
                    total_generation += plant_summary[0].generation

                total_plant_capacity += plant.capacity
                total_plant += 1
            total_generation = fix_generation_units(total_generation)
            total_plant_capacity = fix_capacity_units(total_plant_capacity)
            date_month = current_time.date().strftime("%d/%m")
            print "total_plant %s" % total_plant
            print "total_generation %s" % total_generation
            print "total_plant_capacity %s" % total_plant_capacity
            print "date_month %s" % date_month

            if total_plant > 0 and phone_number:
                sms_message = "Hi,\nYour solar portfolio generation (%s plants, %s) for today (%s) is: %s. Thanks." \
                              %(total_plant, total_plant_capacity, date_month, total_generation)
                print send_solutions_infini_sms(phone_number, sms_message)
        except Exception as exception:
            print "exception with client_level_generation_sms %s" % exception
            continue
    print "end client_level_generation_sms"


# NewMod: Sends Daily Perfornamce Report of plants for which a user is subscribed to.Condition is users which have daily_report=True
def send_user_customised_daily_performance_report():
    try:
        # Remove following 3 lines in prod
        # tz = pytz.timezone("UTC")
        # date = datetime.datetime(2017, 11, 11, 0, 0)
        # utc_date = tz.localize(date)

        user_role = UserRole.objects.filter(daily_report=True)
        total_users=len(user_role)
        t_u=0
        logger.debug("There are [ %d ] users who want to receive daily report(daily_report=True)"%(total_users))
        logger.debug(user_role)
        for usr in user_role:
            print "Sending User Customised Daily Performance E Mail Report For : ",usr,"[ %d ] Remaining"%(total_users-t_u)
            logger.debug("Sending User Customised Daily Performance E Mail Report For : "+str(usr)+"[ %d ] Remaining"%(total_users-t_u))
            t_u+=1
            try:
                # organization_list is basically plant list with organization ids
                organization_list = usr.user.organizations_organizationuser.all().values_list('organization_id', flat=True)
                # org_list = ur.user.organizations_organizationuser.all().values_list('organization_id', flat=True)

                # plants gives list of plant with organization ids
                plants = SolarPlant.objects.filter(organization_ptr__in=organization_list)
                plants_list = ", ".join(plant.name for plant in plants)
                client_name = plants[0].groupClient.name
                cap = 0.0
                for p in plants:
                    cap = cap + p.capacity
                    # print p.capacity
                total_capacity = cap

                plant = plants[0]
                current_time = timezone.now()
                try:
                    current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                except Exception as exc:
                    # logger.debug(str(exc))
                    current_time = timezone.now()
                date = current_time.replace(hour=0, minute=0, second=0, microsecond=0)

                # Remove following line in production
                # date = utc_date.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                email_id = str(usr.user)

                userName = (email_id.split('@')[0]).title()
            except Exception as e:
                logger.debug("initialization exception"+str(e))

            try:
                file_name = "-".join([plant.groupClient.name, 'Daily-Portfolio-Report', str(date.date())]).replace(" ",
                                                                                                                   "-") + "-" + userName + ".xls"
            except:
                file_name = "-".join([plant.groupClient.name, 'Daily-Portfolio-Report']).replace(" ", "-") + "-" + userName + ".xls"

            summary_dict = excel_creation_for_user_customised_daily_performance_report(file_name, plants, date)
            print "SuMMMMMMMMMMMMMMMMMMmary dict",summary_dict

            try:
                if summary_dict!=None:
                    # print summary_dict
                    template_data = {}
                    template_data['date'] = str(date.date())
                    template_data['client_name'] = client_name
                    template_data['name'] = userName
                    template_data['plant_name'] = plants_list
                    template_data['plant_dc_capacity'] = total_capacity
                    template_data['plant_location'] = "Null"
                    template_data['energy_generation'] = summary_dict['Generation (kWh)']
                    template_data['performance_ratio'] = summary_dict['PR']
                    template_data['CUF'] = summary_dict['CUF']
                    template_data['specific_yield'] = summary_dict['Specific Yield']
                    template_data['support_email'] = "support@dataglen.com"
                    template_data['sender_name'] = "DataGlen Team"
                    template_data['portal_download_link'] = "http://dataglen.com/"
                    template_data['contact_email'] = "support@dataglen.com"
                    logger.debug("This is Email Template Data Dict : "+str(template_data))

                    file_path = '/var/tmp/monthly_report/test_daily/' + file_name
                    to = email_id
                    send_email_report(template_data, file_name, file_path, to, logger, template_id=None)

                    print "User Customised Daily Performance E Mail Report is Sent for : ", usr, "[ %d ] Remaining" %(total_users - t_u)
                else:
                    print "All details are empty so not sending any reports"
                    template_data = {}
                    template_data['date'] = str(date.date())
                    template_data['client_name'] = client_name
                    template_data['name'] = userName
                    template_data['plant_name'] = plants_list
                    template_data['plant_dc_capacity'] = total_capacity
                    template_data['plant_location'] = "Null"
                    template_data['energy_generation'] = "Not Available"
                    template_data['performance_ratio'] = "Not Available"
                    template_data['CUF'] = "Not Available"
                    template_data['specific_yield'] = "Not Available"
                    template_data['support_email'] = "support@dataglen.com"
                    template_data['sender_name'] = "DataGlen Team"
                    template_data['portal_download_link'] = "http://dataglen.com/"
                    template_data['contact_email'] = "support@dataglen.com"
                    logger.debug("This is EMPTY {} Email Template Data Dict : " + str(template_data))

                    file_path = '/var/tmp/monthly_report/test_daily/' + file_name
                    to = email_id
                    send_email_report(template_data, file_name, file_path, to, logger, template_id=None)
            except Exception as exception:
                # print "Exception in user customised daily report", str(exception), usr
                logger.debug("Exception in user customised daily report"+str(exception))
    except Exception as e:
        logger.debug("Exception in send_user_customised_daily_performance_report as : "+str(e))

def send_detailed_report_with_attachment_for_pvsyst_cleanmax(plant,file_name,email_id):
    try:
        template_data = {}
        template_data['client_name'] = plant.groupClient.name
        user = User.objects.filter(email=email_id)
        if user:
            user_name = (user[0].first_name).capitalize() + " " + (user[0].last_name).capitalize()
        else:
            user_name = (str(email_id).split('@')[0]).capitalize()
        template_data['name'] = user_name

        now = datetime.datetime.now()
        template_data['copyright_year'] = str(now.year)
        template_data['support_email'] = "support@dataglen.com"
        template_data['sender_name'] = "DataGlen Team"
        template_data['portal_download_link'] = "https://solar.dataglen.com/"
        dataglen_logo = "<img src= " + "http://www.comsnets.org/archive/2016/assets/images/partners/dataglen.jpg"
        group_logo = plant.dataglengroup.groupLogo if plant.dataglengroup.groupLogo else plant.groupClient.clientLogo
        client_logo = "<img src= " + str(group_logo)
        dataglen_logo_html = dataglen_logo + " style='max-width: 100%;width: 135px;'>"
        client_logo_html = client_logo + " style='max-width: 100%;width: 135px;' align='right'>"
        template_data['client_logo_html']=group_logo
        file_location = "/var/tmp/monthly_report/PVsyst/"
        file_path=file_location+file_name
        send_email_report(template_data, file_name, file_path, email_id, logger, template_id=5851682)

    except Exception as exception:
        print("Error in sending daily report: " + str(exception))
        logger.debug("Error in sending daily report: " + str(exception))


def cron_send_daily_report_consolidated(recepient_email, date_str):
    """
    recepient_email = "dataglen@jakson.com"
    date_str = "2018-05-08"
    cron_send_daily_report_consolidated(recepient_email, date_str)

    :param recepient_email:
    :param date_str:
    :return:
    """
    try:
        user = User.objects.get(email=recepient_email)
    except Exception as exception:
        logger.debug("user not found %s " % exception)
        return "user not found"
    user_full_name = user.first_name + " " + user.last_name
    now = datetime.datetime.now()
    copyright_year = str(now.year)
    date_wo_tz = parser.parse(date_str)
    plants = SolarPlant.objects.filter(organization_ptr__users__email="%s" % recepient_email)
    dg_client_name = user.role.dg_client.name
    client_name = re.sub("[^A-Za-z0-9\s-]", "", dg_client_name.replace(" ", "-"))
    file_name = "%s-portfolio-report-for-%s.xls" % (client_name, date_wo_tz.strftime("%B-%Y"))

    directory_path = "/var/tmp/monthly_report/portfolio/"
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
    out_path = directory_path + file_name
    stat = portfolio_monthly_excel(user, plants, date_wo_tz,out_path)
    if not stat:
        return "file not created"

    solar_plants = []
    for plant in plants:
        plant_dict = {}
        date = update_tz(date_wo_tz, plant.metadata.plantmetasource.dataTimezone)
        values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                     identifier=plant.slug, ts=date).limit(1)
        if len(values):
            plant_dict['name'] = plant.name
            plant_dict['dc_capacity'] = plant.capacity
            plant_dict['energy_generation'] = round(values[0].generation, 2)
            plant_dict['performance_ratio'] = round(values[0].performance_ratio*100, 2)
            plant_dict['cuf'] = round(values[0].cuf*100, 2)
            solar_plants.append(plant_dict)

    context = {}
    context['client_name'] = client_name
    context['user_full_name'] = user_full_name
    context['solar_plants'] = solar_plants
    context['copyright_year'] = copyright_year
    current_date = date.strftime("%d-%B-%Y")
    context['current_date'] = current_date
    message = render_to_string('solarmonitoring/daily_portfolio.html', context=context)
    postmark = PostmarkClient(server_token=POSTMARKAPP_KEY)
    attachments = [str(out_path)]
    out = postmark.emails.send(
        From='alerts@dataglen.com',
        # comment following line in production and uncomment next
        #To='upendra@dataglen.com',
        To=recepient_email,
        Subject='Daily Generation Report For All Plants [ %s ]' % current_date,
        HtmlBody=message,
        Attachments=attachments
    )
    print out
    logger.debug("Email is sent %s " % out)


def portfolio_monthly_excel(user,plants,date_wo_tz,out_path):
    """

    :param user:
    :param plants:
    :param date_wo_tz:
    :param out_path:
    :return:
    """
    try:
        user_features = []
        accessible_features = []
        client_name = user.role.dg_client.name
        user_features_obj_list = RoleAccess.objects.get(role=user.role.role,
                                                        dg_client=user.role.dg_client).features.all()
        for feature_obj in user_features_obj_list:
            user_features.append(str(feature_obj))
        for feature in user_features:
            if feature in feature_to_df_mappings:
                accessible_features.append(feature_to_df_mappings[feature])
        logger.debug("Accessible features list : " + str(accessible_features))
    except Exception as e:
        logger.debug("Exception for RoleAccess in PortfolioExcelReport" + str(e))
        accessible_features = ['Generation (kWh)', 'Inverter Total Generation (kWh)', 'PR', 'CUF',
                               'Specific Yield', 'Insolation (kWh/m^2)']
        logger.debug("Accessible features list after Exception : " + str(accessible_features))

    pandasWriter = pd.ExcelWriter(out_path, engine='xlsxwriter')
    startDate = date_wo_tz.replace(day=1)
    endDate = date_wo_tz.replace(day=calendar.monthrange(date_wo_tz.year, date_wo_tz.month)[1])

    for plant in plants:
        try:
            st = update_tz(startDate, plant.metadata.plantmetasource.dataTimezone)
            et = update_tz(endDate, plant.metadata.plantmetasource.dataTimezone)
        except:
            return ("startTime and endTime are required for monthly report")
        try:
            monthly_summary_report = get_monthly_report_values(st, et, plant, accessible_features)
            if not monthly_summary_report.empty:
                monthly_summary_report['Date'] = monthly_summary_report['Date'].map(lambda x: (
                    x.replace(tzinfo=pytz.utc).astimezone(plant.metadata.plantmetasource.dataTimezone)).date())

                monthly_summary_report, l1, l2 = manipulateColumnNames(monthly_summary_report, plant, 'Date')
                sheetName = str(plant.name)
                if len(sheetName) > 30:
                    sheetName = sheetName[:28]

                monthly_summary_report.to_excel(pandasWriter, sheetName)
                pandasWriter = excelConversion(pandasWriter, monthly_summary_report, l1, l2, sheetName)

        except Exception as exception:
            logger.debug(str(exception))

    pandasWriter.save()
    return True


def send_html_email_daily_portfolio():
    """

    :return:
    """

    print "start send_html_email_daily_portfolio"
    recepient_email = ("mwom@jakson.com", "kwom@jakson.com")
    date_str = "%s" % timezone.now().date()
    for email_id in recepient_email:
        cron_send_daily_report_consolidated(email_id, date_str)
    print "end send_html_email_daily_portfolio"


def function_for_cron_send_daily_report_consolidated_without_attachments(recepient_user_role_obj, date_str=None):
    recepient_email = recepient_user_role_obj.user.email

    if date_str == None:
        date_wo_tz = datetime.datetime.now()
        date_wo_tz = date_wo_tz.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        try:
            date_wo_tz = parser.parse(date_str)
        except Exception as exception:
            logger.debug("Exception in parsing time. %s"%exception)
    try:
        user = recepient_user_role_obj.user
        user_full_name = user.first_name + " " + user.last_name
        now = datetime.datetime.now()
        copyright_year = str(now.year)
        plants = SolarPlant.objects.filter(organization_ptr__users__email="%s" % user.email)
        dg_client_name = recepient_user_role_obj.dg_client.name
        client_name = re.sub("[^A-Za-z0-9\s-]", "", dg_client_name.replace(" ", "-"))

        week_dates = []
        for i in range(6,-1,-1):
            d = update_tz(date_wo_tz, plants[0].metadata.plantmetasource.dataTimezone) - datetime.timedelta(days=i)
            week_dates.append(d)

        solar_plants = []
        for plant in plants:
            plant_dict = {}
            weeks_generation_list = []
            values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                        count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                         identifier=plant.slug, ts__in=week_dates).order_by("-ts")

            if len(values):
                weeks_generation_list = [round(values[day].generation, 2) for day in range(7)]
                weeks_daily_avg = sum(weeks_generation_list) / 7
                weeks_data_string = str(weeks_generation_list)[1:-1]
                plant_dict['weeks_gen'] = weeks_data_string
                plant_dict['energy_generation_week_avg'] = round(weeks_daily_avg, 2)

                plant_dict['name'] = plant.name
                plant_dict['dc_capacity'] = plant.capacity
                plant_dict['energy_generation'] = round(values[0].generation, 2)
                plant_dict['performance_ratio'] = round(values[0].performance_ratio*100, 2)
                plant_dict['cuf'] = round(values[0].cuf*100, 2)
                solar_plants.append(plant_dict)

        context = {}
        # Check if user is cleanmax with client id 655. Remove PR for this client- changed as per client's request
        if recepient_user_role_obj.dg_client.id == 655:
            context['show_pr'] = 'False'
        else:
            context['show_pr'] = 'True'

        context['client_name'] = client_name
        context['user_full_name'] = user_full_name
        context['solar_plants'] = solar_plants
        context['copyright_year'] = copyright_year
        current_date = date_wo_tz.strftime("%d-%B-%Y")
        context['current_date'] = current_date
        message = render_to_string('solarmonitoring/daily_portfolio_without_attachment.html', context=context)
        postmark = PostmarkClient(server_token=POSTMARKAPP_KEY)
        # attachments = [str(out_path)]
        out = postmark.emails.send(
            From='alerts@dataglen.com',
            # comment following line in production and uncomment next
            # To='upendra@dataglen.com',
            To=recepient_email,
            Subject='Daily Generation Report For All Plants [ %s ]' % current_date,
            HtmlBody=message,
        )
        logger.debug("Email is sent %s " % out)
    except Exception as exception:
        logger.debug("Exception in sending daily email report : %s" % str(exception))

def cron_send_daily_sms_and_email_report_consolidated_for_all_plants_without_attachments():
    logger.debug("cron_send_daily_sms_and_email_report_consolidated_for_all_plants_without_attachments is started...")
    client_level_generation_sms()
    all_user_roles = UserRole.objects.filter(daily_report = True)
    for ur in all_user_roles:
        function_for_cron_send_daily_report_consolidated_without_attachments(ur)





