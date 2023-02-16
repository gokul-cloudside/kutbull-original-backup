import pytz
import datetime
from solarrms.models import SolarGroup, PlantCompleteValues, SpecificYieldTable
from django.utils import timezone
from django.conf import settings
from solarrms.solargrouputils import get_solar_groups_module_temperature, get_solar_groups_ambient_temperature,\
    get_solar_groups_windspeed, get_solar_groups_irradiation, get_solar_groups_total_generation,\
    get_solar_groups_today_generation, get_solar_groups_power, get_solar_groups_pr_cuf_sy


def get_all_solar_groups_details():
    """

    :return:
    """
    print "current_time;group_name;group_id;pr;cuf;sy;total_generation;group_generation_today;co2_savings;current_power;irradiation;windspeed;module_temperature;ambient_temperature"
    current_time = timezone.now()
    all_solar_groups = SolarGroup.objects.\
        prefetch_related('groupAJBs', 'groupIndependentInverters', 'groupEnergyMeters', 'groupPlantMetaSources',\
                         'groupGatewaySources').select_related('plant')
    for solar_group in all_solar_groups:

        time_zone = solar_group.plant.metadata.plantmetasource.dataTimezone
        current_time = current_time.astimezone(pytz.timezone(time_zone))
        plant_start_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)

        plant = solar_group.plant
        # calculate pr, cuf, sy
        pr, cuf, sy = get_solar_groups_pr_cuf_sy(plant_start_time, current_time, solar_group, plant)

        # ! grid availability

        # ! equipment availability

        # ! Tickets

        # Total generation
        total_generation = get_solar_groups_total_generation(current_time, solar_group)

        # Today's generation
        group_generation_today = get_solar_groups_today_generation(current_time, solar_group)

        # CO2 savings
        co2_savings = group_generation_today * 0.7

        # ! current active power
        delay_mins = 2
        current_power = 0.0
        values = get_solar_groups_power(current_time - datetime.timedelta(minutes=30),
                                        current_time - datetime.timedelta(minutes=delay_mins),
                                 solar_group, solar_group.plant)
        if len(values) > 0:
            current_power = float(values[-1]["power"])
        else:
            current_power = 0.0


        # irradiation values
        irradiation = get_solar_groups_irradiation(current_time, solar_group)


        # wind speed
        windspeed = get_solar_groups_windspeed(current_time, solar_group)


        # get module temperature data
        module_temperature = get_solar_groups_module_temperature(current_time, solar_group)

        # Ambient temperature
        ambient_temperature = get_solar_groups_ambient_temperature(current_time, solar_group)

        # ! connection status of inverters

        # ! connection status of SMB's

        # ! last 7 days energy values

        # ! last 7 days PR value

        # ! past 7 days cuf

        # ! past 7 days grid availability

        # ! past 7 days equipment availability

        # ! Past 7 days energy losses

        # ! updating client parameters

        total_capacity = 0.0
        for inverter in solar_group.groupIndependentInverters.all():
            total_capacity += inverter.total_capacity if inverter.total_capacity else inverter.actual_capacity

        print "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s" % (
        current_time, solar_group.name, solar_group.varchar_id, pr, cuf, sy, total_generation, group_generation_today,
        co2_savings, current_power, irradiation, windspeed, module_temperature, ambient_temperature)

        daily_group_values = PlantCompleteValues(
            timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
            count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
            identifier=solar_group.varchar_id,
            ts=current_time.replace(hour=0, minute=0, second=0, microsecond=0),
            name=solar_group.name,
            capacity=total_capacity,
            location=solar_group.plant.location,
            latitude=solar_group.plant.latitude,
            longitude=solar_group.plant.longitude,
            pr=pr,
            cuf=cuf,
            total_generation=total_generation,
            plant_generation_today=group_generation_today,
            co2_savings=co2_savings,
            active_power=current_power,
            irradiation=irradiation,
            windspeed=windspeed,
            ambient_temperature=ambient_temperature,
            module_temperature=module_temperature,
            updated_at=current_time)
        daily_group_values.save()

        specific_yield_entry = SpecificYieldTable(
            timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
            count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
            identifier=solar_group.varchar_id,
            ts=current_time.replace(hour=0, minute=0, second=0, microsecond=0),
            specific_yield=sy,
            updated_at=timezone.now())
        specific_yield_entry.save()



