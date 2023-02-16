from django.conf import settings
from solarrms.models import PredictedValues
from datetime import datetime, timedelta
from django.utils import timezone
import requests
import json
import sys
import pytz
from solarrms.models import SolarPlant
from rest_framework.authtoken.models import Token
from helpdesk.dg_functions import create_ticket
from helpdesk.models import Queue, Ticket
from solarrms.cron_new_tickets import close_ticket

tz_ist = pytz.timezone('Asia/Kolkata')

#plant_names = { 'waaneep' : '1971e093c790edb3fd5c38dc93029c317f5fe396' }
header = {'Content-Type': 'application/json'}

def DG_get_dataSourceList(apikey):
    dg_server = 'http://dataglen.com/'
    dg_header = {'Authorization': 'Token ' + apikey,
                 'Content-Type' : 'application/json'}
    dg_get_url = dg_server + 'api/sources/'
    r = requests.get(dg_get_url, headers=dg_header)
    return r

#('1 18 * * *', 'solarrms.cron_cleaning_schedule.cleaning_schedule', '>> /var/log/kutbill/cleaning_schedule.log 2>&1')
#curl http://analytics.dataglen.org/ocpu/user/samy/library/rsolar/R/cleaning_schedule/json
def cleaning_schedule(today=datetime.now()):
    try:
        print datetime.now().isoformat(), "cleaning_schedule CRONJOB STARTED"
        from_server_address = 'http://kafkastaging.dataglen.org'
        sources_url = '/ocpu/user/samy/library/rsolar/R/cleaning_schedule/json'
        #today = datetime.now()
        today = today.strftime('%Y-%m-%d')
        plants = SolarPlant.objects.all()
        #plants = SolarPlant.objects.filter(slug='airportmetrodepot')
        # Copy the inverter data
        for plant in plants:
            plant_name = plant.slug
            try:
                key_value = Token.objects.get(user=plant.groupClient.owner.organization_user.user)
            except Exception as ex:
                print 'Exception occured while getting apikey:', ex, ' skipping ', plant_name
                continue
            apikey = str(key_value.key)
            # dataSourceList = None
            # try:
            #     print("Getting datasource list for %s", str(plant_name))
            #     dataSourceList = DG_get_dataSourceList(apikey)
            #     dataSourceList = dataSourceList.json()
            # except Exception as ex:
            #     print("Exception occured in cleaning_schedule cronjob : %s", str(ex))
            #     continue
            #
            # if dataSourceList == None:
            #     print("Empty datasource list for %s.. skipping", str(plant_name))
            #     continue
            print("Computing for plant : ", str(plant_name))
            inverters = plant.independent_inverter_units.all()
            for ds in inverters:
                invkey = ds.sourceKey
                inverter = ds.name
                try:
                    from_url = from_server_address + sources_url
                    params = {'plantname': plant_name, 'invkey': invkey, 'date': str(today)}
                    print datetime.now().isoformat(), today, plant_name, inverter, invkey, 'making API call...'
                    response = requests.post(from_url, headers=header, data=json.dumps(params))
                    response_json = json.loads(response.content)
                    #inverter = 'Inverter_1.1'
                    print datetime.now().isoformat(), today, plant_name, inverter, invkey, 'saving cleaning schedule...'
                    if handle_cleaning_schedule_result(plant_name, inverter, response_json):
                        print datetime.now().isoformat(), today, plant_name, inverter, invkey, response.status_code
                    else:
                        print datetime.now().isoformat(), today, plant_name, inverter, invkey, response.status_code, response.text
                except Exception as ex:
                    print("Exception occured while calling cleaning_schedule API : %s", str(ex))
                    pass
            new_create_cleaning_ticket(str(plant.slug), 'cleaning')
        print datetime.now().isoformat(), "cleaning_schedule CRONJOB STOPPED"
    except Exception as ex:
        print("Exception occured in cleaning_schedule cronjob : %s", str(ex))

