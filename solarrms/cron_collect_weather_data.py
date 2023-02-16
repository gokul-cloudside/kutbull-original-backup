import json
import requests
import time
import datetime
from solarrms.models import SolarPlant, WeatherData
from django.utils import timezone
import pytz

WORLD_WEATHER_API = "https://api.worldweatheronline.com/premium/v1/weather.ashx"
WORLD_WEATHER_API_KEY = "39217aee72de46088c4145902170302"
HOURLY_DATA = 1
DAILY_DATA = 24

def _weather_api_call(query_parameter, timestamp_type=1):
    """

    :param query_parameter: either city name or lat long as q
    :param timestamp_type: specify hourly or daily data
    :return:
    """
    response_json = None
    url = "%s?key=%s&q=%s&num_of_days=2&tp=%s&format=json" % (
        WORLD_WEATHER_API, WORLD_WEATHER_API_KEY, query_parameter, timestamp_type)
    #print url
    try:
        response = requests.get(url)
        response_json = json.loads(response.content)
    except Exception as es:
        print(str(es))
    # per second call
    time.sleep(1)
    return response_json


def cron_collect_weather_data_main():
    """

    :return: cron to collect data from world weather and save on daily and hourly bases
    """
    print("Start collecting weather data main!")
    solar_plants = SolarPlant.objects.all()
    for splants in solar_plants:
        lat_lng_or_city = "%s,%s" % (splants.latitude, splants.longitude)
        if not lat_lng_or_city:
            continue
        # 1 for hourly data for current and future
        _create_weather_data_hourly_or_daily(lat_lng_or_city, splants, HOURLY_DATA)
        # 24 for daily data for current and future
        _create_weather_data_hourly_or_daily(lat_lng_or_city, splants, DAILY_DATA)
    print("End collecting weather data main!")


def _create_weather_data_hourly_or_daily(lat_lng_or_city, splants, timestamp_type=1):
    """

    :param lat_lng_or_city: either lat long or city
    :param splants: solar plant query set
    :param hourly_data: for which hour
    :return:
    """
    try:
        print("Start _create_weather_data_hourly_or_daily %s!" %timestamp_type)
        weather_data_response = _weather_api_call(lat_lng_or_city, timestamp_type=timestamp_type)
        if 'weather' not in weather_data_response['data']:
            return
        prediction_type = WeatherData.CURRENT
        timestamp_type_text = WeatherData.DAILY if timestamp_type == DAILY_DATA else WeatherData.HOURLY
        for wapi_data in weather_data_response['data']['weather']:
            wapi_sunrise = "%s %s" % (wapi_data['date'], wapi_data['astronomy'][0]['sunrise'])
            wapi_sunrise = datetime.datetime.strptime(wapi_sunrise, "%Y-%m-%d %I:%M %p")
            wapi_sunset = "%s %s" % (wapi_data['date'], wapi_data['astronomy'][0]['sunset'])
            wapi_sunset = datetime.datetime.strptime(wapi_sunset, "%Y-%m-%d %I:%M %p")
            try:
                tz = pytz.timezone(splants.metadata.plantmetasource.dataTimezone)
                wapi_sunrise = tz.localize(wapi_sunrise)
                wapi_sunrise = wapi_sunrise.astimezone(tz)
                wapi_sunset = tz.localize(wapi_sunset)
                wapi_sunset = wapi_sunset.astimezone(tz)
            except Exception as exception:
                print str(exception)
                tz = pytz.timezone(splants.metadata.plantmetasource.dataTimezone)
            for wapi_data_hourly in wapi_data['hourly']:
                try:
                    time_stamp = timezone.now()
                    time_stamp = time_stamp.astimezone(tz)
                    per_hours = "%s 00:00:00" % (wapi_data['date'])
                    if timestamp_type_text == WeatherData.HOURLY and int(wapi_data_hourly['time']) > 0:
                        hourly = "%02d" %(int(wapi_data_hourly['time'])/100)
                        per_hours = "%s %s:00:00" % (wapi_data['date'], hourly)
                    per_hours = datetime.datetime.strptime(per_hours, "%Y-%m-%d %H:%M:%S")
                    per_hours = tz.localize(per_hours)
                    per_hours = per_hours.astimezone(tz)
                except Exception as exception:
                    print str(exception)
                    time_stamp = timezone.now()
                WeatherData.objects.create(api_source='world-weather',
                                           timestamp_type=timestamp_type_text,
                                           identifier=splants.slug,
                                           ts=per_hours,
                                           city=splants.openweather,
                                           latitude=splants.latitude,
                                           longitude=splants.longitude,
                                           sunrise=wapi_sunrise,
                                           sunset=wapi_sunset,
                                           cloudcover=wapi_data_hourly['cloudcover'],
                                           humidity=wapi_data_hourly['humidity'],
                                           windspeed=wapi_data_hourly['windspeedKmph'],
                                           precipMM=wapi_data_hourly['precipMM'],
                                           prediction_type=prediction_type,
                                           updated_at=time_stamp,
                                           chanceofrain=wapi_data_hourly['chanceofrain'])
            # changing because it will bring data for next day
            prediction_type = WeatherData.FUTURE
        print("End _create_weather_data_hourly_or_daily %s!" %timestamp_type)
    except Exception as exception:
        print(str(exception))