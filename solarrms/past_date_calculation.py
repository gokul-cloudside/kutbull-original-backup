# Script to re calculate energy and other KPI's in case past data was uploaded.
import datetime
from solarrms.models import HistoricEnergyValues, HistoricEnergyValuesWithPrediction, PerformanceRatioTable, CUFTable,\
    SpecificYieldTable, KWHPerMeterSquare, PlantSummaryDetails, PlantDeviceSummaryDetails, MaxValuesTable, VirtualGateway
from solarrms.solarutils import update_tz, get_aggregated_energy, get_expected_energy, calculate_pr, \
    calculate_specific_yield, calculate_CUF, get_kwh_per_meter_square_value, get_minutes_aggregated_energy
import pytz
from django.conf import settings
from dataglen.models import ValidDataStorageByStream
from solarrms.cron_max_values import get_max_irradiance, get_max_dc_power_inverter_wise, get_max_active_power_inverter_wise
from solarrms.settings import TOTAL_OPERATIONAL_HOURS_UNITS, TOTAL_OPERATIONAL_HOURS_UNITS_CONVERSION
from dateutil import parser

from solarrms.models import SolarPlant, SolarGroup, GatewaySource

# Re calculate historic energy
def historic_energy_recalculate(starttime, endtime, plant):
    try:
        try:
            starttime = pytz.utc.localize(starttime)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        try:
            endtime = pytz.utc.localize(endtime)
            endtime = endtime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        while endtime>starttime:
            initial_time = starttime.replace(hour=0, minute=0, second= 0, microsecond=0)
            final_time = starttime.replace(hour=23, minute=59, second=59, microsecond=59)
            try:
                todays_energy = get_minutes_aggregated_energy(initial_time,final_time,plant,'DAY',1)
                print todays_energy
            except Exception as exception:
                print("Error in getting the energy values" + str(exception))
            try:
                if todays_energy and len(todays_energy) > 0:
                    #energy_values = [item['energy'] for item in todays_energy]
                    if len(todays_energy) > 0:
                        today_energy_value = todays_energy[len(todays_energy)-1]['energy']
                    else:
                        today_energy_value = 0.0
                else:
                    today_energy_value = 0.0
            except Exception as exception:
                print str(exception)
                today_energy_value = 0.0
            print "today_energy_value"
            print initial_time, today_energy_value
            try:
                daily_energy_entry = HistoricEnergyValues.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                      count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                      identifier=plant.slug,
                                                                      ts=initial_time)
                daily_energy_entry.update(energy=today_energy_value)
            except Exception as exception:
                print str(exception)
                energy_entry = HistoricEnergyValues.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=plant.slug,
                                                                   ts=initial_time,
                                                                   energy=today_energy_value)
                energy_entry.save()
            starttime = starttime + datetime.timedelta(days=1)
    except Exception as exception:
        print str(exception)