def handle_cleaning_schedule_result(plant_name, inverter, cleaning_res):
    if not cleaning_res.has_key('cleaning'):
        return False

    cleaning  = cleaning_res['cleaning']
    timestamp   = cleaning['timestamp']
    actual      = cleaning['actual']
    predicted   = cleaning['predicted']
    residuals   = cleaning['residuals']
    residual_sum = cleaning['residual_sum']
    losses = cleaning['losses']
    model_name  = 'regression'
    stream_name = 'cleaning'
    plant_name = plant_name + "-" + inverter
    for index in range(len(timestamp)):
        #print 'saving -', timestamp[index], residuals[index]
        ts = parse_timestamp(timestamp[index])
        ac = float(actual[index])
        pr = float(predicted[index])
        rs = float(residuals[index])
        rs_sum = float(residual_sum[index])
        loss = float(losses[index])
        print 'saving ', ts, rs, rs_sum, loss
        save_cleaning_schedule(plant_name, stream_name, model_name, ts, ac, pr, rs, rs_sum, loss)
    return True

def save_cleaning_schedule(plant_name, stream_name, model_name, timestamp, actual, predicted, residual, residual_sum, losses):
    #ts           = timezone.now()
    #plantname    = 'palladam'
    #stream_name  = 'energy'
    #model_name   = 'svm'
    #actual       = 0.0
    #predicted    = 0.0
    try:
        predict = PredictedValues.objects.create(
                    timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_TIMESTAMP_IN_DATA,
                    count_time_period = settings.DATA_COUNT_PERIODS.DAILY,
                    identifier = plant_name,
                    stream_name = stream_name,
                    model_name = model_name,
                    actual_value = actual,
                    predicted_value = predicted,
                    residual  = residual,
                    residual_sum=residual_sum,
                    losses = losses,
                    ts = timestamp,
                    updated_at = timezone.now() )
        predict.save()
    except Exception as ex:
        print("Exception occured while saving predictions : %s %s", str(ex), str(timestamp))

    # Create the ticket if the predicted value goes below a threshold value

def parse_timestamp(timestamp):
    #ts = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
    ts = datetime.strptime(timestamp, '%Y-%m-%d')
    if ts.tzinfo is None:
        ts = tz_ist.localize(ts)
        ts = ts.astimezone(tz_ist)
    return ts

# def create_cleaning_ticket(plant_name, stream_name):
#     try:
#         try:
#             plant = SolarPlant.objects.get(slug=plant_name)
#         except Exception as exception:
#             print("No plant found with name : " + str(plant_name))
#
#         inverters = plant.independent_inverter_units.all()
#         associations_dict = {}
#         for inverter in inverters:
#             # get the last 3 entry from the predicted table for this plant
#             values = PredictedValues.objects.filter(timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_TIMESTAMP_IN_DATA,
#                                                     count_time_period = settings.DATA_COUNT_PERIODS.DAILY,
#                                                     identifier=str(plant.slug)+'-'+str(inverter.name),
#                                                     stream_name='cleaning').limit(3)
#             if len(values) == 3 and inverter.total_capacity:
#                 residual_threshold = (int(settings.CLEANING_THRESHOLD_PERCENT)*inverter.total_capacity)/100.0
#                 if values[0].residual < 0 and abs(values[0].residual) > residual_threshold and \
#                     values[0].residual<values[1].residual and values[1].residual<values[2].residual:
#                     # raise ticket
#                     try:
#                         current_time = timezone.now()
#                         current_time = current_time.astimezone(pytz.timezone(inverter.dataTimezone))
#                     except Exception as exc:
#                         current_time = timezone.now()
#                     priority = 1
#                     due_date = current_time + datetime.timedelta(hours=12)
#                     associations_dict[inverter.sourceKey] = ['CLEANING_REQUIRED', '-2', inverter.name, current_time]
#         print associations_dict
#         if len(associations_dict) > 0:
#             try:
#                 create_ticket(plant=plant, priority=priority, due_date=due_date,
#                               ticket_name="Cleaning of solar panels required " + " at " + str(plant.location),
#                               ticket_description = 'The generation has been decreasing over past 3 days at ' + str(plant.location) + '. Hence, cleaning of solar panels are required. ',
#                               associations_dict = associations_dict,
#                               open_comment='Ticket created automatically based on the generation analysis.')
#             except Exception as exception:
#                 print("Error in creating ticket for plant : " + str(plant.slug) + " - " + str(exception))
#     except Exception as exception:
#         print("Error in creating cleaning schedule ticket : " + str(exception))


