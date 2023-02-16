import pandas as pd
from dataglen.models import ValidDataStorageByStream
from solarrms.solarutils import fill_results
import datetime
from solarrms.models import SolarPlant
endtime = '2017-02-17 05:30:00'

def update_ajb_aggregated_current_value(endtime, plant):
    try:
        print ("computing current for plant: "+str(plant.slug))
        groups = plant.solar_groups.all()
        #inverters = plant.independent_inverter_units.all()
        #inverters = [inverters[13],inverters[14],inverters[15],inverters[16]]#, inverters[1],inverters[2],inverters[3],inverters[4],inverters[5]]
        inverters = []
        for i in range(7,8):
            inverters.extend(groups[i].groupIndependentInverters.all())
        for inverter in inverters:
            print("computing for inverter " + str(inverter.name))
            df_results_current = pd.DataFrame()
            ajbs = inverter.ajb_units.all()
            #ajbs = [ajbs[0]]
            if ajbs:
                for ajb in ajbs:
                    print("computing for " + str(ajb.name))
                    try:
                        df_results_current_temp = pd.DataFrame()
                        streams = ajb.fields.all().filter(isActive=True)
                        for stream in streams:
                            if str(stream.name).startswith('S'):
                                df_list_current_temp = []
                                ajb_data_current_temp = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                                                                stream_name= stream.name,
                                                                                                timestamp_in_data__lte=endtime
                                                                                                ).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')
                                values_current_temp = []
                                timestamp_current_temp = []
                                for data_point in ajb_data_current_temp:
                                    timestamp_current_temp.append(data_point[1].replace(second=0, microsecond=0))
                                    values_current_temp.append(float(data_point[0]))
                                if len(values_current_temp) > 0:
                                    df_list_current_temp.append(pd.DataFrame({stream.name: values_current_temp,
                                                                             'timestamp': pd.to_datetime(timestamp_current_temp)}))

                                if len(df_list_current_temp) > 0:
                                    results_current_temp = df_list_current_temp[0]
                                    for i in range(1, len(df_list_current_temp)):
                                        results_current_temp = results_current_temp.merge(df_list_current_temp[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
                                        updated_results_current_temp = fill_results(results_current_temp)
                                        results_current_temp = updated_results_current_temp
                                    if df_results_current_temp.empty:
                                        df_results_current_temp = results_current_temp
                                    else:
                                        df_new = pd.merge(df_results_current_temp, results_current_temp.drop_duplicates('timestamp'), on='timestamp', how='outer')
                                        df_results_current_temp = df_new
                        df_results_current_temp['current'] = df_results_current_temp.sum(axis=1)
                        for i in range(df_results_current_temp.count()['timestamp']):
                            try:
                                value = ValidDataStorageByStream.objects.create(source_key=ajb.sourceKey,
                                                                                stream_name='CURRENT',
                                                                                timestamp_in_data=df_results_current_temp.loc[i]['timestamp'],
                                                                                raw_value=str(df_results_current_temp.loc[i]['current']),
                                                                                stream_value=str(df_results_current_temp.loc[i]['current']))
                                value.save()
                            except Exception as exception:
                                print(str(exception))
                    except Exception as exception:
                        print("Error : " + str(exception))
                        continue

    except Exception as exception:
        print(str(exception))


def update_ajb_aggregated_power_value(endtime, plant):
    try:
        print ("computing power for plant: "+str(plant.slug))
        inverters = plant.independent_inverter_units.all()
        #inverters = [inverters[8]]#, inverters[1],inverters[2],inverters[3],inverters[4],inverters[5]]
        for inverter in inverters:
            print ("computing power for inverter " + str(inverter.name))
            df_results_current = pd.DataFrame()
            ajbs = inverter.ajb_units.all()
            #ajbs = [ajbs[0]]
            if ajbs:
                for ajb in ajbs:
                    df_list_voltage = []
                    df_list_current = []
                    print("computing power for " + str(ajb.name))
                    try:
                        ajb_data_voltage = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                                                   stream_name='VOLTAGE',
                                                                                   timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')

                        values_voltage = []
                        timestamp_voltage = []
                        for data_point in ajb_data_voltage:
                            timestamp_voltage.append(data_point[1].replace(second=0, microsecond=0))
                            values_voltage.append(float(data_point[0])/1000.0)
                        df_list_voltage.append(pd.DataFrame({'voltage': values_voltage,
                                                             'timestamp': pd.to_datetime(timestamp_voltage)}))

                        if len(df_list_voltage) > 0:
                            results_voltage = df_list_voltage[0]
                            for i in range(1, len(df_list_voltage)):
                                results_voltage = results_voltage.merge(df_list_voltage[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
                                updated_results_voltage = fill_results(results_voltage)
                                results_voltage = updated_results_voltage
                            #results_voltage.set_index('timestamp', inplace=True)
                            results_voltage = results_voltage.sort()

                        #print results_voltage


                        ajb_data_current = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                                                   stream_name='CURRENT',
                                                                                   timestamp_in_data__lte=endtime).limit(0).order_by('timestamp_in_data').values_list('stream_value','timestamp_in_data')

                        values_current = []
                        timestamp_current = []
                        for data_point in ajb_data_current:
                            timestamp_current.append(data_point[1].replace(second=0, microsecond=0))
                            values_current.append(float(data_point[0]))
                        df_list_current.append(pd.DataFrame({'current': values_current,
                                                            'timestamp': pd.to_datetime(timestamp_current)}))


                        if len(df_list_current) > 0:
                            results_current = df_list_current[0]
                            for i in range(1, len(df_list_current)):
                                results_current = results_current.merge(df_list_current[i].drop_duplicates('timestamp'), how='outer', on='timestamp')
                                updated_results_current = fill_results(results_current)
                                results_current = updated_results_current
                            #results_current.set_index('timestamp', inplace=True)
                            results_current = results_current.sort()

                        #print results_current

                        if not results_current.empty and not results_voltage.empty:
                            df_results_power = pd.DataFrame()
                            df_results_power['timestamp'] = results_current['timestamp']
                            df_results_power['power'] = results_current['current']*results_voltage['voltage']

                        #print df_results_power
                        for i in range(df_results_power.count()['timestamp']):
                            try:
                                value = ValidDataStorageByStream.objects.create(source_key=ajb.sourceKey,
                                                                                stream_name='POWER',
                                                                                timestamp_in_data=df_results_power.loc[i]['timestamp'],
                                                                                raw_value=str(df_results_power.loc[i]['power']),
                                                                                stream_value=str(df_results_power.loc[i]['power']))
                                value.save()
                            except Exception as exception:
                                print(str(exception))
                    except Exception as exception:
                        print("Error : " + str(exception))
                        continue

    except Exception as exception:
        print(str(exception))

def update_current_power_values():
    try:
        print("update cronjob started")
        end_time = datetime.datetime.strptime(endtime, '%Y-%m-%d %H:%M:%S')
        print(end_time)
        plants = SolarPlant.objects.all()
        include_plants = ['waaneep']
        for plant in plants:
            print("computing for plant: " + str(plant.slug))
            if str(plant.slug) in include_plants:
                #update_ajb_aggregated_current_value(end_time, plant)
                update_ajb_aggregated_power_value(end_time, plant)
            else:
                pass
    except Exception as exception:
        print(str(exception))
