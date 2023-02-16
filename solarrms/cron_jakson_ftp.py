import ftplib
import collections
import pytz
from django.utils import timezone
from cStringIO import StringIO
from datetime import datetime, timedelta
from dataglen.models import ValidDataStorageByStream
from solarrms.models import SolarPlant
from solarrms.solarutils import get_minutes_aggregated_energy

#FTP_HOST = "data.reconnectenergy.com" # ftp host
FTP_HOST = "52.41.144.51" # ftp host
#FTP_USER = "bap_jakson" # ftp user
FTP_USER = "bap_jodhpur" # ftp user
#FTP_PASSWORD = "solar@bap9" # ftp password
FTP_PASSWORD = "admin123" # ftp password
FTP_PORT = 21 # ftp port
#PLANT_SLUG = ["jppl1", "jppl2"] # solarplant slug
PLANT_SLUG = ["ioclkadapa3mwp"] # solarplant slug
#FTP_DIRECTORY = "/BapJakson/Historical_Data/" # ftp directory
FTP_DIRECTORY = "/Kadapa/" # ftp directory
DATA_TIME_INTERVAL = 15 # fetch data of every 15 min and find mean of the values
BUFFER_TIME = 5 # buffer to fetch data before 5 mins
GET_POWER_FROM_INVERTER = False # set to true if you want to consider power from inverter

# Proper headers for csv file
CSV_HEADERS = {'timestamp': 'Time Stamp',
               'total_meter_power': 'Total Power (kW)',
               #'grid_connectivity': 'Grid Connectivity (sec)',
               'ambient_temperature': 'Ambient Temperature (Deg C)',
               'ghi': 'Solar Insolation (Watt/square m)',
               'module_temperature': 'Module Temperature (Deg C)',
               'plant_energy': 'Plant Energy (kWh)'}


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


