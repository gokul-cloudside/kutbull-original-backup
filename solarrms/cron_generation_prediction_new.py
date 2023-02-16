from django.conf import settings
from solarrms.models import PredictedValues
from datetime import datetime, timedelta
from django.utils import timezone
import requests
import json
import sys
import pytz
import pandas as pd

import traceback

tz_ist = pytz.timezone('Asia/Calcutta')
DG_SERVER = "http://dataglen.com/"
NO_OF_TRAINING_DAYS = 30

plantdetails = { 'palladam' : '13fcd7319bb9ae25bf7ea290f9f2ba8eca2e41bc',
                 'waaneep' : '1971e093c790edb3fd5c38dc93029c317f5fe396' }

def DG_download_energy_data(plantname, apikey, startTime, endTime):
    dg_header = {'Authorization': 'Token ' + apikey, 'Content-Type' : 'application/json'}
    energy_url = DG_SERVER + "/api/solar/plants/" + plantname + "/energy/?startTime=" 
    energy_url = energy_url + startTime + "&endTime=" + endTime + "&aggregator=HOUR"
    r = requests.get(energy_url, headers=dg_header)
    return r

#('1 18 * * *', 'solarrms.cron_generation_prediction.generation_prediction', '>> /var/log/kutbill/generation_prediction.log 2>&1')
#curl http://analytics.dataglen.org/ocpu/user/samy/library/rsolar/R/generation_prediction/json 
def generation_prediction_new():
    try:
        print datetime.now().isoformat(), "generation_prediction CRONJOB STARTED"
        today = datetime.now().date()
        startTime = str( today - timedelta(days = NO_OF_TRAINING_DAYS) )
        endTime   = str( today )

        for plantname, apikey in plantdetails.iteritems():
            try:
                print 'Downloaing energy data for plant ', plantname
                response = DG_download_energy_data(plantname, apikey, startTime, endTime)
                if response.status_code == 200:
                    print 'Predicting energy data for plant ', plantname
                    energy_prediction(plantname, response.text)
                else:
                    print datetime.now().isoformat(), 'Error occured', plantname, response.status_code
            except Exception as ex:
                print("Exception occured while calling generation_prediction API : %s", str(ex))
                pass
        print datetime.now().isoformat(), "generation_prediction CRONJOB STOPPED"
    except Exception as ex:
        print("Exception occured in generation_prediction cronjob : %s", str(ex))

def energy_prediction(plantname, energy_data):
    startHour = 6
    endHour   = 18
    today = datetime.now().date()
    model_name = 'summary'

    try:
        df1 = pd.read_json(energy_data, typ='frame')
        df1.timestamp = pd.to_datetime(df1.timestamp)
        df1.timestamp = df1.timestamp + timedelta(hours = 5.5) # convert UTC to IST, TODO: validation of UTC
        df1.set_index('timestamp', inplace=True)

        for hour in range(startHour,endHour+1):
            hr = str(hour) + ':00'
            print '\t generation prediction for hour ', hr
            df_hr = df1.between_time(hr, hr)
            energy_avg = df_hr.energy.mean()
            energy_std  = df_hr.energy.std()
            (lower, upper) = cal_bounds_std(df_hr.energy, 1) # calc 1st std based bounds
            #print energy_avg, energy_std, lower, upper
            ts = str(today) + ' ' + hr + ':00'
            save_prediction(plantname, 'generation', model_name, ts, energy_avg, energy_avg, 0.0) 
            #save_prediction(plantname, 'generation_lower', model_name, ts, lower, lower, 0.0) 
            #save_prediction(plantname, 'generation_upper', model_name, ts, upper, upper, 0.0) 
    except Exception as ex:
        print("Exception occured in generation_prediction cronjob : %s", str(ex))
    return True

def save_prediction(plant_name, stream_name, model_name, timestamp, actual, predicted, residual):
    try:
        predict = PredictedValues.objects.create(
                    timestamp_type    = settings.TIMESTAMP_TYPES.BASED_ON_TIMESTAMP_IN_DATA,
                    count_time_period = settings.DATA_COUNT_PERIODS.HOUR,
                    identifier   = plant_name,
                    stream_name  = stream_name,
                    model_name   = model_name,
                    actual_value = actual,
                    predicted_value = predicted,
                    residual  = residual,
                    ts = timestamp,
                    updated_at = timezone.now() )
        predict.save()
    except Exception as ex:
        print("Exception occured while saving predictions : %s %s", str(ex), str(timestamp))
        traceback.print_exc()

def cal_bounds_std(data, nstd):
    avg = data.mean()
    sd = data.std()
    upper = avg + nstd * sd
    lower = avg - nstd * sd
    return (lower, upper)

def parse_timestamp(timestamp):
    ts = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
    if ts.tzinfo is None:
        ts = tz_ist.localize(ts)
        ts = ts.astimezone(tz_ist)
    return ts
