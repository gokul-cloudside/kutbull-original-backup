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
from solarrms.cron_cleaning_schedule_new import handle_cleaning_schedule_result

from_server_address = 'http://kafkastaging.dataglen.org'
sources_url = '/ocpu/user/samy/library/rsolar/R/cleaning_schedule_rf/json'
header = {'Content-Type': 'application/json'}

def run_specific_cleaning():
    today=datetime.now() - timedelta(days=2)
    today = '2017-11-05'#today.strftime('%Y-%m-%d')
    plant_name = 'santarem'
    #plant_name = 'castelo'
    plant = SolarPlant.objects.get(slug=plant_name)
    try:
        key_value = Token.objects.get(user=plant.groupClient.owner.organization_user.user)
    except Exception as ex:
        print 'Exception occured while getting apikey:', ex, ' skipping ', plant_name
        #continue
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


