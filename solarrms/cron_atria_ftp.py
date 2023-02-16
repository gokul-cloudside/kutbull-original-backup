import ftplib
import collections
import json
import pytz
from django.utils import timezone
from cStringIO import StringIO
from datetime import datetime, timedelta
from dataglen.models import ValidDataStorageByStream
from solarrms.models import PerformanceRatioTable, SolarPlant
from solarrms.solarutils import get_plant_power
from django.conf import settings

FTP_HOST = "wind3.50hertz.in" # ftp host
FTP_USER = "atria" # ftp user
FTP_PASSWORD = "#t235$YZm81Q" # ftp password
FTP_PORT = 21 # ftp port
PLANT_SLUG = "pavagada" # solarplant slug
FTP_DIRECTORY = "/SOLAR/KA/AT_RYPT/" # ftp directory
DATA_TIME_INTERVAL = 15 # fetch data of every 15 min and find mean of the values
BUFFER_TIME = 5 # buffer to fetch data before 5 mins

# Proper headers for csv file
CSV_HEADERS = {'timestamp': 'Time Stamp',
               'ghi': 'GHI (Watt/square m)',
               'poa': 'POA (Watt/square m)',
               'ambient_temperature': 'Ambient Temperature (Deg C)',
               'module_temperature': 'Module/Surface Temperature (Deg C)',
               'windspeed': 'Wind Speed (m/s)',
               'total_meter_power': 'Total Power (kW) (Metered Power)',
               'inverter_wise_power_ac': 'Inverter wise power (AC) (kW)',
               'inverter_wise_power_dc': 'Inverter wise power (DC) (kW)',
               'performance_ratio':'Performance Ratio'}


def delete_line_break_space(original_string):
    modified_string = original_string.replace('\n', '').replace('\r', '')
    return modified_string


class FtpBufferWriter():
    """
        Read FTP File data to a varibale so we can save it to same file
    """
    def __init__(self):
        self.ftp_file_data = ''

    def __call__(self, lines):
        self.ftp_file_data += delete_line_break_space(lines)


