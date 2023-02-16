import logging
import pandas as pd
import pytz
from solarrms.models import IndependentInverter, PlantSummaryDetails, PlantDeviceSummaryDetails
from django.utils import timezone
from solarrms.solarutils import sorted_nicely
import calendar
import datetime
from helpdesk.models import Ticket
from solarrms.solarutils import manipulateColumnNames,excelConversion,simpleExcelFormatting


logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)


from solarrms.api_views import update_tz
def get_inverter_alarms_from_ticket(starttime, endtime, plant, event_types):
    try:
        df_final = pd.DataFrame()
        number_of_days = (endtime - starttime).days
        for i in range(number_of_days+1):
            st = starttime
            et = starttime + datetime.timedelta(days=1)
            df = pd.DataFrame()
            for inverter in plant.independent_inverter_units.all():
                try:
                    inverter_alarms = []
                    alarms_dict = ""
                    identifier = inverter.sourceKey
                    associations = Ticket.get_identifier_history(plant, st, et, identifier, event_types)
                    for association in associations:
                        for solar_status in association['association_alarms']:
                            for alarm in association['association_alarms'][solar_status]:
                                alarms_dict += "Inverter status : " + str(solar_status) + ", alarm code : " + str(alarm['alarm_code']) + ", created : " + \
                                str(update_tz(alarm['alarm_created'], "Asia/Kolkata").replace(tzinfo=None)) + ", closed: " + \
                                str(update_tz(alarm['alarm_closed'], "Asia/Kolkata").replace(tzinfo=None)) + " ; "
                    inverter_alarms.append(alarms_dict)
                    df['Date'] = st.replace(hour=0,minute=0,second=0,microsecond=0).astimezone(pytz.utc).replace(tzinfo=None)
                    df[str(inverter.name)+"_AL"] = inverter_alarms
                except Exception as exception:
                    print str(exception)
                    continue
            df_final = df_final.append(df, ignore_index=True)
            starttime += datetime.timedelta(days=1)
        return df_final
    except Exception as exception:
        print str(exception)

def get_inverter_alarms_from_ticket_inverter_level(starttime, endtime,plant, event_types):
    try:
        df_final = pd.DataFrame()
        number_of_days = (endtime - starttime).days
        for i in range(number_of_days+1):
            st = starttime
            et = starttime + datetime.timedelta(days=1)
            for inverter in plant.independent_inverter_units.all():
                print str(inverter.name)
                df_inverter = pd.DataFrame()
                try:
                    solar_status_list = []
                    alarm_code_list = []
                    created_list=[]
                    closed_list=[]
                    inverters=[]
                    identifier = inverter.sourceKey
                    associations = Ticket.get_identifier_history(plant, st, et, identifier, event_types)
                    for association in associations:
                        for solar_status in association['association_alarms']:
                            for alarm in association['association_alarms'][solar_status]:
                                inverters.append(str(inverter.name))
                                solar_status_list.append(solar_status)
                                alarm_code_list.append(alarm['alarm_code'])
                                created_list.append(update_tz(alarm['alarm_created'], "Asia/Kolkata").replace(second=0,microsecond=0).replace(tzinfo=None))
                                closed_list.append(update_tz(alarm['alarm_closed'], "Asia/Kolkata").replace(second=0,microsecond=0).replace(tzinfo=None))
                    df_inverter['Inverter Name'] = inverters
                    df_inverter['Inverter Status'] = solar_status_list
                    df_inverter['Alarm Code'] = alarm_code_list
                    df_inverter['Created'] = created_list
                    df_inverter['Closed'] = closed_list
                    print df_inverter
                    if df_final.empty:
                        df_final = df_inverter
                    else:
                        df_final = df_final.append(df_inverter)
                except Exception as exception:
                    print str(exception)
                    continue
            starttime = starttime + datetime.timedelta(days=1)
        return df_final.sort(['Inverter Name','Created'])
    except Exception as exception:
        print str(exception)

