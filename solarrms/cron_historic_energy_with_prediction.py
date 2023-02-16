import datetime
from solarrms.models import SolarPlant, PlantMetaSource, HistoricEnergyValuesWithPrediction
from django.utils import timezone
from django.conf import settings
import pytz
from solarrms.solarutils import get_aggregated_energy, get_energy_meter_values, get_expected_energy,\
    get_minutes_aggregated_energy

start_date = "2017-06-01 00:00:00"


def compute_historical_energy_values_with_prediction():
    print('Historical energy values cronjob started {0}'.format(str(datetime.datetime.now())))
    try:
        plants = SolarPlant.objects.all()
        for plant in plants:
            print str("computing for plant : " + str(plant.slug))
            if plant.isOperational and plant.metadata.plantmetasource:
                try:
                    current_time = timezone.now()
                    current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                except Exception as exc:
                    print("Error in converting the timezone" + str(exc))

                # store daily energy values
                historic_last_entry = HistoricEnergyValuesWithPrediction.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                        count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                        identifier=plant.slug).limit(1).values_list('ts')

                if historic_last_entry:
                    last_entry_values = [item[0] for item in historic_last_entry]
                    last_entry = last_entry_values[0]
                    if last_entry.tzinfo is None:
                        last_entry = pytz.utc.localize(last_entry)
                        last_entry = last_entry.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                        print(last_entry)
                else:
                    last_entry = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                    if last_entry.tzinfo is None:
                        last_entry = pytz.utc.localize(last_entry)
                        last_entry = last_entry.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                        print(last_entry)

                duration = (current_time - last_entry)
                duration_days = duration.days
                print duration_days
                loop_count = 0
                last_entry_daily = last_entry
                last_entry_monthly = last_entry
                # calculate the daily energy values
                while loop_count < duration_days:
                    initial_time = last_entry_daily.replace(hour=0, minute=0, second= 0, microsecond=0)
                    final_time = last_entry_daily.replace(hour=21, minute=59, second=59, microsecond=59)
                    try:
                        todays_energy = get_minutes_aggregated_energy(initial_time,final_time,plant,'DAY',1)
                    except Exception as exception:
                        print("Error in getting the energy values" + str(exception))
                        todays_energy = None
                    if todays_energy and len(todays_energy) > 0:
                        energy_values = [item['energy'] for item in todays_energy]
                        if len(energy_values) > 0:
                            today_energy_value = energy_values[len(energy_values)-1]
                        else:
                            today_energy_value = 0.0
                    else:
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
                        energy_entry = HistoricEnergyValuesWithPrediction.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                         count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                         identifier=plant.slug,
                                                                                         ts=initial_time,
                                                                                         energy=today_energy_value,
                                                                                         predicted_energy=today_predicted_value,
                                                                                         lower_bound=today_predicted_lower_bound,
                                                                                         upper_bound=today_predicted_upper_bound)
                        energy_entry.save()
                    last_entry_daily = last_entry_daily + datetime.timedelta(days=1)
                    duration_days -= 1

                if duration_days == 0:
                    initial_time = current_time.replace(hour=0, minute=0, second= 0, microsecond=0)
                    final_time = current_time.replace(hour=21, minute=59, second=59, microsecond=59)
                    month_start_day = initial_time.replace(day=1)
                    month_end_day = final_time

                    todays_energy = get_minutes_aggregated_energy(initial_time,final_time,plant,'DAY',1)
                    if todays_energy and len(todays_energy) > 0:
                        energy_values = [item['energy'] for item in todays_energy]
                        if len(energy_values) > 0:
                            today_energy_value = energy_values[len(energy_values)-1]
                        else:
                            today_energy_value = 0.0
                    else:
                        today_energy_value = 0.0


                    try:
                        todays_predicted_energy = get_expected_energy(str(plant.slug), 'PLANT', initial_time, final_time)
                        print todays_predicted_energy
                    except Exception as exception:
                        print(str(exception))
                        todays_predicted_energy = None

                    if todays_predicted_energy:
                        today_predicted_value = todays_predicted_energy[0]
                        today_predicted_lower_bound = todays_predicted_energy[1]
                        today_predicted_upper_bound = todays_predicted_energy[2]
                    else:
                        today_predicted_value = 0.0
                        today_predicted_lower_bound = 0.0
                        today_predicted_upper_bound = 0.0

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
                        energy_entry = HistoricEnergyValuesWithPrediction.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                         count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                         identifier=plant.slug,
                                                                                         ts=initial_time,
                                                                                         energy=today_energy_value,
                                                                                         predicted_energy=today_predicted_value,
                                                                                         lower_bound=today_predicted_lower_bound,
                                                                                         upper_bound=today_predicted_upper_bound)
                        energy_entry.save()


                    # get monthly energy values
                    try:
                        monthly_historical_energy_values = HistoricEnergyValuesWithPrediction.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                                             count_time_period=86400,
                                                                                                             identifier=str(plant.slug),
                                                                                                             ts__gte=month_start_day,
                                                                                                             ts__lte=month_end_day)
                    except Exception as exception:
                        print("Error in getting historical energy values : " + str(exception))

                    # calculate total energy of the month
                    try:
                        total_monthly_energy_value = 0.0
                        for monthly_energy_value in monthly_historical_energy_values:
                            total_monthly_energy_value += float(monthly_energy_value.energy)
                    except Exception as exception:
                        print("Error in calculating the total energy of the month : " + str(exception))
                        pass
                    try:
                        monthly_energy_entry = HistoricEnergyValuesWithPrediction.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                              count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                              identifier=plant.slug,
                                                                                              ts=month_start_day)
                        monthly_energy_entry.update(energy=total_monthly_energy_value)
                    except:
                        energy_entry = HistoricEnergyValuesWithPrediction.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                         count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                         identifier=plant.slug,
                                                                                         ts=month_start_day,
                                                                                         energy=total_monthly_energy_value)
                        energy_entry.save()

                monthly_duration = (current_time - last_entry)
                monthly_duration_days = monthly_duration.days
                monthly_loop_count = 0
                while monthly_loop_count < monthly_duration_days:
                    print str("computing past monthly energy values for plant : " + str(plant.slug))
                    initial_time = last_entry_monthly.replace(hour=0, minute=0, second= 0, microsecond=0)
                    final_time = last_entry_monthly.replace(hour=23, minute=59, second=59, microsecond=59)
                    month_start_day = initial_time.replace(day=1)
                    month_end_day = final_time
                    # get monthly energy values
                    try:
                        monthly_historical_energy_values = HistoricEnergyValuesWithPrediction.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                                             count_time_period=86400,
                                                                                                             identifier=str(plant.slug),
                                                                                                             ts__gte=month_start_day,
                                                                                                             ts__lte=month_end_day)
                    except Exception as exception:
                        print("Error in getting historical energy values : " + str(exception))

                    # calculate total energy of the month
                    try:
                        total_monthly_energy_value = 0.0
                        for monthly_energy_value in monthly_historical_energy_values:
                            total_monthly_energy_value += float(monthly_energy_value.energy)
                    except Exception as exception:
                        print("Error in calculating the total energy of the month : " + str(exception))
                        pass
                    try:
                        monthly_energy_entry = HistoricEnergyValuesWithPrediction.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                              count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                              identifier=plant.slug,
                                                                                              ts=month_start_day)
                        monthly_energy_entry.update(energy=total_monthly_energy_value)
                    except:
                        energy_entry = HistoricEnergyValuesWithPrediction.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                         count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                         identifier=plant.slug,
                                                                                         ts=month_start_day,
                                                                                         energy=total_monthly_energy_value)
                        energy_entry.save()
                    last_entry_monthly = last_entry_monthly + datetime.timedelta(days=1)
                    monthly_duration_days -= 1

                if monthly_duration_days == 0:
                    print str("computing current monthly energy values for plant : " + str(plant.slug))
                    initial_time = last_entry_monthly.replace(hour=0, minute=0, second= 0, microsecond=0)
                    final_time = last_entry_monthly.replace(hour=23, minute=59, second=59, microsecond=59)
                    month_start_day = initial_time.replace(day=1)
                    month_end_day = final_time
                    # get monthly energy values
                    try:
                        monthly_historical_energy_values = HistoricEnergyValuesWithPrediction.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                                                             count_time_period=86400,
                                                                                                             identifier=str(plant.slug),
                                                                                                             ts__gte=month_start_day,
                                                                                                             ts__lte=month_end_day)
                    except Exception as exception:
                        print("Error in getting historical energy values : " + str(exception))

                    # calculate total energy of the month
                    try:
                        total_monthly_energy_value = 0.0
                        for monthly_energy_value in monthly_historical_energy_values:
                            total_monthly_energy_value += float(monthly_energy_value.energy)
                    except Exception as exception:
                        print("Error in calculating the total energy of the month : " + str(exception))
                        pass
                    try:
                        monthly_energy_entry = HistoricEnergyValuesWithPrediction.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                              count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                              identifier=plant.slug,
                                                                                              ts=month_start_day)
                        monthly_energy_entry.update(energy=total_monthly_energy_value)
                    except:
                        energy_entry = HistoricEnergyValuesWithPrediction.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                         count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                                                                                         identifier=plant.slug,
                                                                                         ts=month_start_day,
                                                                                         energy=total_monthly_energy_value)
                        energy_entry.save()

                # store the monthly energy generated
                # monthly_initial_date = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                # if monthly_initial_date.tzinfo is None:
                #     monthly_initial_date = pytz.utc.localize(monthly_initial_date)
                #     monthly_initial_date = monthly_initial_date.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                #
                # energy_values_monthly = get_minutes_aggregated_energy(monthly_initial_date, current_time, plant, "MONTH",1)
                # if energy_values_monthly and len(energy_values_monthly)>0:
                #     for value in energy_values_monthly:
                #         try:
                #             monthly_energy_entry = HistoricEnergyValuesWithPrediction.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                #                                                                                   count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                #                                                                                   identifier=plant.slug,
                #                                                                                   ts=value['timestamp'])
                #             monthly_energy_entry.update(energy=value['energy'])
                #         except Exception as exception:
                #             energy_entry = HistoricEnergyValuesWithPrediction.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                #                                                                              count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                #                                                                              identifier=plant.slug,
                #                                                                              ts=value['timestamp'],
                #                                                                              energy=value['energy'])
                #             energy_entry.save()
    except Exception as exception:
        print('Error{0}'.format(str(exception)))
