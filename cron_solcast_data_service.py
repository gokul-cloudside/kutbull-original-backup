import json
import requests
import time
from dateutil import parser
import csv
import datetime
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider


SOLCAST_RADIATION_FORECAST_API_URL = "https://api.solcast.com.au/radiation/forecasts"
SOLCAST_RADIATION_ACTUAL_API_URL = "https://api.solcast.com.au/radiation/estimated_actuals"
SOLCAST_POWER_FORECAST_API_URL = "https://api.solcast.com.au/pv_power/forecasts"
SOLCAST_POWER_ACTUAL_API_URL = "https://api.solcast.com.au/pv_power/estimated_actuals"
SOLCAST_API_KEY = "dqPK8G13mwfAVVJAmIEI9DC7s6atWGMS"
LAT_LNG_SOURCE_FILE = "./city_lat_lng.csv"
CASSANDRA_CLUSTER_HOST = ['10.148.0.14', '10.148.0.15']
CASSANDRA_KEYSPACE = "dataglen_weather_data"
CASSANDRA_TABLE = "weather_data"
HOURLY = "hourly"
DAILY = "daily"
CURRENT = "current"
FUTURE = "future"
API_SOURCE = "solcast"
RADIATION='RADIATION'
POWER='POWER'
CAPACITY = 1000

def _weather_api_call(url, query_parameter):
    """

    :param query_parameter: either city name or lat long as q
    :param timestamp_type: specify hourly or daily data
    :return:
    """
    response_json = None
    url = "%s?%s&api_key=%s&format=json" % (url, query_parameter, SOLCAST_API_KEY)
    print url
    try:
        response = requests.get(url)
        print response
        response_json = json.loads(response.content)
    except Exception as es:
        print(str(es))
    # per second call
    time.sleep(1)
    return response_json


def cron_collect_solcast_weather_data_main():
    """

    :return: cron to collect data from world weather and save on daily and hourly bases
    """
    print "Start collecting weather data main!"
    auth_provider = PlainTextAuthProvider(username='rkunnath', password='P@tt@nch3ry')
    cluster = Cluster(CASSANDRA_CLUSTER_HOST, auth_provider=auth_provider)
    session = cluster.connect(CASSANDRA_KEYSPACE)

    with open(LAT_LNG_SOURCE_FILE, "rb") as fp:
        reader = csv.reader(fp, delimiter=',')
        _ = next(reader)
        for row in reader:
            city_id, city_name, longitude, latitude = row
            city_name = city_name.lower()
            lat_lng = "longitude=%s&latitude=%s" % (longitude, latitude)
            if not lat_lng or "NA" in lat_lng:
                continue
            # 30 min data for current and future for RADIATION
            _create_radiation_forecasts_data(lat_lng, city_name, session)
            _create_radiation_estimated_actuals_data(lat_lng, city_name, session)
            # 30 min data for current and future for POWER
            _create_power_forecasts_actual_data(lat_lng, city_name, session, SOLCAST_POWER_FORECAST_API_URL, FUTURE)
            _create_power_forecasts_actual_data(lat_lng, city_name, session, SOLCAST_POWER_ACTUAL_API_URL, CURRENT)

    print "End collecting weather data main!"