def get_inverters_generation_report(starttime, endtime, plant):
    try:
        df_result = pd.DataFrame()
        inverters = plant.independent_inverter_units.all()
        inverters_name = []
        for inverter in inverters:
            inverters_name.append(str(inverter.name))
        inverters_name = sorted_nicely(inverters_name)
        inverters = []
        for name in inverters_name:
            inverter = IndependentInverter.objects.get(plant=plant, name=name)
            inverters.append(inverter)

        for inverter in inverters:
            df_inverter = pd.DataFrame()
            inverter_values = []
            inverter_timestamp = []
            inverter_generations = PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                            count_time_period=86400,
                                                                            identifier=str(inverter.sourceKey),
                                                                            ts__gte=starttime,
                                                                            ts__lte=endtime).order_by('ts')
            for value in inverter_generations:
                inverter_values.append(round(float(value.generation),3) if value.generation else value.generation)
                inverter_timestamp.append(pd.to_datetime(value.ts))
            df_inverter['Date'] = inverter_timestamp
            df_inverter[str(inverter.name)+' (kWh)'] = inverter_values
            df_inverter.sort('Date')
            if df_result.empty:
                df_result = df_inverter
            else:
                df_result = df_result.merge(df_inverter.drop_duplicates('Date'), how='outer', on='Date')
        return df_result
    except Exception as exception:
        print str(exception)

def get_plant_level_performance_parameters(starttime, endtime, plant):
    try:
        plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                  count_time_period=86400,
                                                                  identifier=str(plant.slug),
                                                                  ts__gte=starttime,
                                                                  ts__lte=endtime).order_by('ts')
        df_result = pd.DataFrame()
        timestamp = []
        generation = []
        pr = []
        cuf = []
        average_irradiation = []
        for value in plant_summary_values:
            timestamp.append(pd.to_datetime(value.ts))
            generation.append(round(value.generation,3) if value.generation else value.generation)
            pr.append(round(value.performance_ratio,3)if value.performance_ratio else value.performance_ratio)
            cuf.append(round(value.cuf,3) if value.cuf else value.cuf)
            average_irradiation.append(round(value.average_irradiation,3)if value.average_irradiation else value.average_irradiation)
        print(timestamp)
        df_result['Date'] = timestamp
        df_result['generation (kWh)'] = generation
        df_result['PR'] = pr
        df_result['CUF'] = cuf
        df_result['Insolation (kWh/m^2)'] = average_irradiation
        df_result.sort('Date')
        return df_result
    except Exception as exception:
        print str(exception)

def get_aggregated_parameters_at_plant_level_and_inverters_information(starttime, endtime, plant):
    try:
        plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                  count_time_period=86400,
                                                                  identifier=str(plant.slug),
                                                                  ts__gte=starttime,
                                                                  ts__lte=endtime).order_by('ts')
        df_result = pd.DataFrame()
        timestamp = []
        inclined_irradiance = []
        ambient_temperature = []
        module_temperature = []
        wind_speed = []
        grid_availability = []
        equipment_availability = []
        grid_availability_non_sunshine = []
        for value in plant_summary_values:
            timestamp.append(pd.to_datetime(value.ts))
            inclined_irradiance.append(round(value.average_irradiation,3) if value.average_irradiation else value.average_irradiation)
            ambient_temperature.append(round(value.average_ambient_temperature,3) if value.average_ambient_temperature else value.average_ambient_temperature)
            module_temperature.append(round(value.average_module_temperature,3) if value.average_module_temperature else value.average_module_temperature)
            wind_speed.append(round(value.average_wind_speed,3) if value.average_wind_speed else value.average_wind_speed)
            grid_availability.append(round(value.grid_availability,3) if value.grid_availability is not None else value.grid_availability)
            equipment_availability.append(round(value.equipment_availability,3) if value.equipment_availability is not None else value.equipment_availability)
            grid_availability_non_sunshine.append(100.0)
        df_result['Date'] = timestamp
        df_result['Inclined Irradiance (kWh/m^2)'] = inclined_irradiance
        df_result['Avg Ambient Temp (C)'] = ambient_temperature
        df_result['Avg Module Temp (C)'] = module_temperature
        df_result['Avg Wind Speed (km/hr)'] = wind_speed
        df_result.sort('Date')

        inverters = plant.independent_inverter_units.all()
        inverters_name = []
        for inverter in inverters:
            inverters_name.append(str(inverter.name))
        inverters_name = sorted_nicely(inverters_name)
        inverters = []
        for name in inverters_name:
            inverter = IndependentInverter.objects.get(plant=plant, name=name)
            inverters.append(inverter)

        for inverter in inverters:
            df_inverter = pd.DataFrame()
            inverter_values = []
            inverter_timestamp = []
            inverter_generations = PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                            count_time_period=86400,
                                                                            identifier=str(inverter.sourceKey),
                                                                            ts__gte=starttime,
                                                                            ts__lte=endtime).order_by('ts')
            for value in inverter_generations:
                inverter_values.append(round(float(value.total_working_hours),3) if value.generation else value.generation)
                inverter_timestamp.append(pd.to_datetime(value.ts))

            df_inverter['Date'] = inverter_timestamp
            df_inverter[str(inverter.name)+' (Operational hours)'] = inverter_values
            df_inverter.sort('Date')
            if df_result.empty:
                df_result = df_inverter
            else:
                df_result = df_result.merge(df_inverter.drop_duplicates('Date'), how='outer', on='Date')

        try:
            df_result['Equipment Availability (%)'] = equipment_availability
            df_result['Grid Availability During Sunshine Hours(%)'] = grid_availability
            df_result['Grid Availability During Non-Sunshine Hours(%)'] = grid_availability_non_sunshine
        except:
            pass

        df_result.sort('Date')
        return df_result
    except Exception as exception:
        print ("Error in getting the agregated values : " + str(exception))