# Re calculate historic energy with prediction
def historic_energy_with_prediction_recalculate(starttime, endtime, plant):
    try:
        try:
            starttime = pytz.utc.localize(starttime)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        try:
            endtime = pytz.utc.localize(endtime)
            endtime = endtime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        while endtime>starttime:
            initial_time = starttime.replace(hour=0, minute=0, second= 0, microsecond=0)
            final_time = starttime.replace(hour=23, minute=59, second=59, microsecond=59)

            try:
                todays_energy = get_minutes_aggregated_energy(initial_time,final_time,plant,'DAY',1)
                print todays_energy
            except Exception as exception:
                print("Error in getting the energy values" + str(exception))
            try:
                if todays_energy and len(todays_energy) > 0:
                    #energy_values = [item['energy'] for item in todays_energy]
                    if len(todays_energy) > 0:
                        today_energy_value = todays_energy[len(todays_energy)-1]['energy']
                    else:
                        today_energy_value = 0.0
                else:
                    today_energy_value = 0.0
            except Exception as exception:
                print str(exception)
                today_energy_value = 0.0

            # get the predicted energy value
            try:
                todays_predicted_energy = get_expected_energy(str(plant.slug), 'PLANT', initial_time, final_time)
                print todays_predicted_energy
            except Exception as exception:
                print str(exception)
                todays_predicted_energy = None

            if todays_predicted_energy:
                today_predicted_value = todays_predicted_energy[0]
                today_predicted_lower_bound = todays_predicted_energy[1]
                today_predicted_upper_bound = todays_predicted_energy[2]
            else:
                today_predicted_value = 0.0
                today_predicted_lower_bound = 0.0
                today_predicted_upper_bound = 0.0

            print initial_time, today_energy_value, today_predicted_value, today_predicted_lower_bound, today_predicted_upper_bound
            try:
                daily_energy_entry = HistoricEnergyValuesWithPrediction.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                      count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                      identifier=plant.slug,
                                                                      ts=initial_time)
                daily_energy_entry.update(energy=today_energy_value,
                                          predicted_energy=today_predicted_value,
                                          lower_bound=today_predicted_lower_bound,
                                          upper_bound=today_predicted_upper_bound)
            except Exception as exception:
                print str(exception)
                energy_entry = HistoricEnergyValuesWithPrediction.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=plant.slug,
                                                                   ts=initial_time,
                                                                   energy=today_energy_value,
                                                                   predicted_energy=today_predicted_value,
                                                                   lower_bound=today_predicted_lower_bound,
                                                                   upper_bound=today_predicted_upper_bound)
                energy_entry.save()
            starttime = starttime + datetime.timedelta(days=1)
    except Exception as exception:
        print str(exception)


def historic_pr_recalculate(starttime, endtime, plant):
    try:
        try:
            starttime = pytz.utc.localize(starttime)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        try:
            endtime = pytz.utc.localize(endtime)
            endtime = endtime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        while endtime>starttime:
            initial_time = starttime.replace(hour=0, minute=0, second= 0, microsecond=0)
            final_time = starttime.replace(hour=23, minute=59, second=59, microsecond=59)
            pr_value = calculate_pr(initial_time,final_time,plant)
            print initial_time, pr_value
            try:
                daily_pr_entry = PerformanceRatioTable.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                                   ts=initial_time)
                daily_pr_entry.update(performance_ratio=pr_value)
            except:
                daily_pr_entry = PerformanceRatioTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                      count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                      identifier=plant.metadata.plantmetasource.sourceKey,
                                                                      ts=initial_time,
                                                                      performance_ratio=pr_value)
                daily_pr_entry.save()
            starttime = starttime + datetime.timedelta(days=1)
    except Exception as exception:
        print str(exception)


def historic_cuf_recalculate(starttime, endtime, plant):
    try:
        try:
            starttime = pytz.utc.localize(starttime)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        try:
            endtime = pytz.utc.localize(endtime)
            endtime = endtime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        while endtime>starttime:
            initial_time = starttime.replace(hour=0, minute=0, second= 0, microsecond=0)
            final_time = starttime.replace(hour=23, minute=59, second=59, microsecond=59)
            cuf_value = calculate_CUF(initial_time,final_time,plant)
            print initial_time, cuf_value
            try:
                daily_cuf_entry = CUFTable.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                       identifier=plant.metadata.plantmetasource.sourceKey,
                                                       ts=initial_time)
                daily_cuf_entry.update(CUF=cuf_value)
            except:
                daily_cuf_entry = CUFTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                          count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                          identifier=plant.metadata.plantmetasource.sourceKey,
                                                          ts=initial_time,
                                                          CUF=cuf_value)
                daily_cuf_entry.save()
            starttime = starttime + datetime.timedelta(days=1)
    except Exception as exception:
        print str(exception)


