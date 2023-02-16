from __future__ import absolute_import
from celery import shared_task
import logging
import traceback
import sys
from django.conf import settings
from django.db import connections
import datetime
from dataglen.models import Sensor
from isoweek import Week
from solarrms.models import IndependentInverter, SolarPlant, PlantMetaSource
from dataglen.models import ValidDataStorageByStream
from solarrms.settings import INVERTER_VALID_LAST_ENTRY_MINUTES, INVERTER_POWER_FIELD, \
    PLANT_POWER_STREAM, PLANT_ENERGY_STREAM, INVERTER_ENERGY_FIELD
# DO NOT CHANGE THIS IMPORT!
from kutbill.worker import *
from monitoring.views import write_a_data_write_ttl
from datetime import timedelta
import pytz


# get a logger
logger = logging.getLogger('logger.tasks')
logger.setLevel(logging.DEBUG)

def write_logging_errors(func_name):
    logger.debug("%s,%s,%s",
                 func_name, traceback.format_exc(),
                 repr(traceback.extract_stack()))


def compare_dates(offset_naive_dt, offset_aware_dt):
    return offset_naive_dt.replace(tzinfo=pytz.UTC, microsecond=0) == offset_aware_dt.astimezone(pytz.UTC).replace(microsecond=0)

def write_plant_energy(user_id, plant_metakey, ts, n_writes):
    #logger.debug(",".join([str(user_id), str(plant_metakey), str(ts), str(n_writes)]))
    unit_conversion = 1.0
    try:
        plant_meta = PlantMetaSource.objects.get(sourceKey=plant_metakey)
        #logger.debug(plant_meta)
        plant_slug = plant_meta.plant.slug
        #logger.debug(plant_slug)
        # DO THE POWER CALCULATIONS
        if plant_meta.sending_aggregated_power:
            unit = plant_meta.fields.filter(name=PLANT_POWER_STREAM)[0].streamDataUnit
            #logger.debug(unit)
            if unit:
                if unit.upper() == "W":
                    unit_conversion = 1000.0
                elif unit.upper() == "KW":
                    unit_conversion = 1.0
            else:
                unit_conversion = 1.0
            #logger.debug("power unit:" + str(unit_conversion))
            try:
                power_value = ValidDataStorageByStream.objects.filter(source_key=plant_meta.sourceKey,
                                                                      stream_name=PLANT_POWER_STREAM,
                                                                      timestamp_in_data=ts)
                # assert that the last data write is same as this ts
                power_value = float(power_value[0].stream_value)/float(unit_conversion)
            except:
                return 0
            #logger.debug(power_value)
            # WRITE THE VALUES
            update_power(plant_slug, ts, power_value)
            #logger.debug("power_updated")

        if plant_meta.sending_aggregated_energy:
            # DO THE ENERGY CALCULATIONS
            unit = plant_meta.fields.filter(name=PLANT_ENERGY_STREAM)[0].streamDataUnit
            if unit:
                if unit.upper() == "WH":
                    unit_conversion = 1000.0
                elif unit.upper() == "KWH":
                    unit_conversion = 1.0
            else:
                unit_conversion = 1.0

            #logger.debug("energy unit: " + str(unit_conversion))
            try:
                energy_values = ValidDataStorageByStream.objects.filter(source_key=plant_meta.sourceKey,
                                                                        stream_name=PLANT_ENERGY_STREAM,
                                                                        timestamp_in_data__lte=ts).limit(2)
                # assert that the first timestamp is same as this data write
                assert(compare_dates(energy_values[0].timestamp_in_data,ts))
                # if the values are next to each other
                if energy_values[0].timestamp_in_data - energy_values[1].timestamp_in_data < datetime.timedelta(minutes=INVERTER_VALID_LAST_ENTRY_MINUTES):
                    # since it's cumulative, it should be positive
                    if (float(energy_values[0].stream_value) - float(energy_values[1].stream_value)) > 0:
                        energy_value = float(float(energy_values[0].stream_value) - float(energy_values[1].stream_value))/float(unit_conversion)
                        energy_today = float(energy_values[0].stream_value)
                    else:
                        return 0
                else:
                    return 0
            except:
                return 0
            #logger.debug(energy_value)
            update_energy(str(user_id) + "_" + str(plant_slug), ts, energy_value, energy_today)
            #logger.debug("energy_updated")
    except Sensor.DoesNotExist:
        return 0

