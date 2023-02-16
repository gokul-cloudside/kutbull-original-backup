import datetime
from solarrms.models import PlantMetaSource, EnergyLossTableNew, SolarPlant
from django.utils import timezone
from django.conf import settings
import pytz
from solarrms.solarutils import get_all_energy_losses_aggregated
from solarrms.energy_loss_new import compute_dc_loss, compute_conversion_loss, compute_ac_loss


start_date = "2017-11-01 00:00:00"

def compute_energy_losses():
    try:
        print("Energy loss cronjob started")
        #plants = SolarPlant.objects.filter(slug='yerangiligi')
        plants = SolarPlant.objects.all()
        for plant in plants:
            print "Energy Loss calculation for : " + str(plant.slug)
            try:
                tz = pytz.timezone(plant.metadata.plantmetasource.dataTimezone)
            except:
                print ("Error in getting tz")
            try:
                current_time = timezone.now()
                current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
            except Exception as exc:
                print(str(exc))
                current_time = timezone.now()

            energy_losses_last_entry = EnergyLossTableNew.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                      count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                      identifier=plant.metadata.plantmetasource.sourceKey).limit(1).values_list('ts')

            #energy_losses_last_entry=None
            if energy_losses_last_entry:
                last_entry_values = [item[0] for item in energy_losses_last_entry]
                last_entry  = last_entry_values[0]
                print("last_time_entry: ", last_entry)
                if last_entry.tzinfo is None:
                    last_entry =pytz.utc.localize(last_entry)
                    last_entry = last_entry.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
            else:
                last_entry = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                if last_entry.tzinfo is None:
                    last_entry = tz.localize(last_entry)
                    last_entry = last_entry.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))

            duration = (current_time - last_entry)
            duration_days = duration.days
            loop_count = 0
            while loop_count < duration_days:
                print(duration_days)
                print last_entry
                plant_shut_down_time = last_entry.replace(hour=19, minute=0, second=0, microsecond=0)
                plant_start_time = last_entry.replace(hour=6, minute=0, second=0, microsecond=0)
                last_entry = plant_start_time

                daily_energy_loss = EnergyLossTableNew.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                                   ts=last_entry.replace(hour=0, minute=0, second=0, microsecond=0))

                try:
                    dc_loss_values = compute_dc_loss(plant_start_time,plant_shut_down_time,plant)
                    conversion_loss_values = compute_conversion_loss(plant_start_time, plant_shut_down_time, plant)
                    ac_loss_values = compute_ac_loss(plant_start_time, plant_shut_down_time, plant)
                    try:
                        dc_energy_ajb = dc_loss_values['dc_energy_from_ajb']
                    except Exception as exception:
                        print str(exception)
                        dc_energy_ajb = None
                    try:
                        dc_energy_inverters_ajb = dc_loss_values['dc_energy_from_inverter']
                    except Exception as exception:
                        print str(exception)
                        dc_energy_inverters_ajb = None
                    try:
                        dc_energy_loss = dc_energy_ajb - dc_energy_inverters_ajb
                    except Exception as exception:
                        print str(exception)
                        dc_energy_loss = None
                    try:
                        dc_energy_inverters = conversion_loss_values['dc_energy_inverter']
                        print dc_energy_inverters
                    except Exception as exception:
                        print str(exception)
                        dc_energy_inverters = None
                    try:
                        ac_energy_inverters_ap = conversion_loss_values['ac_energy_inverter']
                    except Exception as exception:
                        print str(exception)
                        ac_energy_inverters_ap = None
                    try:
                        conversion_loss = dc_energy_inverters - ac_energy_inverters_ap
                    except Exception as exception:
                        print str(exception)
                        conversion_loss = None
                    try:
                        ac_energy_inverters = ac_loss_values['inverter_ac_energy']
                    except Exception as exception:
                        print str(exception)
                        ac_energy_inverters = None
                    try:
                        ac_energy_meters = ac_loss_values['meter_ac_energy']
                    except Exception as exception:
                        print str(exception)
                        ac_energy_meters = None
                    try:
                        ac_energy_loss = ac_energy_inverters - ac_energy_meters
                    except Exception as exception:
                        print str(exception)
                        ac_energy_loss = None
                except Exception as exception:
                    print(str(exception))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    duration_days -= 1
                    continue

                try:
                    if len(daily_energy_loss) == 0:
                        daily_entry = EnergyLossTableNew.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                        count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                        identifier=plant.metadata.plantmetasource.sourceKey,
                                                                        ts=last_entry.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                        dc_energy_ajb=dc_energy_ajb,
                                                                        dc_energy_inverters_ajb=dc_energy_inverters_ajb,
                                                                        dc_energy_inverters=dc_energy_inverters,
                                                                        ac_energy_inverters_ap=ac_energy_inverters_ap,
                                                                        ac_energy_inverters=ac_energy_inverters,
                                                                        ac_energy_meters=ac_energy_meters,
                                                                        dc_energy_loss=dc_energy_loss,
                                                                        conversion_loss=conversion_loss,
                                                                        ac_energy_loss=ac_energy_loss,
                                                                        updated_at=current_time
                                                                        )
                        daily_entry.save()
                    else:
                        daily_energy_loss.update(dc_energy_ajb=dc_energy_ajb,
                                                 dc_energy_inverters_ajb=dc_energy_inverters_ajb,
                                                 dc_energy_inverters=dc_energy_inverters,
                                                 ac_energy_inverters_ap=ac_energy_inverters_ap,
                                                 ac_energy_inverters=ac_energy_inverters,
                                                 ac_energy_meters=ac_energy_meters,
                                                 dc_energy_loss=dc_energy_loss,
                                                 conversion_loss=conversion_loss,
                                                 ac_energy_loss=ac_energy_loss,
                                                 updated_at=current_time)

                    inverters = plant.independent_inverter_units.all()
                    for inverter in inverters:
                        inverter_daily_energy_loss = EnergyLossTableNew.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                    identifier=inverter.sourceKey,
                                                                                    ts=last_entry.replace(hour=0, minute=0, second=0, microsecond=0))
                        try:
                            inverter_dc_energy_ajb = dc_loss_values['dc_energy_ajb_' + str(inverter.name)]
                        except Exception as exception:
                            print str(exception)
                            inverter_dc_energy_ajb = None
                        try:
                            inverter_dc_energy_inverters = dc_loss_values['dc_energy_' + str(inverter.name)]
                        except Exception as exception:
                            print str(exception)
                            inverter_dc_energy_inverters = None
                        try:
                           inverter_dc_energy_loss =  inverter_dc_energy_ajb - inverter_dc_energy_inverters
                        except Exception as exception:
                            print str(exception)
                            inverter_dc_energy_loss = None
                        try:
                            inverter_ac_energy_inverters_ap = conversion_loss_values['dc_energy_' + str(inverter.name)]
                        except Exception as exception:
                            print str(exception)
                            inverter_ac_energy_inverters_ap = None
                        try:
                            inverter_ac_energy_inverter = conversion_loss_values['ac_energy_'+str(inverter.name)]
                        except Exception as exception:
                            print str(exception)
                            inverter_ac_energy_inverter = None
                        try:
                            print inverter_ac_energy_inverters_ap, inverter_ac_energy_inverter
                            inverter_conversion_loss = inverter_ac_energy_inverters_ap - inverter_ac_energy_inverter
                        except Exception as exception:
                            print str(str(exception))
                            inverter_conversion_loss = None
                        if len(inverter_daily_energy_loss) == 0:
                            inverter_daily_entry = EnergyLossTableNew.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                     count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                     identifier=inverter.sourceKey,
                                                                                     ts=last_entry.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                                     dc_energy_ajb=inverter_dc_energy_ajb,
                                                                                     dc_energy_inverters=inverter_dc_energy_inverters,
                                                                                     ac_energy_inverters_ap=inverter_ac_energy_inverters_ap,
                                                                                     ac_energy_inverters=inverter_ac_energy_inverter,
                                                                                     dc_energy_loss=inverter_dc_energy_loss,
                                                                                     conversion_loss=inverter_conversion_loss,
                                                                                     updated_at=current_time
                                                                                    )
                            inverter_daily_entry.save()
                        else:
                            inverter_daily_energy_loss.update(dc_energy_ajb=inverter_dc_energy_ajb,
                                                             dc_energy_inverters=inverter_dc_energy_inverters,
                                                             ac_energy_inverters_ap=inverter_ac_energy_inverters_ap,
                                                             ac_energy_inverters=inverter_ac_energy_inverter,
                                                             dc_energy_loss=inverter_dc_energy_loss,
                                                             conversion_loss=inverter_conversion_loss,
                                                             updated_at=current_time
                                                             )
                    last_entry = last_entry + datetime.timedelta(days=1)
                    duration_days -= 1
                except Exception as ex:
                    print("Exception in energy loss calculation: %s", str(ex))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    duration_days -= 1
                    continue

            if duration_days == 0:
                print("Current Energy Loss computation for plant : {0}".format(str(plant)))
                initial_time = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
                final_time = current_time
                plant_shut_down_time = final_time.replace(hour=19, minute=0, second=0, microsecond=0)
                plant_start_time = final_time.replace(hour=6, minute=0, second=0, microsecond=0)

                daily_energy_loss = EnergyLossTableNew.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=plant.metadata.plantmetasource.sourceKey,
                                                                   ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0))

                try:
                    dc_loss_values = compute_dc_loss(plant_start_time,plant_shut_down_time,plant)
                    print "dc_loss_values"
                    print dc_loss_values
                    conversion_loss_values = compute_conversion_loss(plant_start_time, plant_shut_down_time, plant)
                    print "conversion_loss_values"
                    print conversion_loss_values
                    ac_loss_values = compute_ac_loss(plant_start_time, plant_shut_down_time, plant)
                    print ac_loss_values
                    print "ac_loss_values"
                    try:
                        dc_energy_ajb = dc_loss_values['dc_energy_from_ajb']
                    except Exception as exception:
                        print ("Exception1 : " + str(exception))
                        dc_energy_ajb = None
                    try:
                        dc_energy_inverters_ajb = dc_loss_values['dc_energy_from_inverter']
                    except Exception as exception:
                        print ("Exception2 : " + str(exception))
                        dc_energy_inverters_ajb = None
                    try:
                        dc_energy_loss = dc_energy_ajb - dc_energy_inverters_ajb
                    except Exception as exception:
                        print ("Exception3 : " + str(exception))
                        dc_energy_loss = None
                    try:
                        dc_energy_inverters = conversion_loss_values['dc_energy_inverter']
                        print dc_energy_inverters
                    except Exception as exception:
                        print ("Exception4 : " + str(exception))
                        dc_energy_inverters = None
                    try:
                        ac_energy_inverters_ap = conversion_loss_values['ac_energy_inverter']
                    except Exception as exception:
                        print str(exception)
                        ac_energy_inverters_ap = None
                    try:
                        conversion_loss = dc_energy_inverters - ac_energy_inverters_ap
                    except Exception as exception:
                        print str(exception)
                        conversion_loss = None
                    try:
                        ac_energy_inverters = ac_loss_values['inverter_ac_energy']
                    except Exception as exception:
                        print str(exception)
                        ac_energy_inverters = None
                    try:
                        ac_energy_meters = ac_loss_values['meter_ac_energy']
                    except Exception as exception:
                        print str(exception)
                        ac_energy_meters = None
                    try:
                        ac_energy_loss = ac_energy_inverters - ac_energy_meters
                    except Exception as exception:
                        print str(exception)
                        ac_energy_loss = None
                except Exception as exception:
                    print ("Error in getting enerly loss values for current day " + str(exception))

                try:
                    if len(daily_energy_loss) == 0:
                        print("first Daily loss entry for current data")
                        daily_entry = EnergyLossTableNew.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                     count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                     identifier=plant.metadata.plantmetasource.sourceKey,
                                                                     ts=final_time.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                     dc_energy_ajb=dc_energy_ajb,
                                                                     dc_energy_inverters_ajb=dc_energy_inverters_ajb,
                                                                     dc_energy_inverters=dc_energy_inverters,
                                                                     ac_energy_inverters_ap=ac_energy_inverters_ap,
                                                                     ac_energy_inverters=ac_energy_inverters,
                                                                     ac_energy_meters=ac_energy_meters,
                                                                     dc_energy_loss=dc_energy_loss,
                                                                     conversion_loss=conversion_loss,
                                                                     ac_energy_loss=ac_energy_loss,
                                                                     updated_at=current_time)
                        daily_entry.save()

                        hourly_entry = EnergyLossTableNew.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                         count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                         identifier=plant.metadata.plantmetasource.sourceKey,
                                                                         ts=current_time.replace(minute=0,second=0,microsecond=0),
                                                                         dc_energy_ajb=dc_energy_ajb,
                                                                         dc_energy_inverters_ajb=dc_energy_inverters_ajb,
                                                                         dc_energy_inverters=dc_energy_inverters,
                                                                         ac_energy_inverters_ap=ac_energy_inverters_ap,
                                                                         ac_energy_inverters=ac_energy_inverters,
                                                                         ac_energy_meters=ac_energy_meters,
                                                                         dc_energy_loss=dc_energy_loss,
                                                                         conversion_loss=conversion_loss,
                                                                         ac_energy_loss=ac_energy_loss,
                                                                         updated_at=current_time)
                        hourly_entry.save()
                    else:
                        daily_energy_loss.update(dc_energy_ajb=dc_energy_ajb,
                                                 dc_energy_inverters_ajb=dc_energy_inverters_ajb,
                                                 dc_energy_inverters=dc_energy_inverters,
                                                 ac_energy_inverters_ap=ac_energy_inverters_ap,
                                                 ac_energy_inverters=ac_energy_inverters,
                                                 ac_energy_meters=ac_energy_meters,
                                                 dc_energy_loss=dc_energy_loss,
                                                 conversion_loss=conversion_loss,
                                                 ac_energy_loss=ac_energy_loss,
                                                 updated_at=current_time)
                        hourly_entry = EnergyLossTableNew.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                         count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                         identifier=plant.metadata.plantmetasource.sourceKey,
                                                                         ts=current_time.replace(minute=0,second=0,microsecond=0),
                                                                         dc_energy_ajb=dc_energy_ajb,
                                                                         dc_energy_inverters_ajb=dc_energy_inverters_ajb,
                                                                         dc_energy_inverters=dc_energy_inverters,
                                                                         ac_energy_inverters_ap=ac_energy_inverters_ap,
                                                                         ac_energy_inverters=ac_energy_inverters,
                                                                         ac_energy_meters=ac_energy_meters,
                                                                         dc_energy_loss=dc_energy_loss,
                                                                         conversion_loss=conversion_loss,
                                                                         ac_energy_loss=ac_energy_loss,
                                                                         updated_at=current_time)
                        hourly_entry.save()

                    inverters = plant.independent_inverter_units.all()
                    for inverter in inverters:
                        inverter_daily_energy_loss = EnergyLossTableNew.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                    identifier=inverter.sourceKey,
                                                                                    ts=last_entry.replace(hour=0, minute=0, second=0, microsecond=0))
                        try:
                            inverter_dc_energy_ajb = dc_loss_values['dc_energy_ajb_' + str(inverter.name)]
                        except:
                            inverter_dc_energy_ajb = None
                        try:
                            print "conversion_loss_values"
                            print conversion_loss_values
                            inverter_dc_energy_inverters = dc_loss_values['dc_energy_' + str(inverter.name)]
                            print dc_energy_inverters, "inverter_dc_energy_inverters"
                        except Exception as exception:
                            print str(exception)
                            inverter_dc_energy_inverters = None
                        try:
                           inverter_dc_energy_loss =  inverter_dc_energy_ajb - inverter_dc_energy_inverters
                        except:
                           inverter_dc_energy_loss = None
                        try:
                            inverter_ac_energy_inverters_ap = conversion_loss_values['dc_energy_' + str(inverter.name)]
                        except Exception as exception:
                            print str(exception)
                            inverter_ac_energy_inverters_ap = None
                        try:
                            inverter_ac_energy_inverter = conversion_loss_values['ac_energy_'+str(inverter.name)]
                        except Exception as exception:
                            print str(exception)
                            inverter_ac_energy_inverter = None
                        try:
                            print inverter_ac_energy_inverters_ap, inverter_ac_energy_inverter
                            inverter_conversion_loss = inverter_ac_energy_inverters_ap - inverter_ac_energy_inverter
                        except Exception as exception:
                            print str(str(exception))
                            inverter_conversion_loss = None
                        if len(inverter_daily_energy_loss) == 0:
                            inverter_daily_entry = EnergyLossTableNew.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                     count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                     identifier=inverter.sourceKey,
                                                                                     ts=last_entry.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                                     dc_energy_ajb=inverter_dc_energy_ajb,
                                                                                     dc_energy_inverters=inverter_dc_energy_inverters,
                                                                                     ac_energy_inverters_ap=inverter_ac_energy_inverters_ap,
                                                                                     ac_energy_inverters=inverter_ac_energy_inverter,
                                                                                     dc_energy_loss=inverter_dc_energy_loss,
                                                                                     conversion_loss=inverter_conversion_loss,
                                                                                     updated_at=current_time
                                                                                    )
                            inverter_daily_entry.save()
                            hourly_entry = EnergyLossTableNew.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                         count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                         identifier=inverter.sourceKey,
                                                                         ts=current_time.replace(minute=0,second=0,microsecond=0),
                                                                         dc_energy_ajb=inverter_dc_energy_ajb,
                                                                         dc_energy_inverters=inverter_dc_energy_inverters,
                                                                         ac_energy_inverters_ap=inverter_ac_energy_inverters_ap,
                                                                         ac_energy_inverters=inverter_ac_energy_inverter,
                                                                         dc_energy_loss=inverter_dc_energy_loss,
                                                                         conversion_loss=inverter_conversion_loss,
                                                                         updated_at=current_time)
                            hourly_entry.save()
                        else:
                            inverter_daily_energy_loss.update(dc_energy_ajb=inverter_dc_energy_ajb,
                                                             dc_energy_inverters=inverter_dc_energy_inverters,
                                                             ac_energy_inverters_ap=inverter_ac_energy_inverters_ap,
                                                             ac_energy_inverters=inverter_ac_energy_inverter,
                                                             dc_energy_loss=inverter_dc_energy_loss,
                                                             conversion_loss=inverter_conversion_loss,
                                                             updated_at=current_time
                                                             )
                            hourly_entry = EnergyLossTableNew.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                             count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                             identifier=inverter.sourceKey,
                                                                             ts=current_time.replace(minute=0,second=0,microsecond=0),
                                                                             dc_energy_ajb=inverter_dc_energy_ajb,
                                                                             dc_energy_inverters=inverter_dc_energy_inverters,
                                                                             ac_energy_inverters_ap=inverter_ac_energy_inverters_ap,
                                                                             ac_energy_inverters=inverter_ac_energy_inverter,
                                                                             dc_energy_loss=inverter_dc_energy_loss,
                                                                             conversion_loss=inverter_conversion_loss,
                                                                             updated_at=current_time)
                            hourly_entry.save()
                except Exception as exception:
                    print ("Error in storing the current energy loss values " + str(exception))
    except Exception as exception:
        print str(exception)