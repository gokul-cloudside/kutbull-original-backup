from solarrms.models import SolarPlant
from dataglen.models import ValidDataStorageByStream
import pandas as pd
from helpdesk.models import Ticket, Queue
import numpy as np
from solarrms.models import HistoricEnergyValuesWithPrediction


# Method to get the average irradiation between 11 and 2
def find_average_irradiance_between_11_and_2(starttime, endtime, plant):
    try:
        meta = plant.metadata.plantmetasource
        values = ValidDataStorageByStream.objects.filter(source_key=meta.sourceKey,
                                                         stream_name='IRRADIATION',
                                                         timestamp_in_data__gte=starttime,
                                                         timestamp_in_data__lte=endtime)
        df_irradiation = pd.DataFrame()
        timestamp = []
        irradiation_values = []
        for v in values:
            timestamp.append(v.timestamp_in_data)
            irradiation_values.append(float(v.stream_value))
        df_irradiation['timestamp'] = timestamp
        df_irradiation['irradiation'] = irradiation_values
        df_irradiation = df_irradiation.set_index('timestamp')
        df_irradiation = df_irradiation.between_time("05:25:00","08:35:00")
        df_irradiation = df_irradiation.reset_index()
        return round(df_irradiation['irradiation'].mean(),4)
    except Exception as exception:
        return 0.0


def average_irradiation_summary(starttime, endtime, plants):
    try:
        print str('Client Name,Plant Slug,Plant Name,Irradiation Sensor Key,Latitude,Longitude,Average Irradiation')
        for plant in plants:
            print str(plant.groupClient.name)+','+str(plant.slug)+','+str(plant.name).replace(',',' ')+','+str(plant.metadata.plantmetasource.sourceKey)+','+\
                str(plant.latitude)+','+str(plant.longitude)+','+str(find_average_irradiance_between_11_and_2(starttime,endtime,plant))
    except Exception as exception:
        print str(exception)


# Method to get the total cleaning tickets so far and average closing time
def number_of_cleaning_tickets(plant):
    try:
        queue = Queue.objects.get(plant=plant)
        tickets = Ticket.objects.filter(queue=queue, event_type='PANEL_CLEANING')
        return len(tickets)
    except Exception as exception:
        #print str(exception)
        return 0

# method to get average cleaning ticket open time in minutes
def average_open_time_of_cleaning_tickets(plant):
    try:
        open_time_list = []
        queue = Queue.objects.get(plant=plant)
        tickets = Ticket.objects.filter(queue=queue, event_type='PANEL_CLEANING')
        for ticket in tickets:
            if int(ticket.status) == 4:
                open_time_list.append((ticket.modified-ticket.created).total_seconds()/60.0)
        if len(open_time_list)>0:
            return np.mean(open_time_list)
        else:
            return 0.0
    except Exception as exception:
        #print str(exception)
        return 0

def get_number_of_cleaning_tickets_created_for_all_the_plants():
    try:
        plants = SolarPlant.objects.all()
        print str('Client Name,Plant Slug,Plant Name,Irradiation Sensor Key,Latitude,Longitude,Number of Cleaning Tickets')
        for plant in plants:
            try:
                tickets_number = number_of_cleaning_tickets(plant)
                print str(plant.groupClient.name)+','+str(plant.slug)+','+str(plant.name).replace(',',' ')+','+str(plant.metadata.plantmetasource.sourceKey)+','+\
                str(plant.latitude)+','+str(plant.longitude)+','+str(tickets_number)
            except:
                continue
    except Exception as exception:
        print str(exception)

def get_average_open_time_of_cleaning_tickets_created_for_all_the_plants_in_minutes():
    try:
        plants = SolarPlant.objects.all()
        print str('Client Name,Plant Slug,Plant Name,Irradiation Sensor Key,Latitude,Longitude,Average Ticket open time(in minutes)')
        for plant in plants:
            try:
                average_ticket_open_time = average_open_time_of_cleaning_tickets(plant)
                print str(plant.groupClient.name)+','+str(plant.slug)+','+str(plant.name).replace(',',' ')+','+str(plant.metadata.plantmetasource.sourceKey)+','+\
                str(plant.latitude)+','+str(plant.longitude)+','+str(average_ticket_open_time)
            except:
                continue
    except Exception as exception:
        print str(exception)