def create_panel_cleaning_ticket(plant, priority, due_date):
    try:
        ticket_name = "Cleaning of solar panels required : " + str(plant.location)
        ticket_description = 'The generation has been decreasing over past 3 days at ' + str(plant.location) + '. Hence, cleaning of solar panels are required. '
        event_type = "PANEL_CLEANING"
        open_comment = "Tickets created automatically based on the residual values of inverters."
        new_panel_cleaning_ticket = create_ticket(plant=plant, priority=priority, due_date=due_date, ticket_name=ticket_name,
                                                              ticket_description=ticket_description, open_comment=open_comment, event_type=event_type)
        return new_panel_cleaning_ticket
    except Exception as exception:
        print("Error in creating panel cleaning ticket: " + str(exception))

def new_create_cleaning_ticket(plant_name, stream_name):
    try:
        try:
            plant = SolarPlant.objects.get(slug=plant_name)
        except Exception as exception:
            print("No plant found with name : " + str(plant_name))

        inverters = plant.independent_inverter_units.all()
        panel_cleaning_inverters_dict = {}
        panel_cleaning_inverters_list = []
        try:
            queue = Queue.objects.get(plant=plant)
        except Exception as exception:
            print ("Queue does not exist for plant : " + str(plant.slug))
        for inverter in inverters:
            panel_cleaning_list_temp = []
            # get the last 3 entry from the predicted table for this plant
            values = PredictedValues.objects.filter(timestamp_type = settings.TIMESTAMP_TYPES.BASED_ON_TIMESTAMP_IN_DATA,
                                                    count_time_period = settings.DATA_COUNT_PERIODS.DAILY,
                                                    identifier=str(plant.slug)+'-'+str(inverter.name),
                                                    stream_name='cleaning').limit(3)

            try:
                current_time = timezone.now()
                current_time = current_time.astimezone(pytz.timezone(inverter.dataTimezone))
            except Exception as exc:
                current_time = timezone.now()
            if len(values) == 3 and inverter.total_capacity:
                #residual_threshold = (int(settings.CLEANING_THRESHOLD_PERCENT)*inverter.total_capacity)/100.0
                # if values[0].residual < 0 and abs(values[0].residual) > residual_threshold and \
                #     values[0].residual<values[1].residual and values[1].residual<values[2].residual:
                #if values[0].losses> 0 and values[1].losses > 0 and values[2].losses > 0:
                if values[0].residual_sum< 0 and values[1].residual_sum < 0 and values[2].residual_sum < 0:
                    print "inside values"
                    panel_cleaning_inverters_list.append(str(inverter.sourceKey))
                    panel_cleaning_dict_temp = {}
                    panel_cleaning_dict_temp['st'] = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
                    panel_cleaning_dict_temp['et'] = current_time.replace(hour=19, minute=0, second=0, microsecond=0)
                    panel_cleaning_dict_temp['identifier'] = str(inverter.name)
                    panel_cleaning_dict_temp['residual'] = values[0].residual_sum
                    panel_cleaning_list_temp.append(panel_cleaning_dict_temp)
                    panel_cleaning_inverters_dict[str(inverter.sourceKey)] = panel_cleaning_list_temp

            print "panel_cleaning_inverters_list"
            print (panel_cleaning_inverters_list)
            print "panel_cleaning_inverters_dict"
            print panel_cleaning_inverters_dict

        # check if an open ticket exists for Inverters Under performing
        panels_cleaning_ticket = Ticket.objects.filter(queue=queue, event_type='PANEL_CLEANING', status=1)
        if len(panels_cleaning_ticket)>0:
            # Ticket exists, update the association
            panels_cleaning_ticket[0].update_ticket_associations(panel_cleaning_inverters_list, performance_dict=panel_cleaning_inverters_dict)
            if len(panel_cleaning_inverters_dict)==0:
                # Ticket exist, but the problem does not exist now, close the ticket
                close_ticket(plant=plant, ticket=panels_cleaning_ticket[0], request_arrival_time=timezone.now())
        elif len(panels_cleaning_ticket) == 0 and len(panel_cleaning_inverters_dict)>0:
            # Ticket does not exist,problem has occurred just now, create a new ticket.
            print "inside create ticket"
            new_panel_cleaning_ticket = create_panel_cleaning_ticket(plant, 1, None)
            new_panel_cleaning_ticket.update_ticket_associations(panel_cleaning_inverters_list, performance_dict=panel_cleaning_inverters_dict)
        else:
            pass
    except Exception as exception:
        print("Error in panel cleaning ticket : " + str(exception))