def _create_radiation_forecasts_data(lat_lng, city_name, session):
    """

    :param lat_lng_or_city: either lat long or city
    :param splants: solar plant query set
    :return:
    """
    try:
        print "Start _create_radiation_forecasts_data %s!" % city_name
        weather_data_response = _weather_api_call(SOLCAST_RADIATION_FORECAST_API_URL, lat_lng)
        if 'forecasts' not in weather_data_response:
            return
        weather_data_response['forecasts'] = weather_data_response['forecasts'][0:48]
        for wapi_data in weather_data_response['forecasts']:
            weather_data_dict = dict()
            try:
                time_stamp = datetime.datetime.now()
                wapi_data['period_end'] = parser.parse(wapi_data['period_end'])
            except:
                time_stamp = datetime.datetime.now()
            #define parameters dict
            weather_data_dict['air_temp'] = wapi_data['air_temp']
            weather_data_dict['api_source'] = "%s" % API_SOURCE
            weather_data_dict['api_request_type'] = "%s" % RADIATION
            weather_data_dict['azimuth'] = wapi_data['azimuth']
            weather_data_dict['city'] = "%s" % city_name
            weather_data_dict['cloud_opacity'] = wapi_data['cloud_opacity']
            weather_data_dict['dhi'] = wapi_data['dhi']
            weather_data_dict['dni'] = wapi_data['dni']
            weather_data_dict['dni_10'] = wapi_data['dni10']
            weather_data_dict['dni_90'] = wapi_data['dni90']
            weather_data_dict['ebh'] = wapi_data['ebh']
            weather_data_dict['ghi'] = wapi_data['ghi']
            weather_data_dict['ghi_10'] = wapi_data['ghi10']
            weather_data_dict['ghi_90'] = wapi_data['ghi90']
            weather_data_dict['latitude'] = float(lat_lng.split("&")[1].split("=")[1])
            weather_data_dict['longitude'] = float(lat_lng.split("&")[0].split("=")[1])
            weather_data_dict['prediction_type'] = FUTURE
            weather_data_dict['timestamp_type'] = HOURLY
            weather_data_dict['ts'] = "%s" % wapi_data['period_end'].replace(tzinfo=None)
            weather_data_dict['updated_at'] = "%s" % time_stamp.replace(microsecond=0)
            weather_data_dict['zenith'] = wapi_data['zenith']
            #close define paratmers dict
            _weather_cassandra_query(session, weather_data_dict)
        print "End _create_radiation_forecasts_data %s!" % city_name
    except Exception as exception:
        print "%s" % exception


def _create_radiation_estimated_actuals_data(lat_lng, city_name, session):
    """

    :param lat_lng_or_city: either lat long or city
    :param splants: solar plant query set
    :return:
    """
    try:
        print "Start _create_radiation_estimated_actuals_data %s!" % city_name
        weather_data_response = _weather_api_call(SOLCAST_RADIATION_ACTUAL_API_URL, lat_lng)
        if 'estimated_actuals' not in weather_data_response:
            return
        weather_data_response['estimated_actuals'] = weather_data_response['estimated_actuals'][0:48]
        for wapi_data in weather_data_response['estimated_actuals']:
            weather_data_dict = dict()
            try:
                time_stamp = datetime.datetime.now()
                wapi_data['period_end'] = parser.parse(wapi_data['period_end'])
            except:
                time_stamp = datetime.datetime.now()
            # define parameters dict
            weather_data_dict['api_source'] = "%s" % API_SOURCE
            weather_data_dict['api_request_type'] = "%s" % RADIATION
            weather_data_dict['city'] = "%s" % city_name
            weather_data_dict['cloud_opacity'] = wapi_data['cloud_opacity']
            weather_data_dict['dhi'] = wapi_data['dhi']
            weather_data_dict['dni'] = wapi_data['dni']
            weather_data_dict['ebh'] = wapi_data['ebh']
            weather_data_dict['ghi'] = wapi_data['ghi']
            weather_data_dict['latitude'] = float(lat_lng.split("&")[1].split("=")[1])
            weather_data_dict['longitude'] = float(lat_lng.split("&")[0].split("=")[1])
            weather_data_dict['prediction_type'] = CURRENT
            weather_data_dict['timestamp_type'] = HOURLY
            weather_data_dict['ts'] = "%s" % wapi_data['period_end'].replace(tzinfo=None)
            weather_data_dict['updated_at'] = "%s" % time_stamp.replace(microsecond=0)
            # close define paratmers dict
            _weather_cassandra_query(session, weather_data_dict)
        print "End _create_radiation_estimated_actuals_data %s!" %city_name
    except Exception as exception:
        print "%s" % exception


