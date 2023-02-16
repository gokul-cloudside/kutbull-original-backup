import sys, dateutil, logging
from datetime import datetime
import pytz
import os
import requests
import time
import json
import configparser
from django.utils import timezone
from dataglen.models import ValidDataStorageByStream

#sys.path.append("/Dataglen/template-integration/kutbill-django")
#CONFIG_FILE_NAME = 'E:/dataglen/code\\kutbill-django-master-27ab965d99a60bf663463efe6c348f6759b39330/weather/forecastio.cfg'
CONFIG_FILE_NAME = 'forecastio.cfg'
DEFAULT_TIMEZONE = 'Asia/Kolkata'
JOBNAME = "UPLOAD_FORECASTIO_DATA"

class CaseConfigParser(configparser.ConfigParser):
    def optionxform(self, optionstr):
        return optionstr

class ForecastIO(object):
    def get_config_parameters(self):
        config_server = {}
        config_locations = {}
        try:
            cwd = os.path.dirname(os.path.realpath(__file__))
            config_file_path = os.path.join(cwd, CONFIG_FILE_NAME)
            #print "current dir " + str(os.getcwd()) + os.path.realpath(__file__) + " " + config_file_path
            print "Reading configuration filename " + config_file_path
            config = CaseConfigParser()
            config.read(config_file_path)

            # TODO: validate the existance of all necesasry params
            config_server = dict(config['SERVER'])
            locations = dict(config['LOCATIONS'])

            for key, value in locations.items():
                if value == 'TRUE':
                    dict1 = dict(config[key])
                    dict1['DATASOURCES'] = dict(config[key+'-DATASOURCES'])
                    config_locations[key] = dict1
        except Exception as e:
            print "configparser.Error occured %s. Fix errors in the configuration file" % (e.message)
            config_server = None
            config_locations = None
        return config_server, config_locations

    def __init__(self):
        self.config_server, self.config_locations = self.get_config_parameters()

    def fetch_forecastIO_data(self, latitude, longitude):
        fi_url = self.config_server['URL']
        apikey = self.config_server['APIKEY']
        retry_attempts = int(self.config_server['NO_OF_RETRY_ATTEMPTS'])
        retry_interval = int(self.config_server['RETRY_INTERVAL'])

        done = False
        attempts = 0
        while not done:
            if attempts == retry_attempts:
               return None
            attempts = attempts + 1

            url = fi_url + apikey + "/" + str(latitude) + "," + str(longitude) + "?units=si"
            try:                
                response = requests.get(url)
                done = True
                return response
            except Exception as e:
                print '\t Error occured fetching %s - error : %s  Retrying after %d secs.. No. of attempts %d out of %d' % (url, e.message, retry_interval, attempts, retry_attempts)
                time.sleep(retry_interval)
        return None 

    # store a single datastream values to DG
    def store_datastream_to_DG(self, sourceKey, streamName, timestamp, streamValue):
        dat1 = ValidDataStorageByStream(
             source_key = sourceKey,
             stream_name = streamName,
             timestamp_in_data = timestamp,
             stream_value = str(streamValue),
             insertion_time = timezone.now(),
             raw_value = str(streamValue),
             multiplication_factor = 1.0)
        dat1.save()
        
    # store the weather data source to DG 
    def store_datasource_to_DG(self, sourceKeyList, dataJson, tz):
        for dsName, dsKey in sourceKeyList.iteritems():
            sname = dsName.split("-")[2] # e.g dsName ForecastIO-Palladam-apparentTemperature
            stream_write_count = 0
            # there are 49 entries in the hourly clause in the forecast api call response
            # put into 50 datastreams.. temperature (current), temperature0 (forecast), temperature1, ...., temperature4
            for i in range(-2,49):                
                try:              
                    if i == -2: 
                        # to store the TIMESTAMP itself
                        streamName = "TIMESTAMP"
                        timestamp = self.epoch2datetimehour( dataJson['currently']['time'], tz )
                        streamValue = timestamp
                    elif i == -1: 
                        # get the currently data for the first stream e.g. temperature
                        streamName = sname
                        streamValue = dataJson['currently'][sname]
                        timestamp = self.epoch2datetimehour( dataJson['currently']['time'], tz )
                    else: 
                        # get hourly data for the forecast streams e.g. temperature0, temperature1, ..
                        streamName = sname + str(i)
                        dataBlock =  dataJson['hourly']['data']
                        streamValue = dataBlock[i][sname]
                        timestamp = self.epoch2datetimehour( dataBlock[i]['time'], tz )

                    #print "\t Inserting source: %s stream: %s time: %s value: %s" % (dsName,streamName,str(timestamp), str(streamValue))
                    self.store_datastream_to_DG(dsKey, streamName, timestamp, streamValue)
                    stream_write_count += 1

                except KeyError as e:
                    print "\t\t KeyError occured. source: %s i: %d error message : %s " % (dsName, i, e.message)
                except Exception as e:
                    print "\t\t Error occured. source: %s i: %d error message : %s" % (dsName, i, e.message)
            print "\t %d valid stream data for %s" % (stream_write_count, dsName) 

    # convert epoch to datetime and replace all mins and secs with 0s
    def epoch2datetimehour(self, epoch, tz):
        #tz = pytz.timezone('Asia/Kolkata')
        timestamp = datetime.utcfromtimestamp(epoch).replace(tzinfo=pytz.utc) 
        timestamp = timestamp.astimezone(tz)
        timestamp = timestamp.replace(minute=0, second=0)
        return timestamp