def get_inverter_alarms_from_ticket_inverter_level_newmod(starttime, endtime,plant, event_types):
    try:
        df_final = pd.DataFrame()
        number_of_days = (endtime - starttime).days
        st = starttime
        et = endtime
        for inverter in plant.independent_inverter_units.all():
            print str(inverter.name)
            df_inverter = pd.DataFrame()
            try:
                solar_status_list = []
                alarm_code_list = []
                created_list=[]
                created_date=[]
                closed_list=[]
                inverters=[]
                identifier = inverter.sourceKey
                out={}
                out_duration={}
                associations = Ticket.get_identifier_history(plant, st, et, identifier, event_types)
                for association in associations:
                    for solar_status in association['association_alarms']:
                        for alarm in association['association_alarms'][solar_status]:
                            inverters.append(str(inverter.name))
                            solar_status_list.append(solar_status)
                            alarm_code = alarm['alarm_code']
                            alarm_duration_seconds = alarm['alarm_duration_seconds']

                            alarm_code_list.append(alarm_code)
                            created_list.append(update_tz(alarm['alarm_created'], "Asia/Kolkata").replace(second=0,microsecond=0).replace(tzinfo=None))
                            alarm_created_date=update_tz(alarm['alarm_created'], "Asia/Kolkata").replace(second=0,microsecond=0).replace(tzinfo=None).date()
                            created_date.append(alarm_created_date)

                            closed_list.append(update_tz(alarm['alarm_closed'], "Asia/Kolkata").replace(second=0,microsecond=0).replace(tzinfo=None))

                            if alarm_code in out:
                                out[alarm_created_date].append(alarm_code)
                                out_duration[alarm_created_date].append(alarm_duration_seconds)
                            else:
                                out[alarm_created_date]=[]
                                out_duration[alarm_created_date]=[]
                                out[alarm_created_date].append(alarm_code)
                                out_duration[alarm_created_date].append(alarm_duration_seconds)

                try:
                    no_of_alarms_list=[]
                    avg_alarm_duration_list=[]
                    for i in created_list:
                        no_of_alarms_list.append(len(out[i.date()]))
                        avg_alarm_duration_list.append(sum(out_duration[i.date()])/len(out_duration[i.date()]))
                except Exception as e:
                    print "Ghotala ",str(e)
                    logger.debug("Ghotala get_inverter_alarms_from_ticket_inverter_level_newmod "+str(e))

                df_inverter['Date'] = created_date
                df_inverter[str(inverter.name) + '_No_of_Alarms'] = no_of_alarms_list
                df_inverter[str(inverter.name) + '_Alarm_Code'] = alarm_code_list
                df_inverter[str(inverter.name) + '_Status_Code'] = solar_status_list
                df_inverter[str(inverter.name) + '_Avg_Alarm_Duration'] = avg_alarm_duration_list
                status_code = str(inverter.name) + '_Status_Code'
                alarm_code = str(inverter.name) + '_Alarm_Code'
                no_of_alarms = str(inverter.name) + '_No_of_Alarms'
                avg_alarm_duration = str(inverter.name) + '_Avg_Alarm_Duration'
                df_inverter = df_inverter.groupby('Date').agg({status_code: lambda x: ",".join(x),
                                                               alarm_code: lambda x: ",".join(map(str, x)),
                                                               no_of_alarms: 'sum',
                                                               avg_alarm_duration: 'mean'}).reset_index()

                df_inverter=df_inverter[['Date',no_of_alarms,alarm_code,status_code,avg_alarm_duration]]

                if df_final.empty:
                    df_final = df_inverter
                else:
                    df_final = df_final.merge(df_inverter.drop_duplicates('Date'), how='outer', on='Date')
            except Exception as exception:
                logger.debug("Got Exception in get_inverter_alarms_from_ticket_inverter_level_newmod : "+str(exception))
                continue
        print df_final
        return df_final
    except Exception as exception:
        # print "Inside Final Exception:",str(exception)
        logger.debug("Ghotala Inside Final Exception:"+str(exception))