def write_inverter_energy(user_id, source_key, ts, n_writes):
    logger.debug(",".join([str(user_id), str(source_key), str(ts), str(n_writes), "write_inverter_energy"]))
    unit_conversion = 1.0
    try:
        inverter = IndependentInverter.objects.get(sourceKey=source_key)
        try:
            if hasattr(inverter.plant, 'gateway'):
                if inverter.plant.gateway.isVirtual:
                    write_a_data_write_ttl(inverter.plant.owner.organization_user.user_id,
                                           inverter.plant.gateway.sourceKey,
                                           inverter.plant.gateway.timeoutInterval,
                                           True,
                                           timezone.now())
        except Exception as exc:
            logger.debug(exc)
            pass
        plant_slug = inverter.plant.slug
        unit = inverter.fields.filter(name=INVERTER_POWER_FIELD)[0].streamDataUnit
        if unit:
            if unit.upper() == "W":
                unit_conversion = 1000.0
            elif unit.upper() == "KW":
                unit_conversion = 1.0
        else:
            unit_conversion = 1.0
    except IndependentInverter.DoesNotExist:
        return 0

    try:
        #raise ValidDataStorageByStream.DoesNotExist
        daily_yield = ValidDataStorageByStream.objects.filter(source_key=source_key,
                                                              stream_name=INVERTER_ENERGY_FIELD,
                                                              timestamp_in_data__lte=ts).limit(2)
        if len(daily_yield) == 0:
            # it's a dumb inverter
            logger.debug("daily_yield == 0 no such data")
            raise ValidDataStorageByStream.DoesNotExist

        if len(daily_yield) >= 1:
            # update the power in all cases if there's no cluster controller
            if hasattr(inverter.plant, 'metadata'):
                if inverter.plant.metadata.sending_aggregated_power is False:
                    logger.debug("writing power for this inverter")
                    # update power values for this inverter, nothing can be done for energy yet
                    write_entries = ValidDataStorageByStream.objects.filter(source_key=source_key,
                                                                            stream_name=INVERTER_POWER_FIELD,
                                                                            timestamp_in_data=ts).values_list('timestamp_in_data', 'stream_value')
                    if len(write_entries) == 0:
                        logger.debug("write_entries==0")
                    elif n_writes == 1:
                        update_power(plant_slug, ts, float(write_entries[0][1])/float(unit_conversion))
                    elif n_writes > 1:
                        logger.debug("this should not be happening since we are not sending aggregated data yet")

        # assert that the first timestamp in the data is same as of this data write
        assert(compare_dates(daily_yield[0].timestamp_in_data, ts))
        if len(daily_yield) == 2:
            # update energy if the data records are greater than 1 (i.e. the energy can be calculated)
            # and there is no cluster controller
            # it's an intelligent inverter
            if daily_yield[0].timestamp_in_data - daily_yield[1].timestamp_in_data > \
                    datetime.timedelta(minutes=INVERTER_VALID_LAST_ENTRY_MINUTES):
                return 0

            #logger.debug("intelligent inverter")
            if float(daily_yield[1].stream_value) > 100000 or float(daily_yield[0].stream_value) > 100000:
                # TODO relate it to the plant capacity
                #logger.debug("abnormal value")
                return 0
            #logger.debug(float(daily_yield[0].stream_value))
            #logger.debug(float(daily_yield[1].stream_value))

            energy = float(float(daily_yield[0].stream_value) - float(daily_yield[1].stream_value))
            if energy < 0 :
                #logger.debug("day change?")
                return 0
            # update it for both plant and inverter
            energy_unit = inverter.fields.filter(name=INVERTER_ENERGY_FIELD)[0].streamDataUnit
            energy_unit_conversion = 1.0
            if energy_unit:
                if energy_unit.upper() == "WH":
                    energy_unit_conversion = 1000.0
                elif energy_unit.upper() == "KWH":
                    energy_unit_conversion = 1.0
            # update for the inverter in any case
            update_energy(inverter.sourceKey, ts, energy/energy_unit_conversion, float(daily_yield[1].stream_value))
            if hasattr(inverter.plant, 'metadata'):
                if inverter.plant.metadata.sending_aggregated_energy is False:
                    # update for teh plant also
                    update_energy(str(user_id) + "_" + str(inverter.plant.slug), ts, energy/energy_unit_conversion)
    except Exception as exc:
        #logger.debug(str(exc))
        # there's no daily_yield data, dumb inverter
        #
        # DUMB INVERTER - not sending cumulative energy values
        #logger.debug("it's a dumb inverter")
        try:
            # get all the active power values >= ts and limit by n_writes [essentially the data point at ts]
            write_entries = ValidDataStorageByStream.objects.filter(source_key=source_key,
                                                                    stream_name=INVERTER_POWER_FIELD,
                                                                    timestamp_in_data=ts).values_list('timestamp_in_data', 'stream_value')

            if len(write_entries) == 0:
                #logger.debug(",".join(["returning", str(len(write_entries))]))
                # nothing to be done, this should not be happening though
                return 0

            #logger.debug(",".join(["write_entries", str(len(write_entries))]))
            # get a value just before the first value in the array, to calculate energy
            last_entry = ValidDataStorageByStream.objects.filter(source_key=source_key,
                                                                 stream_name=INVERTER_POWER_FIELD,
                                                                 timestamp_in_data__lt=ts).limit(1).values_list('timestamp_in_data', 'stream_value')
            final_entries = []
            if len(last_entry) == 0:
                #logger.debug("last_entry==0")
                if n_writes > 1:
                    pass
                elif n_writes == 1:
                    # there's no last valid entry
                    # if we've received only a single write, return now
                    if hasattr(inverter.plant, 'metadata'):
                        if inverter.plant.metadata.sending_aggregated_power is False:
                            update_power(plant_slug, ts, float(write_entries[0][1])/float(unit_conversion))
                            return 0
                    else:
                        update_power(plant_slug, ts, float(write_entries[0][1])/float(unit_conversion))
                        return 0
            else:
                final_entries.append(last_entry[0])

            #logger.debug(len(write_entries))
            for entry in write_entries:
                final_entries.append(entry)

            #logger.debug(len(final_entries))
            for i in range(0, len(final_entries) - 1):
                if final_entries[i+1][0] - final_entries[i][0] > datetime.timedelta(minutes=INVERTER_VALID_LAST_ENTRY_MINUTES):
                    continue
                else:
                    if float(final_entries[i+1][1]) < 0 or float(final_entries[i][1]) < 0:
                        continue
                    energy_mean = (float(final_entries[i+1][1]) + float(final_entries[i][1]))/(float(2)*unit_conversion)
                    delta = final_entries[i+1][0] - final_entries[i][0]
                    total_seconds = delta.total_seconds()
                    energy = (energy_mean * total_seconds)/float(3600)
                    if hasattr(inverter.plant, 'metadata'):
                        if inverter.plant.metadata.sending_aggregated_energy is False:
                            update_energy(inverter.sourceKey, ts, energy)
                            update_energy(str(user_id) + "_" + str(inverter.plant.slug), ts, energy)
                        else:
                            update_energy(inverter.sourceKey, ts, energy)
                    else:
                        update_energy(inverter.sourceKey, ts, energy)
                        update_energy(str(user_id) + "_" + str(inverter.plant.slug), ts, energy)

            # skip the first entry as that's an old value - we needed that for the computation of energy
            # but that should not be added again as power
            #logger.debug("updating power values")
            for i in range(1, len(final_entries)):
                if hasattr(inverter.plant, 'metadata'):
                    if inverter.plant.metadata.sending_aggregated_power is False:
                        update_power(plant_slug, ts, float(write_entries[0][1])/float(unit_conversion))
                else:
                    update_power(plant_slug, ts, float(write_entries[0][1])/float(unit_conversion))
        except Exception as exc:
            return 0

