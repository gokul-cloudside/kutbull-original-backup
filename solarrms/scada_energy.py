from solarrms.models import SolarPlant, ScadaDailyEnergyTable, HistoricEnergyValues, CUFTable, SpecificYieldTable,\
    KWHPerMeterSquare, PerformanceRatioTable, PlantSummaryDetails, PlantDeviceSummaryDetails, PVSystInfo
from solarrms.solarutils import get_energy_from_scada_values, get_minutes_aggregated_energy, get_energy_meter_values
from django.utils import timezone
from dataglen.models import ValidDataStorageByStream
import pandas as pd
import numpy as np
import datetime, time

def store_scada_energy_values(plant):
    try:
        print "storing past energy values for : " + str(plant.slug)
        try:
            energy_values = get_energy_from_scada_values(plant, split=False, est=False)
            for value in energy_values:
                new_entry = ScadaDailyEnergyTable.objects.create(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                 count_time_period=86400,
                                                                 energy_type='ACTUAL',
                                                                 identifier=str(plant.slug),
                                                                 ts=value['timestamp'],
                                                                 energy=value['energy'],
                                                                 updated_at=timezone.now())
                new_entry.save()
            energy_values = get_energy_from_scada_values(plant, split=False, est=True)
            for value in energy_values:
                new_entry = ScadaDailyEnergyTable.objects.create(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                 count_time_period=86400,
                                                                 energy_type='ESTIMATED',
                                                                 identifier=str(plant.slug),
                                                                 ts=value['timestamp'],
                                                                 energy=value['energy'],
                                                                 updated_at=timezone.now())
                new_entry.save()

            # store the past energy of inverters
            inverters_energy_values = get_energy_from_scada_values(plant, split=True, est=False)
            for source_key in inverters_energy_values.keys():
                energy_values = inverters_energy_values[source_key]
                for value in energy_values:
                    new_entry = ScadaDailyEnergyTable.objects.create(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                     count_time_period=86400,
                                                                     energy_type='ACTUAL',
                                                                     identifier=str(source_key),
                                                                     ts=value['timestamp'],
                                                                     energy=value['energy'],
                                                                     updated_at=timezone.now())
                    new_entry.save()

            inverters_estimated_energy_values = get_energy_from_scada_values(plant, split=True, est=True)
            for source_key in inverters_estimated_energy_values.keys():
                estimated_energy_values = inverters_estimated_energy_values[source_key]
                for value in estimated_energy_values:
                    new_entry = ScadaDailyEnergyTable.objects.create(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                     count_time_period=86400,
                                                                     energy_type='ESTIMATED',
                                                                     identifier=str(source_key),
                                                                     ts=value['timestamp'],
                                                                     energy=value['energy'],
                                                                     updated_at=timezone.now())
                    new_entry.save()

        except:
            pass
    except Exception as exception:
        print str(exception)

def get_grid_availability_atria(starttime, endtime, plant):
    try:
        inverters = plant.independent_inverter_units.all()
        df_final = pd.DataFrame()
        for inverter in inverters:
            inverter_values = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                      stream_name='SOLAR_STATUS',
                                                                      timestamp_in_data__gte=starttime,
                                                                      timestamp_in_data__lte=endtime).limit(0)
            status_values = []
            inverter_timestamp = []
            df_inverter = pd.DataFrame()
            for value in inverter_values:
                inverter_timestamp.append(value.timestamp_in_data.replace(second=0, microsecond=0))
                status_values.append(float(value.stream_value))
            df_inverter['timestamp'] = inverter_timestamp
            df_inverter[str(inverter.name)] = status_values
            df_inverter = df_inverter[df_inverter[str(inverter.name)]>0]

            if df_final.empty and not df_inverter.empty:
                df_final = df_inverter
            elif not df_final.empty and not df_inverter.empty:
                df_final = df_final.merge(df_inverter, on='timestamp', how='inner')
            else:
                pass

        if not df_final.empty:
            df_final = df_final.sort('timestamp')
            df_final['ts'] = df_final['timestamp'].diff()
        if not df_final.empty:
            down_time = df_final['ts'].sum().total_seconds()
            if np.isnan(down_time):
                down_time = 0
        else:
            down_time = 0
        return down_time
    except Exception as exception:
        print str(exception)
        return 0

