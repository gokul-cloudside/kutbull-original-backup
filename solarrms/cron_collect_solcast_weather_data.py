import json
import requests
import time
import datetime
from dateutil import parser
from solarrms.models import SolarPlant, WeatherData
from django.utils import timezone
import pytz

SOLCAST_FORECAST_API_URL = "https://api.solcast.com.au/radiation/forecasts"
SOLCAST_ACTUAL_API_URL = "https://api.solcast.com.au/radiation/estimated_actuals"
SOLCAST_API_KEY = "SbSKXDQoYkMomBV3BVjM64SSGltbccYX"


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
    solar_plants = SolarPlant.objects.all()
    for splants in solar_plants:
        lat_lng_or_city = "longitude=%s&latitude=%s" % (splants.longitude, splants.latitude)
        if not lat_lng_or_city:
            continue
        # 1 for hourly data for current and future
        _create_radiation_forecasts_data(lat_lng_or_city, splants)
        # 24 for daily data for current and future
        _create_radiation_estimated_actuals_data(lat_lng_or_city, splants)
    print "End collecting weather data main!"


def _create_radiation_forecasts_data(lat_lng_or_city, splants):
    """

    :param lat_lng_or_city: either lat long or city
    :param splants: solar plant query set
    :return:
    """
    try:
        print("Start _create_weather_data_hourly_or_daily %s!" %splants)
        weather_data_response = _weather_api_call(SOLCAST_FORECAST_API_URL, lat_lng_or_city)
        if 'forecasts' not in weather_data_response:
            return
        tz = pytz.timezone(splants.metadata.plantmetasource.dataTimezone)
        weather_data_response['forecasts'] = weather_data_response['forecasts'][0:48]
        for wapi_data in weather_data_response['forecasts']:
            try:
                time_stamp = timezone.now()
                time_stamp = time_stamp.astimezone(tz)
                wapi_data['period_end'] = parser.parse(wapi_data['period_end'])
            except:
                time_stamp = timezone.now()
            WeatherData.objects.create(api_source='solcast',
                                       timestamp_type=WeatherData.HOURLY,
                                       identifier=splants.slug,
                                       ts=wapi_data['period_end'],
                                       city=splants.openweather,
                                       latitude=splants.latitude,
                                       longitude=splants.longitude,
                                       cloudcover=wapi_data['cloud_opacity'],
                                       air_temp=wapi_data['air_temp'],
                                       ghi=wapi_data['ghi'],
                                       ghi_10=wapi_data['ghi10'],
                                       ghi_90=wapi_data['ghi90'],
                                       dni=wapi_data['dni'],
                                       dni_10=wapi_data['dni10'],
                                       dni_90=wapi_data['dni90'],
                                       dhi=wapi_data['dhi'],
                                       prediction_type=WeatherData.FUTURE,
                                       updated_at=time_stamp)

        print "End _create_weather_data_hourly_or_daily %s!" % splants
    except Exception as exception:
        print "%s" % exception


def _create_radiation_estimated_actuals_data(lat_lng_or_city, splants):
    """

    :param lat_lng_or_city: either lat long or city
    :param splants: solar plant query set
    :return:
    """
    try:
        print "Start _create_radiation_estimated_actuals_data %s!" % splants
        weather_data_response = _weather_api_call(SOLCAST_ACTUAL_API_URL, lat_lng_or_city)
        if 'estimated_actuals' not in weather_data_response:
            return
        tz = pytz.timezone(splants.metadata.plantmetasource.dataTimezone)
        weather_data_response['estimated_actuals'] = weather_data_response['estimated_actuals'][0:48]
        for wapi_data in weather_data_response['estimated_actuals'][0:48]:
            try:
                time_stamp = timezone.now()
                time_stamp = time_stamp.astimezone(tz)
                wapi_data['period_end'] = parser.parse(wapi_data['period_end'])
            except:
                time_stamp = timezone.now()
            WeatherData.objects.create(api_source='solcast',
                                       timestamp_type=WeatherData.HOURLY,
                                       identifier=splants.slug,
                                       ts=wapi_data['period_end'],
                                       city=splants.openweather,
                                       latitude=splants.latitude,
                                       longitude=splants.longitude,
                                       cloudcover=wapi_data['cloud_opacity'],
                                       ghi=wapi_data['ghi'],
                                       dni=wapi_data['dni'],
                                       dhi=wapi_data['dhi'],
                                       prediction_type=WeatherData.CURRENT,
                                       updated_at=time_stamp)

        print "End _create_radiation_estimated_actuals_data %s!" %splants
    except Exception as exception:
        print "%s" % exception
