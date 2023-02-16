import json
import requests
import time
import datetime
from solarrms.models import SolarPlant, WeatherData
from django.utils import timezone
import pytz

DARK_SKY_API = "https://api.darksky.net/forecast/"
DARK_SKY_API_KEY = "22b2628f78f326586363d42e60eab949"

def _weather_api_call(query_parameter):
    """

    :param query_parameter: either city name or lat long as q
    :return:
    """
    response_json = None
    url = "%s%s/%s?exclude=currently,flags" % (DARK_SKY_API, DARK_SKY_API_KEY, query_parameter)
    print url
    try:
        response = requests.get(url)
        response_json = json.loads(response.content)
    except Exception as es:
        print "%s" % es
    # per second call
    time.sleep(1)
    return response_json


def cron_collect_darksky_weather_data_main():
    """

    :return: cron to collect data from world weather and save on daily and hourly bases
    """
    print("Start collecting weather data main!")
    current_date = datetime.datetime.now().date()
    current_time = current_date.strftime("%s")
    tomorrow_date = current_date + datetime.timedelta(days=1)
    tomorrow_time = tomorrow_date.strftime("%s")
    solar_plants = SolarPlant.objects.all()
    for splants in solar_plants:
        lat_lng_or_city = "%s,%s" % (splants.latitude, splants.longitude)
        if not lat_lng_or_city:
            continue
        #current datetime values
        prediction_type = WeatherData.CURRENT
        _create_weather_data_hourly_or_daily(lat_lng_or_city, current_time, splants, prediction_type)
        # tomorrow datetime values
        prediction_type = WeatherData.FUTURE
        _create_weather_data_hourly_or_daily(lat_lng_or_city, tomorrow_time, splants, prediction_type)
    print("End collecting weather data main!")


def _create_weather_data_hourly_or_daily(lat_lng_or_city, current_time, splants, prediction_type):
    """

    :param lat_lng_or_city: either lat long or city
    :param splants: solar plant query set
    :return:
    """
    try:
        print "Start _create_weather_data_hourly_or_daily %s!" % splants
        weather_data_response = _weather_api_call("%s,%s" % (lat_lng_or_city, current_time))
        splant_data = dict()
        splant_data['identifier'] = splants.slug
        splant_data['openweather'] = splants.openweather
        splant_data['latitude'] = splants.latitude
        splant_data['longitude'] = splants.longitude
        splant_data['timestamp_type_text'] = WeatherData.DAILY
        splant_data['sunrise'] = ""
        splant_data['sunset'] = ""
        tz = pytz.timezone(splants.metadata.plantmetasource.dataTimezone)
        if not tz:
            tz = pytz.timezone("UTC")

        # save daily weather data
        if 'daily' in weather_data_response:
            for wapi_data in weather_data_response['daily']['data']:
                weather_data_dict = dict()
                try:
                    # sunrise and sunset timezone convertion
                    splant_data['sunrise'] = datetime.datetime.fromtimestamp(int(wapi_data['sunriseTime']))
                    #splant_data['sunrise'] = tz.localize(splant_data['sunrise'])
                    #splant_data['sunrise'] = splant_data['sunrise'].astimezone(tz)
                    splant_data['sunset'] = datetime.datetime.fromtimestamp(int(wapi_data['sunsetTime']))
                    #splant_data['sunset'] = tz.localize(splant_data['sunset'])
                    #splant_data['sunset'] = splant_data['sunset'].astimezone(tz)
                    # ts convertion
                    weather_data_dict['ts'] = datetime.datetime.fromtimestamp(int(wapi_data['time']))
                    #weather_data_dict['ts'] = tz.localize(weather_data_dict['ts'])
                    #weather_data_dict['ts'] = weather_data_dict['ts'].astimezone(tz)
                    #current time stamp
                    weather_data_dict['time_stamp'] = timezone.now()
                    #weather_data_dict['time_stamp'] = weather_data_dict['time_stamp'].astimezone(tz)
                except Exception as exception:
                    print "%s" % exception

                weather_data_dict['cloudcover'] = wapi_data['cloudCover']
                weather_data_dict['humidity'] = wapi_data['humidity']
                weather_data_dict['windspeedKmph'] = wapi_data['windSpeed']
                weather_data_dict['precipMM'] = wapi_data['precipProbability']
                weather_data_dict['prediction_type'] = prediction_type
                _write_data_to_weatherdata_table(splant_data, weather_data_dict)

        print "%s" % splant_data
        splant_data['timestamp_type_text'] = WeatherData.HOURLY
        # save daily weather data
        if 'hourly' in weather_data_response:
            for wapi_data in weather_data_response['hourly']['data']:
                weather_data_dict = dict()
                try:
                    # ts convertion
                    weather_data_dict['ts'] = datetime.datetime.fromtimestamp(int(wapi_data['time']))
                    #weather_data_dict['ts'] = tz.localize(weather_data_dict['ts'])
                    #weather_data_dict['ts'] = weather_data_dict['ts'].astimezone(tz)

                    #current time stamp
                    weather_data_dict['time_stamp'] = timezone.now()
                    #weather_data_dict['time_stamp'] = weather_data_dict['time_stamp'].astimezone(tz)

                except Exception as exception:
                    print "%s" % exception

                weather_data_dict['cloudcover'] = wapi_data['cloudCover']
                weather_data_dict['humidity'] = wapi_data['humidity']
                weather_data_dict['windspeedKmph'] = wapi_data['windSpeed']
                weather_data_dict['precipMM'] = wapi_data['precipProbability']
                weather_data_dict['prediction_type'] = prediction_type
                _write_data_to_weatherdata_table(splant_data, weather_data_dict)

    except Exception as exception:
        print "%s" % exception


def _write_data_to_weatherdata_table(splant_data, weather_data_dict):
    """

    :param splant_data:
    :param weather_data_dict:
    :return:
    """
    print "%s" % weather_data_dict
    WeatherData.objects.create(api_source='darksky',
                               timestamp_type=splant_data['timestamp_type_text'],
                               identifier=splant_data['identifier'],
                               ts=weather_data_dict['ts'],
                               city=splant_data['openweather'],
                               latitude=splant_data['latitude'],
                               longitude=splant_data['longitude'],
                               sunrise=splant_data['sunrise'],
                               sunset=splant_data['sunset'],
                               cloudcover=weather_data_dict['cloudcover'],
                               humidity=weather_data_dict['humidity'],
                               windspeed=weather_data_dict['windspeedKmph'],
                               precipMM=weather_data_dict['precipMM'],
                               prediction_type=weather_data_dict['prediction_type'],
                               updated_at=weather_data_dict['time_stamp'])