def calculate_AC_CUF(starttime, endtime, plant):
    actual_energy = 0.0
    CUF = 0.0
    if plant.metadata.energy_meter_installed:
        energy_values = get_energy_meter_values(starttime,endtime,plant,'MONTH')
    else:
        energy_values = get_minutes_aggregated_energy(starttime,endtime,plant,'MONTH',1)

    try:
        plant_capacity = plant.ac_capacity if plant.ac_capacity else plant.capacity
    except:
        plant_capacity = plant.capacity

    if energy_values and len(energy_values)>0:
        for value in energy_values:
            actual_energy += float(value['energy'])
        delta_hours=24
        CUF = actual_energy/(delta_hours * plant_capacity)
    return CUF


def update_past_days_energy_based_on_scada_values(plant):
    try:
        updated_energy_values = ScadaDailyEnergyTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                     count_time_period=86400,
                                                                     energy_type='ACTUAL',
                                                                     identifier=str(plant.slug)).limit(15)
        for value in updated_energy_values:
            new_entry = HistoricEnergyValues.objects.create(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                            count_time_period=86400,
                                                            identifier=str(plant.slug),
                                                            ts=value.ts,
                                                            energy=value.energy,
                                                            updated_at=timezone.now())
            new_entry.save()
    except Exception as exception:
        print str(exception)


def update_past_days_cuf_based_on_scada_values(plant):
    try:
        updated_energy_values = ScadaDailyEnergyTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                     count_time_period=86400,
                                                                     energy_type='ACTUAL',
                                                                     identifier=str(plant.slug)).limit(15)
        for value in updated_energy_values:
            new_entry = CUFTable.objects.create(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                count_time_period=86400,
                                                identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                ts=value.ts,
                                                CUF=float(value.energy)/(float(plant.capacity)*24),
                                                updated_at=timezone.now())
            new_entry.save()
    except Exception as exception:
        print str(exception)


def update_past_days_specific_yield_based_on_scada_values(plant):
    try:
        updated_energy_values = ScadaDailyEnergyTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                     count_time_period=86400,
                                                                     energy_type='ACTUAL',
                                                                     identifier=str(plant.slug)).limit(15)
        for value in updated_energy_values:
            print value.energy, float(value.energy)/float(plant.capacity), value.ts
            new_entry = SpecificYieldTable.objects.create(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                          count_time_period=86400,
                                                          identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                          ts=value.ts,
                                                          specific_yield=float(value.energy)/float(plant.capacity),
                                                          updated_at=timezone.now())
            new_entry.save()
    except Exception as exception:
        print str(exception)

def get_pr_value_based_on_scada_pr_values(starttime, endtime, plant):
    try:
        df_PR = pd.DataFrame()
        meta = plant.metadata.plantmetasource
        values = ValidDataStorageByStream.objects.filter(source_key=meta.sourceKey,
                                                          stream_name='PR',
                                                          timestamp_in_data__gte=starttime,
                                                          timestamp_in_data__lte=endtime).limit(0)
        ts = []
        pr = []
        for value in values:
            ts.append(value.timestamp_in_data)
            pr.append(float(value.stream_value))
        df_PR['timestamp'] = ts
        df_PR['PR'] = pr
        df_PR = df_PR[df_PR['PR']>0]
        pr_value = df_PR['PR'].mean()
        if np.isnan(pr_value):
            return 0
        else:
            return pr_value
    except Exception as exception:
        print str(exception)