def _get_plant_data(ts):
    """
    get all data here
    :param ts: timestamp
    :return:
    """
    splant = SolarPlant.objects.get(slug=PLANT_SLUG)
    source_key = splant.metadata.sourceKey
    # if cron run at 10:05 it will bring data of 09:50 to 10:00
    ts = ts-timedelta(minutes=BUFFER_TIME)
    all_inverter = splant.independent_inverter_units.all().filter(isActive=True).\
        values('sourceKey', 'timeoutInterval', 'name')
    response_data = collections.OrderedDict()
    response_data_string = ""
    response_data['timestamp'] = ts.strftime("%d-%m-%Y %H:%M:%S")
    response_data['ghi'] = "" # stream_name=EXTERNAL_IRRADIATION
    response_data['poa'] = ""
    response_data['ambient_temperature'] = ""  # stream_name=AMBIENT_TEMPERATURE
    response_data['module_temperature'] = ""  # stream_name=MODULE_TEMPERATURE
    response_data['windspeed'] = ""  # stream_name=WINDSPEED
    response_data['total_meter_power'] = "" #  if meter then stream_name = WATT_TOTAL else stream_name = ACTIVE_POWER
    response_data['performance_ratio'] = ""  # stream_name=PR

    # START AMBIENT TEMPERATURE DATA
    try:
        ambient_temperature = ValidDataStorageByStream.objects.filter(source_key=source_key,
                                                                      stream_name='AMBIENT_TEMPERATURE',
                                                                      timestamp_in_data__lte=ts,
                                                                      timestamp_in_data__gte=ts - timedelta(
                                                                          minutes=DATA_TIME_INTERVAL))
        ambient_temperature_count = 0
        ambient_temperature_value = 0
        for at in ambient_temperature:
            ambient_temperature_value += float(at.stream_value)
            ambient_temperature_count += 1
        if ambient_temperature_count > 0:
            response_data['ambient_temperature'] = "%s" % (ambient_temperature_value / ambient_temperature_count)
    except Exception as exception:
        print "fail to fetch ambient temperature %s" % exception
    # END AMBIENT TEMPERATURE DATA

    # START MODULE TEMPERATURE DATA
    try:
        module_temperature = ValidDataStorageByStream.objects.filter(source_key=source_key,
                                                                      stream_name='MODULE_TEMPERATURE',
                                                                      timestamp_in_data__lte=ts,
                                                                      timestamp_in_data__gte=ts - timedelta(
                                                                          minutes=DATA_TIME_INTERVAL))
        module_temperature_count = 0
        module_temperature_value = 0
        for mt in module_temperature:
            module_temperature_value += float(mt.stream_value)
            module_temperature_count += 1
        if module_temperature_count > 0:
            response_data['module_temperature'] = "%s" % (module_temperature_value/module_temperature_count)
    except Exception as exception:
        print "fail to fetch module temperature %s" % exception
    # END MODULE TEMPERATURE DATA

    # START WINDSPEED DATA
    try:
        windspeed = ValidDataStorageByStream.objects.filter(source_key=source_key,
                                                                     stream_name='WINDSPEED',
                                                                     timestamp_in_data__lte=ts,
                                                                     timestamp_in_data__gte=ts - timedelta(
                                                                         minutes=DATA_TIME_INTERVAL))
        windspeed_count = 0
        windspeed_value = 0
        for wd in windspeed:
            windspeed_value += float(wd.stream_value)
            windspeed_count += 1
        if windspeed_count > 0:
            response_data['windspeed'] = "%s" % (windspeed_value/windspeed_count)
    except Exception as exception:
        print "fail to fetch windspeed %s" % exception
    # END WINDSPEED DATA

    # START GHI DATA
    try:
        ghi = ValidDataStorageByStream.objects.filter(source_key=source_key,
                                                        stream_name='IRRADIATION',
                                                        timestamp_in_data__lte=ts,
                                                        timestamp_in_data__gte=ts - timedelta(
                                                            minutes=DATA_TIME_INTERVAL))
        ghi_count = 0
        ghi_value = 0
        for gh in ghi:
            ghi_value += float(gh.stream_value)
            ghi_count += 1
        if ghi_count > 0:
            ghi_in_watt = (ghi_value/ghi_count) * 1000
            response_data['ghi'] = "%s" % (ghi_in_watt)

    except Exception as exception:
        print "fail to fetch GHI %s" % exception
    # END GHI DATA

    # START POA DATA
    try:
        poa = ValidDataStorageByStream.objects.filter(source_key=source_key,
                                                        stream_name='EXTERNAL_IRRADIATION',
                                                        timestamp_in_data__lte=ts,
                                                        timestamp_in_data__gte=ts - timedelta(
                                                            minutes=DATA_TIME_INTERVAL))
        poa_count = 0
        poa_value = 0
        for po in poa:
            poa_value += float(po.stream_value)
            poa_count += 1
        if poa_count > 0:
            poa_in_watt = (poa_value / poa_count) * 1000
            response_data['poa'] = "%s" % (poa_in_watt)
    except Exception as exception:
        print "fail to fetch POA %s" % exception
    # END POA DATA

    # START POWER DATA
    meter_counts = 0
    try:
        active_meters = splant.energy_meters.all().filter(energy_calculation=True)
        meter_counts = len(active_meters)
        total_meter_power_value = 0
        total_meter_power_count = 0
        for meter in active_meters:
            active_meter_power = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                         stream_name='WATT_TOTAL',
                                                                         timestamp_in_data__gte=ts - timedelta(
                                                                             minutes=DATA_TIME_INTERVAL),
                                                                         timestamp_in_data__lte=ts)
            active_meter_power_count = 0
            active_meter_power_value = 0
            for amp in active_meter_power:
                active_meter_power_value += float(amp.stream_value)
                active_meter_power_count += 1
            if active_meter_power_count > 0:
                total_meter_power_value = (active_meter_power_value/active_meter_power_count)
            total_meter_power_count += 1
            total_meter_power_value += total_meter_power_value
        if total_meter_power_count > 0:
            response_data['total_meter_power'] = "%s" % (total_meter_power_value)
    except Exception as exception:
        print "fail to calculate power %s" % exception
    # END POWER DATA

    # START PR DATA
    try:
        ts_pr = ts.astimezone(pytz.timezone(splant.metadata.plantmetasource.dataTimezone))
        daily_performance_ratio = PerformanceRatioTable.objects.filter(
            timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
            count_time_period=settings.DATA_COUNT_PERIODS.DAILY, identifier=source_key,
            ts=ts_pr.replace(hour=0, minute=0, second=0, microsecond=0)).limit(1)
        if daily_performance_ratio:
            response_data['performance_ratio'] = "%s" % daily_performance_ratio[0].performance_ratio
    except Exception as exception:
        print "fail to fetch PR %s" % exception
    # END PR DATA

    # START INVERTER DATA
    total_all_inverter_power = 0
    for inverter_ac in all_inverter:
        try:
            active_power = ValidDataStorageByStream.objects.filter(source_key=inverter_ac['sourceKey'],
                                                                   stream_name='ACTIVE_POWER',
                                                                   timestamp_in_data__gte=ts - timedelta(
                                                                       minutes=DATA_TIME_INTERVAL),
                                                                   timestamp_in_data__lte=ts)
            active_power_count = 0
            active_power_value = 0
            active_power_stream_value = 0
            for acp in active_power:
                active_power_value += float(acp.stream_value)
                active_power_count += 1
            inverter_ac_name = "%s_AC" % delete_line_break_space(inverter_ac['name'].replace(" ", "_"))
            response_data[inverter_ac_name] = ""
            if active_power_count > 0:
                active_power_stream_value = (active_power_value / active_power_count)
                response_data[inverter_ac_name] = "%s" % (active_power_stream_value)
            total_all_inverter_power += active_power_stream_value

        except Exception as exception:
            print "not able to fetch active_power %s" % exception
    # END INVERTER DATA

    # if no meter take value from inveter
    if meter_counts == 0:
        response_data['total_meter_power'] = total_all_inverter_power

    for inverter_dc in all_inverter:
        try:
            dc_power = ValidDataStorageByStream.objects.filter(source_key=inverter_dc['sourceKey'],
                                                               stream_name='DC_POWER',
                                                               timestamp_in_data__gte=ts - timedelta(
                                                                   minutes=DATA_TIME_INTERVAL),
                                                               timestamp_in_data__lte=ts)
            dc_power_count = 0
            dc_power_value = 0
            dc_power_stream_value = 0
            for dcp in dc_power:
                dc_power_value += float(dcp.stream_value)
                dc_power_count += 1
            inverter_dc_name = "%s_DC" % delete_line_break_space(inverter_dc['name'].replace(" ", "_"))
            response_data[inverter_dc_name] = ""
            if dc_power_count > 0:
                dc_power_stream_value = (dc_power_value / dc_power_count)
                response_data[inverter_dc_name] = "%s" % (dc_power_stream_value)
        except Exception as exception:
            print "not able to fetch dc_power %s" % exception
    # END INVERTER DATA

    #check if all are empty
    """empty_check = False
    if float(response_data['ghi']) == 0 and float(response_data['poa']) == 0 and float(
            response_data['ambient_temperature']) == 0 and float(response_data['module_temperature']) == 0 and float(
            response_data['windspeed']) == 0 and float(response_data['total_meter_power']) == 0 and float(
            response_data['performance_ratio']) == 0:
        print "gui, ambient & module temperature, windspeed, total_meter_power and pr is empty %s" \
              %response_data['timestamp']
        empty_check = True
        return None, None, empty_check"""
    for resp_data in response_data:
        response_data_string += "%s;" % (response_data["%s" % resp_data])
    header_values = ';'.join(
        CSV_HEADERS.get(response_data_key, response_data_key) for response_data_key in response_data)
    return response_data_string[0:len(response_data_string)-1], header_values