def find_average_prediction_deviation(starttime, endtime, plant):
    try:
        predicted_values = []
        actual_values = []
        values = HistoricEnergyValuesWithPrediction.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                   count_time_period=86400,
                                                                   identifier=str(plant.slug),
                                                                   ts__gte=starttime,
                                                                   ts__lte=endtime)
        for v in values:
            if float(v.predicted_energy)>0.0:
                actual_values.append(float(v.energy))
                predicted_values.append(float(v.predicted_energy))
        no_of_days = len(actual_values)
        prediction_hours = no_of_days*12
        predicted_values = np.sum(predicted_values)
        actual_values = np.sum(actual_values)
        deviation = abs(((predicted_values-actual_values)/(float(plant.capacity)*prediction_hours))*100)
        if np.isnan(deviation):
            return None
        else:
            return 100 - deviation
    except Exception as exception:
        print str(exception)
        return None

def get_prediction_accuracy_for_all_the_plants_in_percent(starttime, endtime):
    try:
        plants = SolarPlant.objects.all()
        print str('Client Name,Plant Slug,Plant Name,Irradiation Sensor Key,Latitude,Longitude,Prediction Accuracy(in percent)')
        for plant in plants:
            try:
                prediction_accuracy = find_average_prediction_deviation(starttime, endtime, plant)
                print str(plant.groupClient.name)+','+str(plant.slug)+','+str(plant.name).replace(',',' ')+','+str(plant.metadata.plantmetasource.sourceKey)+','+\
                str(plant.latitude)+','+str(plant.longitude)+','+str(prediction_accuracy)
            except:
                continue
    except Exception as exception:
        print str(exception)

def number_of_inverter_alarms_per_code(plant):
    try:
        alarms_dict = {}
        queue = Queue.objects.get(plant=plant)
        tickets = Ticket.objects.filter(queue=queue, event_type='INVERTERS_ALARMS')
        for ticket in tickets:
            associations = ticket.associations.all()
            for association in associations:
                try:
                    alarms = association.alarms.all()
                    for alarm in alarms:
                        if alarm.alarm_code:
                            alarms_dict[str(alarm.alarm_code)]+=1
                        else:
                            pass
                except:
                    alarms_dict[str(alarm.alarm_code)] = 1
        return alarms_dict
    except Exception as exception:
        print str(exception)
        return {}

def get_number_of_inverter_alarms_per_code_for_all_plants():
    try:
        plants = SolarPlant.objects.all()
        print str('Client Name;Plant Slug;Plant Name;Irradiation Sensor Key;Latitude;Longitude;Number of alarms per code')
        for plant in plants:
            try:
                alarms_dict = number_of_inverter_alarms_per_code(plant)
                print str(plant.groupClient.name)+';'+str(plant.slug)+';'+str(plant.name).replace(',',' ')+';'+str(plant.metadata.plantmetasource.sourceKey)+';'+\
                str(plant.latitude)+';'+str(plant.longitude)+';'+str(alarms_dict)
            except:
                continue
    except Exception as exception:
        print str(exception)


def average_open_time_inverter_alarms_per_code_in_minutes(plant):
    try:
        alarms_dict = {}
        alarm_dict_final = {}
        queue = Queue.objects.get(plant=plant)
        tickets = Ticket.objects.filter(queue=queue, event_type='INVERTERS_ALARMS')
        for ticket in tickets:
            associations = ticket.associations.all()
            for association in associations:
                try:
                    alarms = association.alarms.all()
                    for alarm in alarms:
                        if alarm.alarm_code and not alarm.active:
                            st = alarm.created
                            et = alarm.closed
                            closing_time = (et-st).total_seconds()/60
                            alarms_dict[str(alarm.alarm_code)].append(closing_time)
                        else:
                            pass
                except:
                    alarms_dict[str(alarm.alarm_code)] = [closing_time]
        for key in alarms_dict.keys():
            alarm_dict_final[key] = np.mean(alarms_dict[key])
        return alarm_dict_final
    except Exception as exception:
        print str(exception)
        return {}

