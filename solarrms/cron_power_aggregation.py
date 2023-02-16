from dataglen.models import ValidDataStorageByStream
import pandas as pd
from django.utils import timezone
import datetime
from dashboards.models import DataglenClient
from solarrms.models import SolarPlant


# Method to aggregate DC power values at plant level obtained from all the inverters
def aggregate_dc_power(starttime, endtime, plant):
    try:
        final_df = pd.DataFrame()
        inverters = plant.independent_inverter_units.all()
        try:
            reporting_interval = int(plant.metadata.plantmetasource.dataReportingInterval)/60
        except:
            reporting_interval = 15

        for inverter in inverters:
            inverter_df = pd.DataFrame()
            dc_power_values = []
            dc_power_timestamp = []
            values = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                             stream_name='DC_POWER',
                                                             timestamp_in_data__gte=starttime,
                                                             timestamp_in_data__lt=endtime).limit(0)
            for value in values:
                dc_power_values.append(float(value.stream_value))
                dc_power_timestamp.append(value.timestamp_in_data.replace(minute=(value.timestamp_in_data.minute - value.timestamp_in_data.minute%reporting_interval),
                                                                          second=0, microsecond=0))
            inverter_df['timestamp'] = dc_power_timestamp
            inverter_df[str(inverter.name)] = dc_power_values
            if final_df.empty:
                final_df = inverter_df
            else:
                final_df = final_df.merge(inverter_df, on='timestamp', how='outer')
        if not final_df.empty:
            final_df['dc_power'] = final_df.sum(axis=1)
        return final_df.sort_values('timestamp')
    except Exception as exception:
        print str(exception)


# Method to aggregate AC power values at plant level obtained from all the inverters
def aggregate_ac_power(starttime, endtime, plant):
    try:
        final_df = pd.DataFrame()
        inverters = plant.independent_inverter_units.all()
        try:
            reporting_interval = int(plant.metadata.plantmetasource.dataReportingInterval)/60
        except:
            reporting_interval = 15

        for inverter in inverters:
            inverter_df = pd.DataFrame()
            ac_power_values = []
            ac_power_timestamp = []
            values = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                             stream_name='ACTIVE_POWER',
                                                             timestamp_in_data__gte=starttime,
                                                             timestamp_in_data__lt=endtime).limit(0)
            for value in values:
                ac_power_values.append(float(value.stream_value))
                ac_power_timestamp.append(value.timestamp_in_data.replace(minute=(value.timestamp_in_data.minute - value.timestamp_in_data.minute%reporting_interval),
                                                                          second=0, microsecond=0))
            inverter_df['timestamp'] = ac_power_timestamp
            inverter_df[str(inverter.name)] = ac_power_values
            if final_df.empty:
                final_df = inverter_df
            else:
                final_df = final_df.merge(inverter_df, on='timestamp', how='outer')
        if not final_df.empty:
            final_df['ac_power'] = final_df.sum(axis=1)
        return final_df.sort_values('timestamp')
    except Exception as exception:
        print str(exception)


def upload_aggregated_dc_power_data(plant):
    try:
        endtime = timezone.now()
        starttime = endtime - datetime.timedelta(hours=5)
        dc_power_values = aggregate_dc_power(starttime, endtime, plant)
        timestamp = dc_power_values['timestamp'].tolist()
        power_values = dc_power_values['dc_power'].tolist()
        for i in range(len(timestamp)):
            print i
            dc_power_value = ValidDataStorageByStream.objects.create(source_key=plant.metadata.plantmetasource.sourceKey,
                                                                     stream_name='INVERTERS_DC_POWER',
                                                                     timestamp_in_data=timestamp[i],
                                                                     stream_value=str(power_values[i]))
            dc_power_value.save()
    except Exception as exception:
        print str(exception)

def upload_aggregated_ac_power_data(plant):
    try:
        endtime = timezone.now()
        starttime = endtime - datetime.timedelta(hours=5)
        dc_power_values = aggregate_ac_power(starttime, endtime, plant)
        timestamp = dc_power_values['timestamp'].tolist()
        power_values = dc_power_values['ac_power'].tolist()
        for i in range(len(timestamp)):
            print i
            dc_power_value = ValidDataStorageByStream.objects.create(source_key=plant.metadata.plantmetasource.sourceKey,
                                                                     stream_name='INVERTERS_AC_POWER',
                                                                     timestamp_in_data=timestamp[i],
                                                                     stream_value=str(power_values[i]))
            dc_power_value.save()
    except Exception as exception:
        print str(exception)

def upload_aggregated_power_values():
    try:
        client = DataglenClient.objects.get(slug='renew-power')
        plants = SolarPlant.objects.filter(groupClient=client)
        for plant in plants:
            print "computing for plant : " + str(plant.slug)
            upload_aggregated_dc_power_data(plant)
            upload_aggregated_ac_power_data(plant)
    except Exception as exception:
        print str(exception)