def historic_sy_recalculate(starttime, endtime, plant):
    try:
        try:
            starttime = pytz.utc.localize(starttime)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        try:
            endtime = pytz.utc.localize(endtime)
            endtime = endtime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        while endtime>starttime:
            initial_time = starttime.replace(hour=0, minute=0, second= 0, microsecond=0)
            final_time = starttime.replace(hour=23, minute=59, second=59, microsecond=59)
            sy_value = calculate_specific_yield(initial_time,final_time,plant)
            print initial_time, sy_value
            try:
                daily_sy_entry = SpecificYieldTable.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                               identifier=plant.metadata.plantmetasource.sourceKey,
                                                               ts=initial_time)
                daily_sy_entry.update(specific_yield=daily_sy_entry)
            except:
                daily_sy_entry = SpecificYieldTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                                   ts=initial_time,
                                                                   specific_yield=sy_value)
                daily_sy_entry.save()
            starttime = starttime + datetime.timedelta(days=1)
    except Exception as exception:
        print str(exception)

def historic_insolation_recalculate(starttime, endtime, plant):
    try:
        try:
            starttime = pytz.utc.localize(starttime)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        try:
            endtime = pytz.utc.localize(endtime)
            endtime = endtime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        while endtime>starttime:
            initial_time = starttime.replace(hour=0, minute=0, second= 0, microsecond=0)
            final_time = starttime.replace(hour=23, minute=59, second=59, microsecond=59)
            insolation = get_kwh_per_meter_square_value(initial_time,final_time,plant)
            print initial_time, insolation
            try:
                daily_insolation_entry = KWHPerMeterSquare.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                       identifier=plant.metadata.plantmetasource.sourceKey,
                                                                       ts=initial_time)
                daily_insolation_entry.update(value=daily_insolation_entry)
            except:
                daily_insolation_entry = KWHPerMeterSquare.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                          count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                          identifier=plant.metadata.plantmetasource.sourceKey,
                                                                          ts=initial_time,
                                                                          value=insolation)
                daily_insolation_entry.save()
            starttime = starttime + datetime.timedelta(days=1)
    except Exception as exception:
        print str(exception)


def historic_plant_summary_recalculate(starttime, endtime, plant):
    try:
        try:
            starttime = pytz.utc.localize(starttime)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        try:
            endtime = pytz.utc.localize(endtime)
            endtime = endtime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        while endtime>starttime:
            initial_time = starttime.replace(hour=0, minute=0, second= 0, microsecond=0)
            final_time = starttime.replace(hour=23, minute=59, second=59, microsecond=59)

            try:
                daily_energy_entry = HistoricEnergyValues.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                      count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                      identifier=plant.slug,
                                                                      ts=initial_time)
                today_energy_value = daily_energy_entry.energy
            except:
                today_energy_value = 0.0
            print "energy", today_energy_value

            try:
                daily_pr_entry = PerformanceRatioTable.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                                   ts=initial_time)
                today_pr_value = daily_pr_entry.performance_ratio
            except Exception as exception:
                print str(exception)
                today_pr_value = 0.0
            print "PR", today_pr_value

            try:
                daily_cuf_entry = CUFTable.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                       identifier=plant.metadata.plantmetasource.sourceKey,
                                                       ts=initial_time)
                today_cuf_value = daily_cuf_entry.CUF
            except:
                today_cuf_value = 0.0
            print "CUF", today_cuf_value

            try:
                daily_sy_entry = SpecificYieldTable.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                identifier=plant.metadata.plantmetasource.sourceKey,
                                                                ts=initial_time)
                today_sy_value = daily_sy_entry.specific_yield
            except:
                today_sy_value = 0.0
            print "Specific Yield", today_sy_value

            try:
                daily_insolation_entry = KWHPerMeterSquare.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                       count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                       identifier=plant.metadata.plantmetasource.sourceKey,
                                                                       ts=initial_time)
                today_insolation_value = daily_insolation_entry.value
            except:
                today_insolation_value = 0.0
            print "Insolation", today_insolation_value

            try:
                max_value_entry = MaxValuesTable.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                             count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                             identifier=plant.metadata.plantmetasource.sourceKey,
                                                             ts=initial_time)
                max_irradiance = max_value_entry.max_irradiance
                inverter_generation = max_value_entry.inverters_generation
                print "max_irradiance", max_irradiance
                print "inverter_generation", inverter_generation
            except:
                today_insolation_value = 0.0

            try:
                daily_summary_entry = PlantSummaryDetails.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                      count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                      identifier=plant.slug,
                                                                      ts=initial_time)
                daily_summary_entry.update(generation=today_energy_value,
                                           performance_ratio=today_pr_value,
                                           cuf=today_cuf_value,
                                           specific_yield=today_sy_value,
                                           average_irradiation=today_insolation_value,
                                           max_irradiance=max_irradiance,
                                           inverter_generation=inverter_generation)
            except Exception as exception:
                print str(exception)
                daily_summary_entry = PlantSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                         count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                         identifier=plant.slug,
                                                                         ts=initial_time)
                daily_summary_entry.update(generation=today_energy_value,
                                           performance_ratio=today_pr_value,
                                           cuf=today_cuf_value,
                                           specific_yield=today_sy_value,
                                           average_irradiation=today_insolation_value,
                                           max_irradiance=max_irradiance,
                                           inverter_generation=inverter_generation)
            starttime = starttime + datetime.timedelta(days=1)
    except Exception as exception:
        print str(exception)