def get_average_open_time_of_inverter_alarms_per_code_for_all_plants():
    try:
        plants = SolarPlant.objects.all()
        print str('Client Name;Plant Slug;Plant Name;Irradiation Sensor Key;Latitude;Longitude;Average open Time of alarms per code')
        for plant in plants:
            try:
                alarms_dict = average_open_time_inverter_alarms_per_code_in_minutes(plant)
                print str(plant.groupClient.name)+';'+str(plant.slug)+';'+str(plant.name).replace(',',' ')+';'+str(plant.metadata.plantmetasource.sourceKey)+';'+\
                str(plant.latitude)+';'+str(plant.longitude)+';'+str(alarms_dict)
            except:
                continue
    except Exception as exception:
        print str(exception)


def warranty_enforcement(starttime, endtime, plant):
    try:
        result = {}
        inverters = plant.independent_inverter_units.all()
        for inverter in inverters:
            active_power = []
            dc_power = []
            ts_active_power = []
            ts_dc_power = []
            df_dc_power = pd.DataFrame()
            df_active_power = pd.DataFrame()
            values = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                             stream_name='DC_POWER',
                                                             timestamp_in_data__gte=starttime,
                                                             timestamp_in_data__lte=endtime).limit(0)
            for value in values:
                ts_dc_power.append(value.timestamp_in_data.replace(second=0, microsecond=0))
                dc_power.append(float(value.stream_value))
            df_dc_power['timestamp'] = ts_dc_power
            df_dc_power['DC_POWER'] = dc_power

            values = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                             stream_name='ACTIVE_POWER',
                                                             timestamp_in_data__gte=starttime,
                                                             timestamp_in_data__lte=endtime).limit(0)
            for value in values:
                ts_active_power.append(value.timestamp_in_data.replace(second=0, microsecond=0))
                active_power.append(float(value.stream_value))
            df_active_power['timestamp'] = ts_active_power
            df_active_power['ACTIVE_POWER'] = active_power

            if df_dc_power.shape >0 and df_active_power.shape>0:
                df_dc_power = df_dc_power[df_dc_power['DC_POWER']>0.0]
                df_active_power = df_active_power[df_active_power['ACTIVE_POWER']>0.0]
                df_power = df_dc_power.merge(df_active_power, on='timestamp', how='inner')
            if df_power.shape>0:
                efficiency = (np.mean(df_power['ACTIVE_POWER'])/np.mean(df_power['DC_POWER']))*100.0
                if np.isnan(efficiency):
                    efficiency = 0.0
            else:
                efficiency = 0.0
            result[inverter.name] = round(efficiency,2)
        return  result
    except Exception as exception:
        print str(exception)

def warranty_enforcement_for_all_the_plants(starttime, endtime):
    try:
        plants = SolarPlant.objects.all()
        print str('Client Name;Plant Slug;Plant Name;Irradiation Sensor Key;Latitude;Longitude;Inverter Manufacturer;Average Efficiency')
        for plant in plants:
            try:
                inverter_manufacturer=plant.independent_inverter_units.all()[0].manufacturer
                average_efficiency = warranty_enforcement(starttime, endtime, plant)
                print str(plant.groupClient.name)+';'+str(plant.slug)+';'+str(plant.name).replace(',',' ')+';'+str(plant.metadata.plantmetasource.sourceKey)+';'+\
                str(plant.latitude)+';'+str(plant.longitude)+';'+str(inverter_manufacturer)+';'+str(average_efficiency)
            except:
                continue
    except Exception as exception:
        print str(exception)