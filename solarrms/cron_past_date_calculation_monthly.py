import datetime
import pytz
import calendar
from django.conf import settings
from django.utils import timezone
from solarrms.models import HistoricEnergyValues, PerformanceRatioTable, CUFTable, SpecificYieldTable, \
    EnergyLossTableNew, KWHPerMeterSquare, PlantDownTime, AggregatedPlantParameters, PlantSummaryDetails, \
    PlantDeviceSummaryDetails, MaxValuesTable
from solarrms.settings import TOTAL_OPERATIONAL_HOURS_UNITS, TOTAL_OPERATIONAL_HOURS_UNITS_CONVERSION
from dataglen.models import ValidDataStorageByStream
from solarrms.solarutils import get_minutes_aggregated_energy


def compute_plant_montly_energy(startdatetime, enddatetime, plant):
    """
    get daily energy values
    :param startdatetime:
    :param enddatetime:
    :param plant:
    :return:
    """

    print "start compute_plant_montly_energy"
    try:
        historical_energy_values = HistoricEnergyValues.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                       count_time_period=86400,
                                                                       identifier=str(plant.slug),
                                                                       ts__gte=startdatetime, ts__lte=enddatetime)
    except Exception as exception:
        print "Error in getting historical energy values %s" % exception

    # calculate total energy of the month
    try:
        monthly_energy_value = 0.0
        for energy_value in historical_energy_values:
            monthly_energy_value += float(energy_value.energy)
    except Exception as exception:
        print "Error in calculating the total energy of the month : %s" % exception
        pass
    print "monthly_energy_value %s" % monthly_energy_value
    print "end compute_plant_montly_energy"
    return monthly_energy_value


def compute_plant_montly_pr(startdatetime, enddatetime, plant):
    """

    :param startdatetime:
    :param enddatetime:
    :param plant_slug:
    :return:
    """

    # get monthly PR
    print "start compute_plant_montly_pr"
    try:
        monthly_performance_ratio_values = PerformanceRatioTable.objects.filter(
            timestamp_type='BASED_ON_REQUEST_ARRIVAL', count_time_period=86400,
            identifier=str(plant.metadata.plantmetasource.sourceKey), ts__gte=startdatetime, ts__lte=enddatetime)
    except Exception as exception:
        print "Error in getting pr values: %s" % exception

    # calculate average pr of the month
    try:
        sum_pr = 0.0
        count_pr = 0
        for pr_value in monthly_performance_ratio_values:
            if float(pr_value.performance_ratio) > 0.0:
                sum_pr += float(pr_value.performance_ratio)
                count_pr += 1
        monthly_pr = float(sum_pr) / float(count_pr)
    except Exception as exception:
        print "Error in getting the average pr of the month : %s" % (exception)
        monthly_pr = 0.0
    print "compute_plant_montly_pr %s" % monthly_pr
    print "end compute_plant_montly_pr"
    return monthly_pr


def compute_plant_monthly_cuf(startdatetime, enddatetime, plant):
    """

    :param startdatetime:
    :param enddatetime:
    :param plant:
    :return:
    """

    print "start compute_plant_monthly_cuf"
    # monthly cuf values
    try:
        monthly_cuf_values = CUFTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL', count_time_period=86400,
                                                     identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                     ts__gte=startdatetime, ts__lte=enddatetime)
    except Exception as exception:
        print "Error in getting the cuf values : %s" % exception

    # calculate average cuf of the month
    try:
        sum_cuf = 0.0
        count_cuf = 0
        for monthly_cuf_value in monthly_cuf_values:
            if float(monthly_cuf_value.CUF) > 0.0:
                sum_cuf += float(monthly_cuf_value.CUF)
                count_cuf += 1
        monthly_cuf = float(sum_cuf) / float(count_cuf)
    except Exception as exception:
        print "Error in getting the average cuf of the month : %s" % exception
        monthly_cuf = 0.0
    print "compute_plant_monthly_cuf %s" % monthly_cuf
    print "end compute_plant_monthly_cuf"
    return monthly_cuf