def get_monthly_plant_report(plant):
    try:
        try:
            current_time = timezone.now()
            current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exc:
            current_time = timezone.now()
        initial_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        final_time = current_time
        month_start_day = initial_time.replace(day=1)
        month_end_day = final_time

        try:
            file_name = "_".join([str(plant.slug), str(calendar.month_name[month_start_day.month]), str(month_start_day.year), 'monthly_report']).replace(" ", "_") +  ".xls"
        except:
            file_name = "_".join([str(plant.slug),'monthly_report']).replace(" ", "_") +  ".xls"

        out_path = "/var/tmp/monthly_report/new/"+file_name
        writer = pd.ExcelWriter(out_path, engine='xlsxwriter')


        df_inverters_generation = get_inverters_generation_report(month_start_day, month_end_day, plant)
        df_aggregated_parameters = get_aggregated_parameters_at_plant_level_and_inverters_information(month_start_day, month_end_day, plant)
        df_plant_performance_prameters = get_plant_level_performance_parameters(month_start_day, month_end_day, plant)
        inverters_alarms = get_inverter_alarms_from_ticket_inverter_level_newmod(month_start_day, month_end_day, plant, ['INVERTERS_ALARMS'])
        if not df_inverters_generation.empty:
            df_inverters_generation['Date'] = df_inverters_generation['Date'].map(lambda x : (x.replace(tzinfo=pytz.utc).astimezone(plant.metadata.plantmetasource.dataTimezone)).date())
            df_inverters_generation = df_inverters_generation.set_index('Date')
            df_inverters_generation.to_excel(excel_writer = writer, sheet_name="Inverters_Generation")
            sheetName = "Inverters_Generation"

            # pandasDataFrame.to_excel(pandasWriter, sheet_name=str(solar_field_name))
            writer = simpleExcelFormatting(writer, df_inverters_generation, sheetName)

        if not df_aggregated_parameters.empty:
            df_aggregated_parameters['Date'] = df_aggregated_parameters['Date'].map(lambda x : (x.replace(tzinfo=pytz.utc).astimezone(plant.metadata.plantmetasource.dataTimezone)).date())
            df_aggregated_parameters,l1,l2= manipulateColumnNames(df_aggregated_parameters,plant,'Date')
            sheetName="Analog Data, Grid & Plant AL"
            df_aggregated_parameters.to_excel(excel_writer = writer, sheet_name=sheetName)
            writer= excelConversion(writer,df_aggregated_parameters,l1,l2,sheetName)

        if not df_plant_performance_prameters.empty:
            count = df_plant_performance_prameters.shape[0]
            df_plant_performance_prameters['Date'] = df_plant_performance_prameters['Date'].map(lambda x : (x.replace(tzinfo=pytz.utc).astimezone(plant.metadata.plantmetasource.dataTimezone)).date())
            df_plant_performance_prameters, l1, l2 = manipulateColumnNames(df_plant_performance_prameters, plant, 'Date')
            df_plant_performance_prameters.to_excel(excel_writer=writer, sheet_name="PR & CUF")
            sheetName="PR & CUF"
            writer = excelConversion(writer,df_plant_performance_prameters,l1,l2,sheetName)

        if not inverters_alarms.empty:
            #inverters_alarms['Date'] = inverters_alarms['Date'].map(lambda x : (x.replace(tzinfo=pytz.utc).astimezone(plant.metadata.plantmetasource.dataTimezone)).date())
            # inverters_alarms=inverters_alarms.set_index('Date')
            inverters_alarms, l1, l2 = manipulateColumnNames(inverters_alarms, plant, 'Date')
            inverters_alarms.to_excel(excel_writer=writer, sheet_name="Inverters Alarms")
            sheetName="Inverters Alarms"
            writer = excelConversion(writer, inverters_alarms,l1,l2, sheetName)

        writer.save()
        print "excel saved"
        logger.debug("Excel in new_solar_report get_monthly_plant_report saved ")
    except Exception as exception:
        print str(exception)