def _check_ftp_connection():
    print "start _check_ftp_connection"
    ftp_session = ftplib.FTP()
    ftp_session.connect(FTP_HOST, FTP_PORT)
    print "%s" %ftp_session.getwelcome()
    try:
        print "login with credential"
        ftp_session.login(FTP_USER, FTP_PASSWORD)
    except Exception as exception:
        print "credential are wrong %s" % exception
    print "end _check_ftp_connection"
    return ftp_session


def _create_or_update_weather_data_over_ftp_server(current_time, file_name):
    response_data_string, response_data_header = _get_plant_data(current_time)
    current_date = current_time.date()
    current_date_string = current_date.strftime("%d-%m-%Y")
    yesterday_date_string = (current_date - timedelta(1)).strftime("%d-%m-%Y")
    tomorrow_date_string = (current_date + timedelta(1)).strftime("%d-%m-%Y")
    ftp_session = _check_ftp_connection()
    fbr = FtpBufferWriter()
    try:
        ftp_session.retrbinary('RETR %s/%s.csv' % (FTP_DIRECTORY,file_name), fbr)
    except Exception as exception:
        print "current_date new file will be created"
    modified_string = ""
    if len(fbr.ftp_file_data) > 0:
        modified_string = "%s%s" % (fbr.ftp_file_data, response_data_string)
    else:
        modified_string = "%s%s" % (response_data_header, response_data_string)
    del fbr
    #todays data \n append
    modified_string = modified_string.replace(current_date_string, "\n%s" % current_date_string)
    # tommorrow data \n append
    modified_string = modified_string.replace(tomorrow_date_string, "\n%s" % tomorrow_date_string)
    #yesterday data \n append
    modified_string = modified_string.replace(yesterday_date_string, "\n%s" % yesterday_date_string)
    response_data_string_io = StringIO(modified_string)
    del modified_string
    ftp_session.storbinary('STOR %s/%s.csv' % (FTP_DIRECTORY,file_name), response_data_string_io)
    ftp_session.quit()


