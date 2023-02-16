from django.conf import settings
from solarrms.models import PredictedValues
from datetime import datetime, timedelta
from django.utils import timezone
import requests
import json
import sys
import pytz

tz_ist = pytz.timezone('Asia/Calcutta')

plant_names = ['palladam'] 
header = {'Content-Type': 'application/json'}

#('1 18 * * *', 'solarrms.cron_generation_prediction.generation_prediction', '>> /var/log/kutbill/generation_prediction.log 2>&1')
#curl http://analytics.dataglen.org/ocpu/user/samy/library/rsolar/R/generation_prediction/json 
def generation_prediction():
    try:
        print datetime.now().isoformat(), "generation_prediction CRONJOB STARTED"
        from_server_address = 'http://analytics.dataglen.org'
        sources_url = '/ocpu/user/samy/library/rsolar/R/generation_prediction/json'
        today = datetime.now()
        today = today.strftime('%Y-%m-%d')
        
        # Copy the inverter data
        for plant_name in plant_names:
            try:
                from_url = from_server_address + sources_url 
                params = {'plantname': plant_name, 'date': str(today)}
                print datetime.now().isoformat(), today, plant_name, 'making API call...'
                response = requests.post(from_url, headers=header, data=json.dumps(params))
                response_json = json.loads(response.content)
                print datetime.now().isoformat(), today, plant_name, 'saving predictions...'
                if handle_prediction_result(plant_name, response_json):
                    print datetime.now().isoformat(), today, plant_name, response.status_code
                else:
                    print datetime.now().isoformat(), today, plant_name, response.status_code, response.text
            except Exception as ex:
                print("Exception occured while calling generation_prediction API : %s", str(ex))
                pass
        print datetime.now().isoformat(), "generation_prediction CRONJOB STOPPED"
    except Exception as ex:
        print("Exception occured in generation_prediction cronjob : %s", str(ex))

def handle_prediction_result(plant_name, prediction_res):
    if not prediction_res.has_key('prediction'):
        return False

    prediction  = prediction_res['prediction']
    timestamp   = prediction['timestamp']
    energy      = prediction['energy']
    predicted   = prediction['predicted']
    model_name  = 'svm'
    stream_name = 'energy'

    for index in range(len(timestamp)):
        ts = parse_timestamp(timestamp[index])
        en = float(energy[index])
        pr = float(predicted[index])
        #print 'saving ', ts, en, pr
        save_prediction(plant_name, stream_name, model_name, ts, en, pr) 
    return True

def save_prediction(plant_name, stream_name, model_name, timestamp, actual, predicted):
    #ts           = timezone.now()
    #plantname    = 'palladam'
    #stream_name  = 'energy'
    #model_name   = 'svm'
    #actual       = 0.0
    #predicted    = 0.0
    try:
        predict = PredictedValues.objects.create(
                    timestamp_type    = settings.TIMESTAMP_TYPES.BASED_ON_TIMESTAMP_IN_DATA,
                    count_time_period = settings.DATA_COUNT_PERIODS.HOUR,
                    identifier   = plant_name,
                    stream_name  = stream_name,
                    model_name   = model_name,
                    actual_value = actual,
                    predicted_value = predicted,
                    ts = timestamp,
                    updated_at = timezone.now() )
        predict.save()
    except Exception as ex:
        print("Exception occured while saving predictions : %s %s", str(ex), str(timestamp))

def parse_timestamp(timestamp):
    ts = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
    if ts.tzinfo is None:
        ts = tz_ist.localize(ts)
        ts = ts.astimezone(tz_ist)
    return ts