def getCurrentLocalTime(tz):
    epoch = int(time.time())
    #tz = pytz.timezone('Asia/Kolkata')
    timestamp = datetime.utcfromtimestamp(epoch).replace(tzinfo=pytz.utc) 
    timestamp = timestamp.astimezone(tz)
    return timestamp

def log_endjob_msg(jobname, tz):
    print("\n============ CRON JOB %s STOPPED at TIME %s ============" % (jobname, str(getCurrentLocalTime(tz))))

def log_startjob_msg(jobname, tz):
    print("\n============ CRON JOB %s STARTED at TIME %s ============" % (jobname, str(getCurrentLocalTime(tz))))

def upload_forecastIO_data():
    
    cur_tz = pytz.timezone(DEFAULT_TIMEZONE)    
    log_startjob_msg(JOBNAME, cur_tz)
    
    fio = ForecastIO()
    if not fio.config_server or not fio.config_locations:
        log_endjob_msg(JOBNAME, cur_tz)
        return

    locations = fio.config_locations;
    
    for key, loc in locations.iteritems():
        print "\n------------------------------ %s ------------------------------" % (str(getCurrentLocalTime(cur_tz)))
        print "Location : %s -> Latitude : %s Longitude : %s Timezone : %s" % (loc['NAME'], loc['LATITUDE'], loc['LONGITUDE'], loc['TIMEZONE'])
        print "Location : %s -> Fetching weather forecast data" % (loc['NAME'])
        response = fio.fetch_forecastIO_data(loc['LATITUDE'], loc['LONGITUDE'])

        if response == None:
            print "Location : %s -> Network error occured" % (loc['NAME'])
            continue
        if response.status_code != 200:
            print "Location : %s -> Invalid response. code : %d text : %s" % (loc['NAME'], response.status_code, response.text)
            continue
        print "Location : %s -> Fetching weather forecast data SUCCESS" % (loc['NAME'])

        try:
            dataJson = response.json()
            print "Location : %s -> Parsing weather forecast data SUCCESS" % (loc['NAME'])
        except Exception as e:
            print "Location : %s -> Json conversion error occured. message : %s" % (loc['NAME'], e.message)
            continue
        
        #print "\nLocation : %s -> %s - DATA: %s \n" % (loc['NAME'], str(getCurrentLocalTime(cur_tz)), str(dataJson))
        
        try:
            print "Location : %s -> Stroing weather forecast data to DataGlen" % (loc['NAME'])
            sourceKeyList = loc['DATASOURCES']
            loc_tz = pytz.timezone(loc['TIMEZONE'])
            fio.store_datasource_to_DG(sourceKeyList, dataJson, loc_tz)
            print "Location : %s -> Stroing weather forecast data to DataGlen DONE" % (loc['NAME'])
        except Exception as e:
            print "Location : %s -> Error occured : %s" % (loc['NAME'], e.message)
            continue
        time.sleep(5)

    log_endjob_msg(JOBNAME, cur_tz)