def compute_plant_monthly_specific_yield(startdatetime, enddatetime, plant):
    """

    :param startdatetime:
    :param enddatetime:
    :param plant:
    :return:
    """

    print "start compute_plant_monthly_specific_yield"
    # monthly specific yield values
    try:
        monthly_specific_yield = SpecificYieldTable.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                   count_time_period=86400, identifier=str(
                plant.metadata.plantmetasource.sourceKey), ts__gte=startdatetime, ts__lte=enddatetime)
    except Exception as exception:
        print "Error in getting the specific yield values : %s" % exception

    # calculate specific yield values per month
    try:
        sum_specific_yield_per_month = 0.0
        for monthly_yield_value in monthly_specific_yield:
            if float(monthly_yield_value.specific_yield) > 0.0:
                sum_specific_yield_per_month += float(monthly_yield_value.specific_yield)
    except Exception as exception:
        print "Error in getting the specific yield per month : %s" % exception
    print "compute_plant_monthly_specific_yield %s" % sum_specific_yield_per_month
    print "end compute_plant_monthly_specific_yield"
    return sum_specific_yield_per_month


def compute_plant_enegry_losses(startdatetime, enddatetime, plant):
    """

    :param startdatetime:
    :param enddatetime:
    :param plant:
    :return:
    """

    # monthly energy losses
    print "start compute_plant_enegry_losses"
    try:
        monthly_energy_losses = EnergyLossTableNew.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                  count_time_period=86400, identifier=str(
                plant.metadata.plantmetasource.sourceKey), ts__gte=startdatetime, ts__lte=enddatetime)
    except Exception as exception:
        print "Error in getting the energy losses values: %s" % exception

    # calculate monthly losses
    total_monthly_dc_loss = 0.0
    total_monthly_conversion_loss = 0.0
    total_monthly_ac_loss = 0.0
    for monthly_loss in monthly_energy_losses:
        try:
            if monthly_loss.dc_energy_loss is not None and float(monthly_loss.dc_energy_loss) > 0:
                total_monthly_dc_loss += monthly_loss.dc_energy_loss
            if monthly_loss.conversion_loss is not None and float(monthly_loss.conversion_loss) > 0:
                total_monthly_conversion_loss += monthly_loss.conversion_loss
            if monthly_loss.ac_energy_loss is not None and float(monthly_loss.ac_energy_loss) > 0:
                total_monthly_ac_loss += monthly_loss.ac_energy_loss
        except:
            continue
    print "total_monthly_dc_loss %s, total_monthly_conversion_loss %s, total_monthly_ac_loss %s" % (
        total_monthly_dc_loss, total_monthly_conversion_loss, total_monthly_ac_loss)
    print "end compute_plant_enegry_losses"
    return total_monthly_dc_loss, total_monthly_conversion_loss, total_monthly_ac_loss


def compute_plant_availability(startdatetime, enddatetime, plant):
    """

    :param startdatetime:
    :param enddatetime:
    :param plant:
    :return:
    """

    # monthly equipment availability
    print "start compute_plant_availability"
    total_monthly_equipment_down_time = 0
    inverters = plant.independent_inverter_units.all()
    for inverter in inverters:
        monthly_equipment_down_time = PlantDownTime.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                   count_time_period=86400,
                                                                   identifier=str(inverter.sourceKey),
                                                                   ts__gte=startdatetime, ts__lte=enddatetime)
        if len(monthly_equipment_down_time) > 0:
            for inverter_down_time in monthly_equipment_down_time:
                try:
                    total_monthly_equipment_down_time += int(inverter_down_time.down_time)
                except:
                    pass
    try:
        average_monthly_down_time = float(total_monthly_equipment_down_time / len(inverters))
    except:
        average_monthly_down_time = 0

    try:
        final_equipment_down_time = ((11 * 60 * len(monthly_equipment_down_time) - average_monthly_down_time) / (
            11 * 60 * len(monthly_equipment_down_time))) * 100 if (
            len(monthly_equipment_down_time) and average_monthly_down_time) else 100
    except Exception as exception:
        print "final equipment down time %s" % exception
        final_equipment_down_time = 100

    # monthly grid availability
    monthly_grid_down_time = PlantDownTime.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                          count_time_period=86400,
                                                          identifier=str(plant.metadata.plantmetasource.sourceKey),
                                                          ts__gte=startdatetime, ts__lte=enddatetime)

    total_monthly_down_time = 0.0
    for down_time in monthly_grid_down_time:
        total_monthly_down_time += down_time.down_time
    try:
        average_monthly_down_time = ((11 * 60 * len(monthly_grid_down_time) - total_monthly_down_time) / (
            11 * 60 * len(monthly_grid_down_time))) * 100 if (
            len(monthly_grid_down_time) and total_monthly_down_time) else 100
    except Exception as exception:
        print "average_monthly_down_time" % exception
        average_monthly_down_time = 100
    print "final_equipment_down_time %s, average_monthly_down_time %s" % (
        final_equipment_down_time, average_monthly_down_time)
    print "end compute_plant_availability"
    return final_equipment_down_time, average_monthly_down_time