def get_plant_start_time_based_on_scada_values(starttime, endtime, plant):
    try:
        meta = plant.metadata.plantmetasource
        values = ValidDataStorageByStream.objects.filter(source_key=meta.sourceKey,
                                                         stream_name='PLANT_START_TIME',
                                                         timestamp_in_data__gte=starttime,
                                                         timestamp_in_data__lte=endtime).limit(1)
        start_time = None
        if len(values)>0:
            start_time = str(values[0].stream_value)
        return start_time
    except Exception as exception:
        print str(exception)

def get_plant_end_time_based_on_scada_values(starttime, endtime, plant):
    try:
        meta = plant.metadata.plantmetasource
        values = ValidDataStorageByStream.objects.filter(source_key=meta.sourceKey,
                                                         stream_name='PLANT_END_TIME',
                                                         timestamp_in_data__gte=starttime,
                                                         timestamp_in_data__lte=endtime).limit(0)
        end_time = None
        if len(values)>0:
            for v in values:
                if str(v.stream_value) != '-':
                    end_time = str(v.stream_value)
        return end_time
    except Exception as exception:
        print str(exception)

def get_plant_run_time(starttime, endtime, plant):
    try:
        run_time = None
        plant_start_time = get_plant_start_time_based_on_scada_values(starttime, endtime, plant)
        plant_end_time = get_plant_end_time_based_on_scada_values(starttime, endtime, plant)
        external_grid_down_time = get_grid_availability_atria(starttime, endtime, plant)
        if plant_start_time and plant_end_time:
            start_time = datetime.datetime.strptime(plant_start_time,'%H:%M:%S')
            end_time = datetime.datetime.strptime(plant_end_time,'%H:%M:%S')
            run_time_seconds = (end_time-start_time).total_seconds() - external_grid_down_time
            run_time = time.strftime("%H:%M:%S", time.gmtime(run_time_seconds))
        return run_time
    except Exception as exception:
        print str(exception)

def update_past_days_performance_ratio_based_on_scada_values(plant):
    try:
        updated_energy_values = ScadaDailyEnergyTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                     count_time_period=86400,
                                                                     energy_type='ACTUAL',
                                                                     identifier=str(plant.slug)).limit(15)
        for value in updated_energy_values:
            performance_ratio = get_pr_value_based_on_scada_pr_values(value.ts, value.ts+datetime.timedelta(days=1), plant)
            if performance_ratio>0.0:
                print(performance_ratio, value.ts)
                new_entry = PerformanceRatioTable.objects.create(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                 count_time_period=86400,
                                                                 identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                                 ts=value.ts,
                                                                 performance_ratio=performance_ratio,
                                                                 updated_at=timezone.now())
                new_entry.save()
    except Exception as exception:
        print str(exception)