def _get_plant_data(ts, splant):
    """
    get all data here
    :param ts: timestamp
    :return:
    """
    source_key = splant.metadata.sourceKey
    # if cron run at 10:05 it will bring data of 09:45 to 10:00
    ts = ts-timedelta(minutes=BUFFER_TIME)
    all_inverter = splant.independent_inverter_units.all().filter(isActive=True).\
        values('sourceKey', 'timeoutInterval', 'name')
    response_data = collections.OrderedDict()
    response_data_string = ""
    response_data['timestamp'] = ts.strftime("%d-%m-%Y %H:%M:%S")
    response_data['total_meter_power'] = "NA"  # if meter then stream_name = WATT_TOTAL else stream_name = ACTIVE_POWER
    #response_data['grid_connectivity'] = "NA"  # PlantDownTime
    response_data['ambient_temperature'] = "NA"  # stream_name=AMBIENT_TEMPERATURE
    response_data['ghi'] = "NA"  # stream_name=IRRADIATION
    response_data['module_temperature'] = "NA"  # stream_name=MODULE_TEMPERATURE
    response_data['plant_energy'] = "NA"  # not stream


    # START AMBIENT TEMPERATURE DATA
    try:
        ambient_temperature = ValidDataStorageByStream.objects.filter(source_key=source_key,
                                                                      stream_name='AMBIENT_TEMPERATURE',
                                                                      timestamp_in_data__lte=ts,
                                                                      timestamp_in_data__gt=ts - timedelta(
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
                                                                      timestamp_in_data__gt=ts - timedelta(
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

    # START GHI DATA
    try:
        ghi = ValidDataStorageByStream.objects.filter(source_key=source_key,
                                                        stream_name='IRRADIATION',
                                                        timestamp_in_data__lte=ts,
                                                        timestamp_in_data__gt=ts - timedelta(
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
                                                                         timestamp_in_data__gt=ts - timedelta(
                                                                             minutes=DATA_TIME_INTERVAL),
                                                                         timestamp_in_data__lte=ts)
            active_meter_power_count = 0
            active_meter_power_value = 0
            total_single_meter_power = 0
            for amp in active_meter_power:
                active_meter_power_value += float(amp.stream_value)
                active_meter_power_count += 1
            if active_meter_power_count > 0:
                total_single_meter_power = (active_meter_power_value/active_meter_power_count)
            total_meter_power_count += 1
            total_meter_power_value += total_single_meter_power
        if total_meter_power_count > 0:
            response_data['total_meter_power'] = "%s" % (total_meter_power_value)
    except Exception as exception:
        print "fail to calculate power %s" % exception
    # END POWER DATA

    # START INVERTER DATA
    total_all_inverter_power = 0

    # if no meter take value from inverter
    if GET_POWER_FROM_INVERTER and meter_counts > 0:
        for inverter_ac in all_inverter:
            try:
                active_power = ValidDataStorageByStream.objects.filter(source_key=inverter_ac['sourceKey'],
                                                                       stream_name='ACTIVE_POWER',
                                                                       timestamp_in_data__gt=ts - timedelta(
                                                                           minutes=DATA_TIME_INTERVAL),
                                                                       timestamp_in_data__lte=ts)
                active_power_count = 0
                active_power_value = 0
                active_power_stream_value = 0
                for acp in active_power:
                    active_power_value += float(acp.stream_value)
                    active_power_count += 1
                if active_power_count > 0:
                    active_power_stream_value = (active_power_value / active_power_count)
                total_all_inverter_power += active_power_stream_value

            except Exception as exception:
                print "not able to fetch active_power %s" % exception

        response_data['total_meter_power'] = total_all_inverter_power
    # END INVERTER DATA

    # START PLANT ENERGY
    try:
        start_time = ts.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = ts
        plant_energy = get_minutes_aggregated_energy(start_time, end_time, splant, "DAY", 1)
        response_data['plant_energy'] = plant_energy[0]['energy']
    except Exception as exception:
        print "not able to fetch plant_energy %s" % exception
    # END PLANT ENERGY

    for resp_data in response_data:
        response_data_string += "%s;" % (response_data["%s" % resp_data])
    header_values = ';'.join(
        CSV_HEADERS.get(response_data_key, response_data_key) for response_data_key in response_data)
    return response_data_string[0:len(response_data_string)-1], header_values


def _check_ftp_connection():
    """

    :return:
    """
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


def _create_or_update_weather_data_over_ftp_server(current_time, file_name, plant):
    """

    :param current_time:
    :param file_name:
    :return:
    """
    response_data_string, response_data_header = _get_plant_data(current_time, plant)
    current_date = current_time.date()
    current_date_string = current_date.strftime("%d-%m-%Y")
    yesterday_date_string = (current_date - timedelta(1)).strftime("%d-%m-%Y")
    tomorrow_date_string = (current_date + timedelta(1)).strftime("%d-%m-%Y")
    ftp_session = _check_ftp_connection()
    fbr = FtpBufferWriter()
    try:
        ftp_session.retrbinary('RETR %s/%s.csv' % (FTP_DIRECTORY, file_name), fbr)
    except Exception as exception:
        print "current_date new file will be created %s" % exception
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
    current_date = current_time.date().strftime("%d_%m_%Y")
    splants = SolarPlant.objects.filter(slug__in=PLANT_SLUG)
    for plant in splants:
        file_name = "%s_%s" % (current_date, plant.slug)
        _create_or_update_weather_data_over_ftp_server(current_time, file_name, plant)
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
        print "specify datetime in %Y-%m-%d %H:%M:%S format %s" % exc
        return
    splants = SolarPlant.objects.filter(slug__in=PLANT_SLUG)
    for plant in splants:
        file_name = "%s_%s" % (file_name, plant.slug)
        while startdatetime <= enddatetime:
            _create_or_update_weather_data_over_ftp_server(startdatetime, file_name, plant)
            startdatetime = startdatetime + timedelta(minutes=DATA_TIME_INTERVAL)
            print "startdatetime %s " % startdatetime
        print "end ftp_cron_between_time_interval_main"