def historic_inverters_summary_recalculate(starttime, endtime, plant):
    try:
        try:
            starttime = pytz.utc.localize(starttime)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        try:
            endtime = pytz.utc.localize(endtime)
            endtime = endtime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        inverters = plant.independent_inverter_units.all()
        try:
            operational_unit = TOTAL_OPERATIONAL_HOURS_UNITS[str(plant.slug)]
            operational_unit_factor = TOTAL_OPERATIONAL_HOURS_UNITS_CONVERSION[operational_unit]
        except:
            operational_unit_factor = 3600
        while endtime>starttime:
            initial_time = starttime.replace(hour=0, minute=0, second= 0, microsecond=0)
            final_time = starttime.replace(hour=23, minute=59, second=59, microsecond=59)
            initial_time_operational = initial_time.replace(hour=0, minute=30, second= 0, microsecond=0)
            energy_values = get_minutes_aggregated_energy(initial_time, final_time, plant, 'DAY', 1, split=True, meter_energy=False)
            if energy_values and len(energy_values)>0:
                for inverter in inverters:
                    try:
                        inverter_energy = energy_values[str(inverter.name)][0]['energy']
                    except:
                        inverter_energy = 0.0

                    # total working hours
                    total_working_hours = 0.0
                    try:
                        working_hours = ValidDataStorageByStream.objects.filter(source_key=str(inverter.sourceKey),
                                                                                stream_name='TOTAL_OPERATIONAL_HOURS',
                                                                                timestamp_in_data__gte=initial_time_operational,
                                                                                timestamp_in_data__lte=final_time)
                        if len(working_hours)>0:
                            try:
                                total_working_hours = (float(working_hours[0].stream_value) - float(working_hours[len(working_hours)-1].stream_value))/operational_unit_factor
                            except:
                                total_working_hours = 0.0
                    except Exception as exception:
                        print(str(exception))

                    try:
                        max_value_entry = MaxValuesTable.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                     count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                     identifier=inverter.sourceKey,
                                                                     ts=initial_time)
                        max_dc_power = max_value_entry.max_dc_power
                        max_ac_power = max_value_entry.max_ac_power
                    except:
                        max_dc_power = None
                        max_ac_power = None

                    print initial_time, inverter.name + " generation : " ,  inverter_energy
                    print initial_time, inverter.name + " working hours : " ,  total_working_hours
                    print initial_time, inverter.name + " max_dc_power : ", max_dc_power
                    print initial_time, inverter.name + " max_ac_power : ", max_ac_power

                    try:
                        daily_energy_entry = PlantDeviceSummaryDetails.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                   identifier=str(inverter.sourceKey),
                                                                                   ts=initial_time)
                        try:
                            daily_energy_entry.update(generation=inverter_energy,
                                                      total_working_hours=total_working_hours,
                                                      max_dc_power=max_dc_power,
                                                      max_ac_power=max_ac_power)
                        except:
                            daily_energy_entry.update(generation=inverter_energy)
                    except Exception as exception:
                        try:
                            energy_entry = PlantDeviceSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                    identifier=str(inverter.sourceKey),
                                                                                    ts=initial_time,
                                                                                    generation=inverter_energy,
                                                                                    total_working_hours=total_working_hours,
                                                                                    max_dc_power=max_dc_power,
                                                                                    max_ac_power=max_ac_power)
                            energy_entry.save()
                        except:
                            energy_entry = PlantDeviceSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                    identifier=str(inverter.sourceKey),
                                                                                    ts=initial_time,
                                                                                    generation=inverter_energy,
                                                                                    max_dc_power=max_dc_power,
                                                                                    max_ac_power=max_ac_power)
                            energy_entry.save()
            starttime = starttime + datetime.timedelta(days=1)
    except Exception as exception:
        print str(exception)