def ftp_cron_for_current_time_main():
    """
    used by cron to upload data to ftp
    :return:
    """
    print "start ftp_cron_for_current_time_main"
    current_time = timezone.now()
    current_date = current_time.date()
    _create_or_update_weather_data_over_ftp_server(current_time, "%s" % current_date)
    print "end ftp_cron_for_current_time_main"


def ftp_cron_between_time_interval_main(startdatetime, enddatetime):
    """
    generate csv on ftp between two timestamp
    :param startdatetime: datetime with YYYY-MM-DD HH-MM-SS formate start it
    :param enddatetime: datetime with YYYY-MM-DD HH-MM-SS formate
    :return:
    """
    print "start ftp_cron_between_time_interval_main"
    file_name = "%s_to_%s" % (startdatetime, enddatetime)
    try:
        startdatetime = pytz.utc.localize(datetime.strptime(startdatetime, "%Y-%m-%d %H:%M:%S"))
        enddatetime = pytz.utc.localize(datetime.strptime(enddatetime, "%Y-%m-%d %H:%M:%S"))
    except Exception as exc:
        print "specify datetime in %Y-%m-%d %H:%M:%S format %s" %exc
        return
    while startdatetime <= enddatetime:
        _create_or_update_weather_data_over_ftp_server(startdatetime, file_name)
        startdatetime = startdatetime + timedelta(minutes=DATA_TIME_INTERVAL)
        print "startdatetime %s " % startdatetime
    print "end ftp_cron_between_time_interval_main"