def compute_plant_average_insolation(startdatetime, enddatetime, plant):
    """

    :param startdatetime:
    :param enddatetime:
    :param plant:
    :return:
    """
    print "start compute_plant_average_insolation"
    # monthly average irradiation values
    monthly_irradiation_values = KWHPerMeterSquare.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                  count_time_period=86400, identifier=str(
            plant.metadata.plantmetasource.sourceKey), ts__gte=startdatetime, ts__lte=enddatetime)

    # calculate average insolation of the month
    try:
        sum_insolation = 0.0
        count_insolation = 0
        for monthly_insolation_value in monthly_irradiation_values:
            if float(monthly_insolation_value.value) > 0.0:
                sum_insolation += float(monthly_insolation_value.value)
                count_insolation += 1
        monthly_insolation = float(sum_insolation) / float(count_insolation)
    except Exception as exception:
        print "Error in getting the average insolation of the month : %s" % exception
        monthly_insolation = 0.0
    print "monthly_insolation %s" % monthly_insolation
    print "end compute_plant_average_insolation"
    return monthly_insolation


def compute_plant_aggregated_values(startdatetime, enddatetime, plant):
    """

    :param startdatetime:
    :param enddatetime:
    :param plant:
    :return:
    """
    # monthly aggregated values
    print "start compute_plant_aggregated_values"
    monthly_aggregated_values = AggregatedPlantParameters.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                         count_time_period=86400,
                                                                         identifier=str(plant.slug),
                                                                         ts__gte=startdatetime, ts__lte=enddatetime)

    # calculate average module temperature of the month
    try:
        sum_module_temperature = 0.0
        count_module_temperature = 0
        for value in monthly_aggregated_values:
            if float(value.average_module_temperature) > 0.0:
                sum_module_temperature += float(value.average_module_temperature)
                count_module_temperature += 1
        monthly_module_temperature = float(sum_module_temperature) / float(count_module_temperature)
    except Exception as exception:
        print "Error in getting the average module temperature of the month : %s" % exception
        monthly_module_temperature = None

    # calculate average ambient temperature of the month
    try:
        sum_ambient_temperature = 0.0
        count_ambient_temperature = 0
        for value in monthly_aggregated_values:
            if float(value.average_ambient_temperature) > 0.0:
                sum_ambient_temperature += float(value.average_ambient_temperature)
                count_ambient_temperature += 1
        monthly_ambient_temperature = float(sum_ambient_temperature) / float(count_ambient_temperature)
    except Exception as exception:
        print "Error in getting the average ambient temperature of the month : %s" % exception
        monthly_ambient_temperature = None

    # calculate average wind speed of the month
    try:
        sum_wind_speed = 0.0
        count_wind_speed = 0
        for value in monthly_aggregated_values:
            if float(value.average_windspeed) > 0.0:
                sum_wind_speed += float(value.average_windspeed)
                count_wind_speed += 1
        monthly_wind_speed = float(sum_wind_speed) / float(count_wind_speed)
    except Exception as exception:
        print "Error in getting the average wind speed of the month : %s" % exception
        monthly_wind_speed = None
    print "monthly_module_temperature %s, monthly_ambient_temperature %s, monthly_wind_speed %s" % (
        monthly_module_temperature, monthly_ambient_temperature, monthly_wind_speed)
    print "end compute_plant_aggregated_values"
    return monthly_module_temperature, monthly_ambient_temperature, monthly_wind_speed