def historic_meters_summary_recalculate(starttime, endtime, plant):
    try:
        try:
            starttime = pytz.utc.localize(starttime)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        try:
            endtime = pytz.utc.localize(endtime)
            endtime = endtime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        meters = plant.energy_meters.all()
        while endtime>starttime:
            initial_time = starttime.replace(hour=0, minute=0, second= 0, microsecond=0)
            final_time = starttime.replace(hour=23, minute=59, second=59, microsecond=59)
            energy_values = get_minutes_aggregated_energy(initial_time, final_time, plant, 'DAY', 1, split=True, meter_energy=True, all_meters=True)
            if energy_values and len(energy_values)>0:
                for meter in meters:
                    try:
                        meter_energy = energy_values[str(meter.name)][0]['energy']
                    except:
                        meter_energy = 0.0
                    print initial_time, meter_energy
                    try:
                        daily_energy_entry = PlantDeviceSummaryDetails.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                   identifier=str(meter.sourceKey),
                                                                                   ts=initial_time,
                                                                                   generation=meter_energy)
                        daily_energy_entry.update(generation=meter_energy)
                    except Exception as exception:
                        energy_entry = PlantDeviceSummaryDetails.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                identifier=str(meter.sourceKey),
                                                                                ts=initial_time,
                                                                                generation=meter_energy)
                        energy_entry.save()
            starttime = starttime + datetime.timedelta(days=1)
    except Exception as exception:
        print str(exception)

def max_values_recalculation(starttime, endtime, plant):
    try:
        try:
            starttime = pytz.utc.localize(starttime)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        try:
            endtime = pytz.utc.localize(endtime)
            endtime = endtime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        while endtime>starttime:
            initial_time = starttime.replace(hour=0, minute=0, second= 0, microsecond=0)
            final_time = starttime.replace(hour=23, minute=59, second=59, microsecond=59)

            max_irradiance = get_max_irradiance(initial_time, final_time, plant)
            inverters_energy = get_minutes_aggregated_energy(initial_time, final_time, plant, 'DAY', 1, False, False)
            try:
                if inverters_energy and len(inverters_energy) > 0:
                    #energy_values = [item['energy'] for item in todays_energy]
                    if len(inverters_energy) > 0:
                        today_energy_value = inverters_energy[len(inverters_energy)-1]['energy']
                    else:
                        today_energy_value = 0.0
                else:
                    today_energy_value = 0.0
            except Exception as exception:
                print str(exception)
                today_energy_value = 0.0

            try:
                max_value = MaxValuesTable.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                        count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                        identifier=plant.metadata.plantmetasource.sourceKey,
                                                        ts=initial_time)

                max_value.update(max_irradiance=max_irradiance,
                                 inverters_generation=today_energy_value)
            except:
                max_value = MaxValuesTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                          count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                          identifier=plant.metadata.plantmetasource.sourceKey,
                                                          ts=initial_time,
                                                          max_irradiance=max_irradiance,
                                                          inverters_generation=today_energy_value)
                max_value.save()
            starttime = starttime + datetime.timedelta(days=1)
    except Exception as exception:
        print str(exception)