def update_plant_summary_details_based_on_scada_values(plant):
    try:
        daily_historical_energy_values = ScadaDailyEnergyTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                              count_time_period=86400,
                                                                              energy_type='ACTUAL',
                                                                              identifier=str(plant.slug)).limit(15)

        daily_historical_estimated_energy_values = ScadaDailyEnergyTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                        count_time_period=86400,
                                                                                        energy_type='ESTIMATED',
                                                                                        identifier=str(plant.slug)).limit(15)
        try:
            plant_ac_capacity = plant.ac_capacity if plant.ac_capacity else plant.capacity
        except:
            plant_ac_capacity = plant.capacity
        for index in range(len(daily_historical_energy_values)):
            plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                      count_time_period=86400,
                                                                      identifier=plant.slug,
                                                                      ts=daily_historical_energy_values[index].ts)
            performance_ratio_values = PerformanceRatioTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                            count_time_period=86400,
                                                                            identifier=plant.metadata.plantmetasource.sourceKey,
                                                                            ts=daily_historical_energy_values[index].ts)
            print "performance_ratio_values"
            print len(performance_ratio_values)
            print daily_historical_energy_values[index].ts
            if len(performance_ratio_values)>0:
                performance_ratio_value = float(performance_ratio_values[0].performance_ratio)
            else:
                performance_ratio_value = 0.0
            plant_start_time = get_plant_start_time_based_on_scada_values(daily_historical_energy_values[index].ts,
                                                                          daily_historical_energy_values[index].ts+datetime.timedelta(days=1),
                                                                          plant)
            plant_end_time = get_plant_end_time_based_on_scada_values(daily_historical_energy_values[index].ts,
                                                                      daily_historical_energy_values[index].ts+datetime.timedelta(days=1),
                                                                      plant)
            plant_run_time = get_plant_run_time(daily_historical_energy_values[index].ts,
                                                daily_historical_energy_values[index].ts+datetime.timedelta(days=1),
                                                plant)
            print "start end values"
            print daily_historical_energy_values[index].ts, plant_start_time, plant_end_time, plant_run_time
            energy_value = daily_historical_energy_values[index].energy
            cuf = float(energy_value)/float(plant.capacity*24)
            ac_cuf = float(energy_value)/float(plant_ac_capacity*24)
            specific_yield = float(energy_value)/float(plant.capacity)
            estimated_generation = daily_historical_estimated_energy_values[index].energy
            curtailment_loss = float(estimated_generation) - float(energy_value)
            month = daily_historical_energy_values[index].ts.month
            ghi_pvsyst = PVSystInfo.objects.filter(plant=plant,
                                                   parameterName='GHI_IRRADIANCE',
                                                   timePeriodType='MONTH',
                                                   timePeriodValue=month)
            print energy_value, specific_yield, cuf, daily_historical_energy_values[index].ts
            if len(ghi_pvsyst)>0:
                estimated_ghi = ghi_pvsyst[0].parameterValue
            else:
                estimated_ghi = 0.0
            if len(plant_summary_values)>0:
                plant_summary_values.update(generation=energy_value,
                                            performance_ratio=performance_ratio_value,
                                            cuf=cuf,
                                            ac_cuf=ac_cuf,
                                            specific_yield=specific_yield,
                                            estimated_generation=estimated_generation,
                                            curtailment_loss=curtailment_loss,
                                            estimated_ghi=estimated_ghi,
                                            plant_start_time=plant_start_time,
                                            plant_stop_time=plant_end_time,
                                            plant_run_time=plant_run_time)
    except Exception as exception:
        print str(exception)

def update_inverters_summary_details(plant):
    try:
        inverters = plant.independent_inverter_units.all()
        for inverter in inverters:
            daily_historical_inverter_energy_values = ScadaDailyEnergyTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                           count_time_period=86400,
                                                                                           energy_type='ACTUAL',
                                                                                           identifier=str(inverter.sourceKey)).limit(15)

            daily_historical_estimated_inverter_energy_values = ScadaDailyEnergyTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                                     count_time_period=86400,
                                                                                                     energy_type='ESTIMATED',
                                                                                                     identifier=str(inverter.sourceKey)).limit(15)
            for index in range(len(daily_historical_inverter_energy_values)):
                inverter_values = PlantDeviceSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                           count_time_period=86400,
                                                                           identifier=str(inverter.sourceKey),
                                                                           ts=daily_historical_inverter_energy_values[index].ts)
                if len(inverter_values)>0:
                    curtailment_loss = daily_historical_estimated_inverter_energy_values[index].energy - daily_historical_inverter_energy_values[index].energy
                    inverter_value = inverter_values[0]
                    inverter_value.update(generation=daily_historical_inverter_energy_values[index].energy,
                                          estimated_generation=daily_historical_estimated_inverter_energy_values[index].energy,
                                          curtailment_loss=curtailment_loss)
    except Exception as exception:
        print str(exception)

def update_metrics_based_on_scada_values():
    try:
        plant = SolarPlant.objects.get(slug='pavagada')
        store_scada_energy_values(plant)
        update_past_days_energy_based_on_scada_values(plant)
        update_past_days_cuf_based_on_scada_values(plant)
        update_past_days_specific_yield_based_on_scada_values(plant)
        update_past_days_performance_ratio_based_on_scada_values(plant)
        update_plant_summary_details_based_on_scada_values(plant)
        update_inverters_summary_details(plant)
    except Exception as exception:
        print str(exception)