@shared_task
def update_power(plant_slug, ts, power):
    #logger.debug(",".join([plant_slug, str(ts), str(power), "update_power"]))
    if power < 0:
        return
    try:
        timestamp = ts.replace(second=0, microsecond=0)
        session = connections['cassandra'].connection.session

        if session:
            get_power_statement = session.prepare("SELECT power from dataglen_data.plant_power_table WHERE plant_slug = ? AND ts = ?")
            update_power_statement = session.prepare("UPDATE dataglen_data.plant_power_table SET power = ? WHERE plant_slug = ? AND ts = ?")

            existing_power = session.execute(get_power_statement, [plant_slug,
                                                                   timestamp])

            if existing_power:
                existing_power_value = float(existing_power[0]['power'])
                updated_power = float(existing_power_value) + float(power)
                session.execute(update_power_statement, [updated_power,
                                                         plant_slug,
                                                         timestamp])
            else:
                session.execute(update_power_statement, [power,
                                                         plant_slug,
                                                         timestamp])
            return 0
        else:
            #logger.debug("Unable to get a new cassandra session in update power")
            return 1
    except Exception as exc:
        #logger.debug(exc)
        write_logging_errors(sys._getframe().f_code.co_name)
        return 1

@shared_task
def update_energy(identifier, ts, energy, energy_today=None):
    try:
        #logger.debug("starting timestamps-1")
        if energy_today:
            logger.debug(",".join([identifier, str(ts), str(energy), str(energy_today), "update_energy"]))
        else:
            logger.debug(",".join([identifier, str(ts), str(energy), "update_energy"]))
        #logger.debug("starting timestamps0")
        identifiers = [identifier]
        #logger.debug("starting timestamps1")
        # let's use the monday of the week as the timestamp for weeks
        week_details = ts.isocalendar()
        #logger.debug("starting timestamps2")
        week = Week(week_details[0], week_details[1])
        #logger.debug("starting timestamps3")
        week_monday_date = week.monday()
        #logger.debug("starting timestamps4")
        timestamps = [(settings.DATA_COUNT_PERIODS.FIVE_MINTUES, ts.replace(minute=ts.minute - ts.minute%5, second=0, microsecond=0)),
                      (settings.DATA_COUNT_PERIODS.HOUR, ts.replace(minute=0, second=0, microsecond=0)),
                      (settings.DATA_COUNT_PERIODS.DAILY, ts.replace(hour=0, minute=0, second=0, microsecond=0)),
                      (settings.DATA_COUNT_PERIODS.WEEK, ts.replace(month=week_monday_date.month,
                                                                    day=week_monday_date.day, hour=0, minute=0,
                                                                    second=0, microsecond=0)),
                      (settings.DATA_COUNT_PERIODS.MONTH, ts.replace(day=1, hour=0,
                                                                     minute=0, second=0, microsecond=0))]
        session = connections['cassandra'].connection.session

        if session:
            get_energy_statement = session.prepare("SELECT energy from dataglen_data.energy_generation_table WHERE timestamp_type = ? AND count_time_period = ? AND identifier = ? AND ts = ?")
            update_energy_statement = session.prepare("UPDATE dataglen_data.energy_generation_table SET energy = ? WHERE timestamp_type = ? AND count_time_period = ? AND identifier = ? AND ts = ?")
            #logger.debug("Statements prepared5")
            for identifier in identifiers:
                for entry in timestamps:
                    #logger.debug(identifier)
                    #logger.debug(entry[0])
                    #logger.debug(entry[1])
                    existing_energy = session.execute(get_energy_statement, [settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                             entry[0],
                                                                             identifier,
                                                                             entry[1]])

                    if existing_energy:
                        existing_energy_value = float(existing_energy[0]['energy'])
                        updated_energy = existing_energy_value + energy

                        # if it's a daily energy log, check if we missed any points
                        if energy_today and entry[0] == settings.DATA_COUNT_PERIODS.DAILY:
                            if updated_energy != energy_today:
                                updated_energy = energy_today


                        # TODO fix the week values, we will probably need am offline job for that

                        session.execute(update_energy_statement, [updated_energy,
                                                                  settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                  entry[0],
                                                                  identifier,
                                                                  entry[1]])
                    else:
                        session.execute(update_energy_statement, [energy,
                                                                  settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                  entry[0],
                                                                  identifier,
                                                                  entry[1]])
            return 0
        else:
            logger.debug("Unable to get a new cassandra session")
            return 1
    except:
        write_logging_errors(sys._getframe().f_code.co_name)
        return 1