def compute_meters_summary_recalculate(starttime, endtime, plant):
    """

    :param starttime:
    :param endtime:
    :param plant:
    :return:
    """
    print "start compute_meters_summary_recalculate"
    meters = plant.energy_meters.all()
    meter_initial_time = starttime.replace(hour=0, minute=0, second=0, microsecond=0)
    for meter in meters:
        total_per_meter_energy = 0.0
        try:
            monthly_meter_energy_entry = PlantDeviceSummaryDetails.objects.filter(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                identifier=str(meter.sourceKey),
                ts__gte=starttime, ts__lte=endtime)
            for meter_value in monthly_meter_energy_entry:
                try:
                    total_per_meter_energy += meter_value.generation
                except Exception as exc:
                    total_per_meter_energy += 0.0
        except Exception as exception:
            print "exception with meters energy loop %s" % exception

        print "meter %s - total_per_meter_energy %s" % (meter, total_per_meter_energy)

        try:
            monthly_energy_entry = PlantDeviceSummaryDetails.objects.get(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                identifier=str(meter.sourceKey),
                ts=meter_initial_time)
            monthly_energy_entry.update(generation=total_per_meter_energy)
        except Exception as exception:
            print "exception with meters %s" % exception
            monthly_entry = PlantDeviceSummaryDetails.objects.create(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                identifier=str(meter.sourceKey),
                ts=meter_initial_time)
            monthly_entry.save()

    print "end compute_meters_summary_recalculate"


def compute_inverters_summary_recalculate(starttime, endtime, plant):
    """

    :param starttime:
    :param endtime:
    :param plant:
    :return:
    """
    print "start compute_inverters_summary_recalculate"
    inverters = plant.independent_inverter_units.all()
    inverter_initial_time = starttime.replace(hour=0, minute=0, second=0, microsecond=0)

    for inverter in inverters:
        total_per_inverter_energy = 0.0
        total_per_inverter_working_hour = 0.0
        total_per_inverter_max_ac_power = 0.0
        total_per_inverter_max_dc_power = 0.0
        try:
            monthly_inverter_energy_entry = PlantDeviceSummaryDetails.objects.filter(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                identifier=str(inverter.sourceKey),
                ts__gte=starttime, ts__lte=endtime)
            for inverter_value in monthly_inverter_energy_entry:
                try:
                    total_per_inverter_energy += inverter_value.generation if \
                        inverter_value.generation > 0 else 0.0
                    total_per_inverter_working_hour += inverter_value.total_working_hours if \
                        inverter_value.total_working_hours > 0 else 0.0
                    total_per_inverter_max_ac_power += inverter_value.max_ac_power if \
                        inverter_value.max_ac_power > 0 else 0.0
                    total_per_inverter_max_dc_power += inverter_value.max_dc_power if \
                        inverter_value.max_dc_power > 0 else 0.0
                except Exception as exception:
                    print "exception with monthly_inverter_energy_entry %s" % exception
        except Exception as exception:
            print "exception with inverters energy loop %s" % exception

        print "inverter %s - energy %s - working_hour %s - max_ac_power %s - max_dc_power %s" % (
        inverter, total_per_inverter_energy, total_per_inverter_working_hour, total_per_inverter_max_ac_power,
        total_per_inverter_max_dc_power,)

        try:
            energy_entry = PlantDeviceSummaryDetails.objects.get(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                identifier=str(inverter.sourceKey),
                ts=inverter_initial_time)
            try:
                energy_entry.update(generation=total_per_inverter_energy,
                                    total_working_hours=total_per_inverter_working_hour,
                                    max_dc_power=total_per_inverter_max_dc_power,
                                    max_ac_power=total_per_inverter_max_ac_power)
            except:
                energy_entry.update(generation=total_per_inverter_energy)
        except Exception as exception:
            try:
                print "exception %s" % exception
                energy_entry = PlantDeviceSummaryDetails.objects.create(
                    timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                    count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                    identifier=str(inverter.sourceKey),
                    ts=inverter_initial_time,
                    generation=total_per_inverter_energy,
                    total_working_hours=total_per_inverter_working_hour,
                    max_dc_power=total_per_inverter_max_dc_power,
                    max_ac_power=total_per_inverter_max_ac_power)
                energy_entry.save()
            except Exception as exception:
                print "exception %s" % exception
                energy_entry = PlantDeviceSummaryDetails.objects.create(
                    timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                    count_time_period=settings.DATA_COUNT_PERIODS.MONTH,
                    identifier=str(inverter.sourceKey),
                    ts=inverter_initial_time,
                    generation=total_per_inverter_energy,
                    max_dc_power=total_per_inverter_max_dc_power,
                    max_ac_power=total_per_inverter_max_ac_power)
                energy_entry.save()

    print "end compute_inverters_summary_recalculate"