def inverters_max_values_recalculation(starttime, endtime, plant):
    try:
        try:
            starttime = pytz.utc.localize(starttime)
            starttime = starttime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        try:
            endtime = pytz.utc.localize(endtime)
            endtime = endtime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        except Exception as exception:
            print str(exception)
            return
        while endtime>starttime:
            initial_time = starttime.replace(hour=0, minute=0, second= 0, microsecond=0)
            final_time = starttime.replace(hour=23, minute=59, second=59, microsecond=59)

            # Max DC Power values for Inverters
            max_dc_power_values = get_max_dc_power_inverter_wise(initial_time, final_time, plant)

            # Max AC power values for inverters
            max_active_power_values = get_max_active_power_inverter_wise(initial_time, final_time, plant)

            inverters = plant.independent_inverter_units.all()

            for inverter in inverters:
                try:
                    max_inverter_dc_power = max_dc_power_values[str(inverter.name)]
                    max_inverter_ac_power  = max_active_power_values[str(inverter.name)]
                except Exception as exception:
                    print str(exception)
                    max_inverter_dc_power = None
                    max_inverter_ac_power = None

                try:
                    max_value = MaxValuesTable.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                            count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                            identifier=inverter.sourceKey,
                                                            ts=initial_time)

                    max_value.update(max_dc_power=max_inverter_dc_power,
                                     max_ac_power=max_inverter_ac_power)
                except:
                    max_value = MaxValuesTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                              count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                              identifier=inverter.sourceKey,
                                                              ts=initial_time,
                                                              max_dc_power=max_inverter_dc_power,
                                                              max_ac_power=max_inverter_ac_power)
                    max_value.save()
            starttime = starttime + datetime.timedelta(days=1)
    except Exception as exception:
        print str(exception)

def historic_values_recalculation(starttime, endtime, plant):
    try:
        historic_energy_recalculate(starttime, endtime, plant)
        historic_energy_with_prediction_recalculate(starttime, endtime, plant)
        historic_pr_recalculate(starttime, endtime, plant)
        historic_cuf_recalculate(starttime, endtime, plant)
        historic_sy_recalculate(starttime, endtime, plant)
        historic_insolation_recalculate(starttime, endtime, plant)
        max_values_recalculation(starttime, endtime, plant)
        inverters_max_values_recalculation(starttime, endtime, plant)
        historic_plant_summary_recalculate(starttime, endtime, plant)
        historic_inverters_summary_recalculate(starttime, endtime, plant)
        if len(plant.energy_meters.all())>0:
            historic_meters_summary_recalculate(starttime, endtime, plant)
    except Exception as exception:
        print str(exception)


def calculate_historic_values(plant_slug, starttime, endtime):
    try:
        plant = SolarPlant.objects.get(slug=plant_slug)
        historic_values_recalculation(parser.parse(starttime),
                                      parser.parse(endtime),
                                      plant)
    except:
        return


# from_plants_slugs_list = ['lawcollege', 'abeedacollege', 'dentalcollege', 'hotelmgt', 'mbacollege']
# to_plant_slug = 'azamcampus'
from django.db import transaction