def _create_power_forecasts_actual_data(lat_lng, city_name, session, URL, PREDITION_TYPE):
    """

    :param lat_lng_or_city: either lat long or city
    :param splants: solar plant query set
    :return:
    """
    try:
        print "Start _create_power_forecasts_actual_data %s!" % city_name
        lat_lng_capacity = "%s&capacity=%s" %(lat_lng, CAPACITY)
        weather_data_response = _weather_api_call(URL, lat_lng_capacity)
        if 'forecasts' in weather_data_response:
            weather_data_response = weather_data_response['forecasts'][0:48]
        if 'estimated_actuals' in weather_data_response:
            weather_data_response = weather_data_response['estimated_actuals'][0:48]
        if not weather_data_response:
            return
        for wapi_data in weather_data_response:
            weather_data_dict = dict()
            try:
                time_stamp = datetime.datetime.now()
                wapi_data['period_end'] = parser.parse(wapi_data['period_end'])
            except:
                time_stamp = datetime.datetime.now()
            # define parameters dict
            weather_data_dict['api_source'] = "%s" % API_SOURCE
            weather_data_dict['api_request_type'] = "%s" % POWER
            weather_data_dict['city'] = "%s" % city_name
            weather_data_dict['capacity'] = CAPACITY
            weather_data_dict['power'] = wapi_data['pv_estimate']
            weather_data_dict['latitude'] = float(lat_lng.split("&")[1].split("=")[1])
            weather_data_dict['longitude'] = float(lat_lng.split("&")[0].split("=")[1])
            weather_data_dict['prediction_type'] = PREDITION_TYPE
            weather_data_dict['timestamp_type'] = HOURLY
            weather_data_dict['ts'] = "%s" % wapi_data['period_end'].replace(tzinfo=None)
            weather_data_dict['updated_at'] = "%s" % time_stamp.replace(microsecond=0)
            # close define parameters dict
            _weather_cassandra_query(session, weather_data_dict)
        print "End _create_power_forecasts_actual_data %s!" % city_name
    except Exception as exception:
        print "%s" % exception


def _weather_cassandra_query(session, weather_data_dict):
    """

    :param weather_prepare_stmt:
    :param session:
    :param wapi_data:
    :param api_request_type:
    :return:
    """
    if weather_data_dict['api_request_type'] == POWER:
        query = """INSERT INTO weather_data (api_source, api_request_type, capacity, city, 
        latitude, longitude, power, prediction_type, timestamp_type, ts, updated_at) 
        VALUES (%(api_source)s, %(api_request_type)s, %(capacity)s, %(city)s, %(latitude)s, 
        %(longitude)s, %(power)s, %(prediction_type)s, %(timestamp_type)s, 
        %(ts)s, %(updated_at)s)"""
        session.execute(query, weather_data_dict)
    if weather_data_dict['api_request_type'] == RADIATION:
        if weather_data_dict['prediction_type'] == FUTURE:
            query = """INSERT INTO weather_data (air_temp, api_source, api_request_type, 
            azimuth, city, cloud_opacity, dhi, dni, dni_10, dni_90, ebh, ghi, ghi_10, ghi_90, 
            latitude, longitude, prediction_type, timestamp_type, ts, updated_at, zenith) 
            VALUES (%(air_temp)s, %(api_source)s, %(api_request_type)s, %(azimuth)s, %(city)s, 
            %(cloud_opacity)s, %(dhi)s, %(dni)s, %(dni_10)s, %(dni_90)s, %(ebh)s, %(ghi)s, 
            %(ghi_10)s, %(ghi_90)s, %(latitude)s, %(longitude)s, %(prediction_type)s, 
            %(timestamp_type)s, %(ts)s, %(updated_at)s, %(zenith)s)"""
            session.execute(query, weather_data_dict)
        if weather_data_dict['prediction_type'] == CURRENT:
            query = """INSERT INTO weather_data (api_source, api_request_type, city, cloud_opacity,
            dhi, dni, ebh, ghi, latitude, longitude, prediction_type, timestamp_type, ts, updated_at) 
            VALUES (%(api_source)s, %(api_request_type)s, %(city)s, %(cloud_opacity)s, 
            %(dhi)s, %(dni)s, %(ebh)s, %(ghi)s, %(latitude)s, %(longitude)s, %(prediction_type)s, 
            %(timestamp_type)s, %(ts)s, %(updated_at)s)"""
            session.execute(query, weather_data_dict)


print "start %s" % datetime.datetime.now()
start_time = time.time()
print "start_time %s" % start_time
cron_collect_solcast_weather_data_main()
end_time = time.time()
print "end_time %s" % end_time 
print "total_time %s" % (end_time - start_time)
print "end %s" % datetime.datetime.now()