def compute_plant_summary_details(startdatetime, enddatetime, plant):
    """

    :param startdatetime:
    :param enddatetime:
    :param plant:
    :return:
    """
    print "start compute_plant_summary_details"
    try:
        startdatetime = datetime.datetime.strptime(startdatetime, "%Y-%m-%d %H:%M:%S")
        enddatetime = datetime.datetime.strptime(enddatetime, "%Y-%m-%d %H:%M:%S")
        startdatetime = pytz.utc.localize(startdatetime)
        enddatetime = pytz.utc.localize(enddatetime)
        startdatetime = startdatetime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
        enddatetime = enddatetime.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
    except Exception as exc:
        print "specify datetime in '%Y-%m-%d %H:%M:%S' format %s" % exc
        return

    while enddatetime > startdatetime:
        initial_time = startdatetime.replace(hour=0, minute=0, second=0)
        _, last_day_of_month = calendar.monthrange(startdatetime.year, startdatetime.month)
        final_time = startdatetime.replace(day=last_day_of_month, hour=23, minute=59, second=59)

        print "startdatetime %s initial_time %s final_time %s" % (startdatetime, initial_time, final_time)

        monthly_energy_value = compute_plant_montly_energy(initial_time, final_time, plant)
        monthly_pr = compute_plant_montly_pr(initial_time, final_time, plant)
        monthly_cuf = compute_plant_monthly_cuf(initial_time, final_time, plant)
        monthly_specific_yield = compute_plant_monthly_specific_yield(initial_time, final_time, plant)
        monthly_dc_loss, monthly_conversion_loss, monthly_ac_loss = compute_plant_enegry_losses(initial_time,
                                                                                                final_time,
                                                                                                plant)
        final_equipment_down_time, average_monthly_down_time = compute_plant_availability(initial_time, final_time,
                                                                                          plant)
        monthly_insolation = compute_plant_average_insolation(initial_time, final_time, plant)
        monthly_module_temperature, monthly_ambient_temperature, monthly_wind_speed = compute_plant_aggregated_values(
            initial_time, final_time, plant)

        # Commented below part for dry run

        try:
            monthly_summary_entry = PlantSummaryDetails.objects.get(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                count_time_period=settings.DATA_COUNT_PERIODS.MONTH, identifier=plant.slug, ts=initial_time)
            print "start plant summary details update existing"
            monthly_summary_entry.update(generation=monthly_energy_value, performance_ratio=monthly_pr, cuf=monthly_cuf,
                                         specific_yield=monthly_specific_yield, dc_loss=monthly_dc_loss,
                                         conversion_loss=monthly_conversion_loss, ac_loss=monthly_ac_loss,
                                         grid_availability=average_monthly_down_time,
                                         equipment_availability=final_equipment_down_time,
                                         average_irradiation=monthly_insolation,
                                         average_module_temperature=monthly_module_temperature,
                                         average_ambient_temperature=monthly_ambient_temperature,
                                         average_wind_speed=monthly_wind_speed,
                                         updated_at=timezone.now().replace(tzinfo=None))
            print "end plant summary details update existing"
        except Exception as exc:
            print "excepiton %s" % exc
            print "start plant summary details create new"
            PlantSummaryDetails.objects.create(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                count_time_period=settings.DATA_COUNT_PERIODS.MONTH, identifier=plant.slug, ts=initial_time,
                generation=monthly_energy_value, performance_ratio=monthly_pr, cuf=monthly_cuf,
                specific_yield=monthly_specific_yield, dc_loss=monthly_dc_loss, conversion_loss=monthly_conversion_loss,
                ac_loss=monthly_ac_loss, grid_availability=average_monthly_down_time,
                equipment_availability=final_equipment_down_time, average_irradiation=monthly_insolation,
                average_module_temperature=monthly_module_temperature,
                average_ambient_temperature=monthly_ambient_temperature, average_wind_speed=monthly_wind_speed,
                updated_at=timezone.now().replace(tzinfo=None))
            print "start plant summary details create new"

        compute_inverters_summary_recalculate(initial_time, final_time, plant)
        compute_meters_summary_recalculate(initial_time, final_time, plant)

        print "startdatetime %s enddatetime %s" % (startdatetime, enddatetime)
        startdatetime = final_time + datetime.timedelta(days=1)
    print "end compute_plant_summary_details"