@transaction.atomic()
def merge_plants(to_plant_slug, from_plants_slugs_list):
    # update inverters, meters, ajbs, gateways, virtual_gateways for each group
    # add number of panels, panels area, fix efficiency
    to_plant = SolarPlant.objects.get(slug=to_plant_slug)
    for plant in SolarPlant.objects.filter(slug__in=from_plants_slugs_list):
        for group in plant.solar_groups.all():
            # update plant
            assert(group.plant == plant)
            group.plant = to_plant
            group.save()
            # update inverter
            for inverter in group.groupIndependentInverters.all():
                assert(inverter.plant == plant)
                inverter.plant = to_plant
                inverter.save()
            # update AJBs
            for ajb in group.groupAJBs.all():
                assert(ajb.plant == plant)
                ajb.plant = to_plant
                ajb.save()
            # update Meters
            for em in group.groupEnergyMeters.all():
                assert(em.plant == plant)
                em.plant = to_plant
                em.save()
            # update Gateway sources
            for gateway in group.groupGatewaySources.all():
                assert(gateway.plant == plant)
                gateway.plant = to_plant
                gateway.save()
            # update virtual gateways
            for vg in VirtualGateway.objects.filter(solar_group = group):
                assert(vg.plant == plant)
                vg.plant = to_plant
                vg.save()

        pm = to_plant.metadata
        pm.PV_panel_area += plant.metadata.PV_panel_area
        pm.no_of_panels += plant.metadata.no_of_panels
        pm.save()

        to_plant.capacity += plant.capacity
        to_plant.save()

        #TODO manage sensors
        #TODO calculate_historic_values(plant_slug, starttime, endtime)


# plant = SolarPlant.objects.get(slug="azamcampus")
# from_groups_gateways_keys = ['OwnxOQ18qICZIiY', 'HFKrcl0a5ZFWnPz']
# to_group_name = 'MCE Society'
# group_slug = 'mcesociety'

# from_groups_gateways_keys = ['6KuBnOp9XLZH8I9', 'oy4VBlakgTtwiQy', '7Ixx70eMMHQonsX']
# to_group_name = 'Rangoonwala College'
# group_slug = 'rangoonwala-college'

from django.db import transaction


@transaction.atomic()
def merge_groups(plant, from_groups_gateways_keys, to_group_name, group_slug):
    # update inverters, meters, ajbs, gateways, virtual_gateways for each group
    # add number of panels, panels area, fix efficiency
    to_group = SolarGroup.objects.create(name=to_group_name,
                                         plant=plant,
                                         slug=group_slug,
                                         isActive=True,
                                         user=plant.independent_inverter_units.all()[0].user,
                                         displayName=to_group_name)

    for group in SolarGroup.objects.filter(groupGatewaySources__in=GatewaySource.objects.filter(sourceKey__in=from_groups_gateways_keys)):
        # update plant
        assert(group.plant == plant)
        # update inverter
        for inverter in group.groupIndependentInverters.all():
            assert(inverter.plant == plant)
            to_group.groupIndependentInverters.add(inverter)

        # update AJBs
        for ajb in group.groupAJBs.all():
            assert(ajb.plant == plant)
            to_group.groupAJBs.add(ajb)

        # update Meters
        for em in group.groupEnergyMeters.all():
            assert(em.plant == plant)
            to_group.groupEnergyMeters.add(em)

        # update Gateway sources
        for gateway in group.groupGatewaySources.all():
            assert(gateway.plant == plant)
            to_group.groupGatewaySources.add(gateway)

        # update IO Sensors
        for io_sensor in group.groupIOSensors.all():
            assert(gateway.plant == plant)
            to_group.groupIOSensors.add(io_sensor)

        # update virtual gateways
        for vg in VirtualGateway.objects.filter(solar_group = group):
            assert(vg.plant == plant)
            vg.solar_group = to_group
            vg.save()

        to_group.save()
        group.delete()
        #TODO manage sensors

    device_id = []
    for group in SolarGroup.objects.filter(groupGatewaySources__in=GatewaySource.objects.filter(sourceKey__in=from_groups_gateways_keys)):
        if group.data_logger_device_id is not None:
            device_id.append(str(group.data_logger_device_id))

    to_group.data_logger_device_id = ",".join(device_id)
    to_group.save()



