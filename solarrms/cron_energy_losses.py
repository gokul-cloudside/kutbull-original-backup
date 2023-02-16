import datetime
from solarrms.models import PlantMetaSource, EnergyLossTable
from django.utils import timezone
from django.conf import settings
import pytz
from solarrms.solarutils import get_all_energy_losses_aggregated

start_date = "2016-08-22 00:00:00"

def compute_energy_losses():
    try:
        print("Energy loss cronjob started")
        plant_meta_sources = PlantMetaSource.objects.all()
        for plant_meta_source in plant_meta_sources:
            print("Energy loss calculation for : " + str(plant_meta_source.plant.slug))
            try:
                tz = pytz.timezone(plant_meta_source.dataTimezone)
            except:
                print ("Error in getting tz")
            try:
                current_time = timezone.now()
                current_time = current_time.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
            except Exception as exc:
                print(str(exc))
                current_time = timezone.now()

            energy_losses_last_entry = EnergyLossTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                      count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                      identifier=plant_meta_source.sourceKey).limit(1).values_list('ts')
            if energy_losses_last_entry:
                last_entry_values = [item[0] for item in energy_losses_last_entry]
                last_entry  = last_entry_values[0]
                print("last_time_entry: ", last_entry)
                if last_entry.tzinfo is None:
                    last_entry =pytz.utc.localize(last_entry)
                    last_entry = last_entry.astimezone(pytz.timezone(plant_meta_source.dataTimezone))
            else:
                last_entry = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                if last_entry.tzinfo is None:
                    last_entry = tz.localize(last_entry)
                    last_entry = last_entry.astimezone(pytz.timezone(plant_meta_source.dataTimezone))

            duration = (current_time - last_entry)
            duration_days = duration.days
            loop_count = 0
            while loop_count < duration_days:
                print(duration_days)
                print last_entry
                plant_shut_down_time = last_entry.replace(hour=19, minute=0, second=0, microsecond=0)
                plant_start_time = last_entry.replace(hour=6, minute=0, second=0, microsecond=0)
                last_entry = plant_start_time

                daily_energy_loss = EnergyLossTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=plant_meta_source.sourceKey,
                                                                   ts=last_entry.replace(hour=0, minute=0, second=0, microsecond=0))
                try:
                    energy_loss_values = get_all_energy_losses_aggregated(plant_start_time,plant_shut_down_time,plant_meta_source.plant)
                    dc_energy_ajb = energy_loss_values['dc_energy_from_ajb'] if energy_loss_values['dc_energy_from_ajb'] is not 'NA' else None
                    dc_energy_inverters = energy_loss_values['dc_energy_from_inverters'] if energy_loss_values['dc_energy_from_inverters'] is not 'NA' else None
                    ac_energy_inverters_ap = energy_loss_values['ac_energy_from_inverters_ap'] if energy_loss_values['ac_energy_from_inverters_ap'] is not 'NA' else None
                    ac_energy_inverters = energy_loss_values['ac_energy_from_inverters'] if energy_loss_values['ac_energy_from_inverters'] is not 'NA' else None
                    ac_energy_meters = energy_loss_values['ac_energy_from_meters'] if energy_loss_values['ac_energy_from_meters'] is not 'NA' else None
                    dc_energy_loss = energy_loss_values['dc_energy_loss'] if energy_loss_values['dc_energy_loss'] is not 'NA' else None
                    conversion_loss = energy_loss_values['conversion_loss'] if energy_loss_values['conversion_loss'] is not 'NA' else None
                    ac_energy_loss = energy_loss_values['ac_energy_loss'] if energy_loss_values['ac_energy_loss'] is not 'NA' else None

                except Exception as exception:
                    print(str(exception))
                    last_entry = last_entry + datetime.timedelta(days=1)
                    duration_days -= 1
                    continue

                try:
                    if len(daily_energy_loss) == 0:
                        daily_entry = EnergyLossTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                     count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                     identifier=plant_meta_source.sourceKey,
                                                                     ts=last_entry.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                     dc_energy_ajb=dc_energy_ajb,
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
                                                 dc_energy_inverters=dc_energy_inverters,
                                                 ac_energy_inverters_ap=ac_energy_inverters_ap,
                                                 ac_energy_inverters=ac_energy_inverters,
                                                 ac_energy_meters=ac_energy_meters,
                                                 dc_energy_loss=dc_energy_loss,
                                                 conversion_loss=conversion_loss,
                                                 ac_energy_loss=ac_energy_loss,
                                                 updated_at=current_time)
                    inverters = plant_meta_source.plant.independent_inverter_units.all()
                    for inverter in inverters:
                        inverter_daily_energy_loss = EnergyLossTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                    identifier=inverter.sourceKey,
                                                                                    ts=last_entry.replace(hour=0, minute=0, second=0, microsecond=0))

                        inverter_dc_energy_ajb = energy_loss_values['dc_energy_ajb_'+inverter.name] if energy_loss_values['dc_energy_ajb_'+inverter.name] is not 'NA' else None
                        inverter_dc_energy_inverters = energy_loss_values['dc_energy_'+inverter.name] if energy_loss_values['dc_energy_'+inverter.name] is not 'NA' else None
                        inverter_ac_energy_inverters_ap = energy_loss_values['ac_energy_ap_'+inverter.name] if energy_loss_values['ac_energy_ap_'+inverter.name] is not 'NA' else None
                        inverter_ac_energy_inverters = energy_loss_values['ac_energy_'+inverter.name] if energy_loss_values['ac_energy_'+inverter.name] is not 'NA' else None
                        inverter_dc_energy_loss = inverter_dc_energy_ajb - inverter_dc_energy_inverters if inverter_dc_energy_ajb and inverter_dc_energy_inverters else None
                        inverter_conversion_loss = inverter_dc_energy_inverters - inverter_ac_energy_inverters_ap if inverter_dc_energy_inverters and inverter_ac_energy_inverters_ap else None

                        if len(inverter_daily_energy_loss) == 0:
                            inverter_daily_entry = EnergyLossTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                  count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                  identifier=inverter.sourceKey,
                                                                                  ts=last_entry.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                                  dc_energy_ajb=inverter_dc_energy_ajb,
                                                                                  dc_energy_inverters=inverter_dc_energy_inverters,
                                                                                  ac_energy_inverters_ap=inverter_ac_energy_inverters_ap,
                                                                                  ac_energy_inverters=inverter_ac_energy_inverters,
                                                                                  dc_energy_loss=inverter_dc_energy_loss,
                                                                                  conversion_loss=inverter_conversion_loss,
                                                                                  updated_at=current_time
                                                                                  )
                            inverter_daily_entry.save()
                        else:
                            inverter_daily_energy_loss.update(dc_energy_ajb=inverter_dc_energy_ajb,
                                                             dc_energy_inverters=inverter_dc_energy_inverters,
                                                             ac_energy_inverters_ap=inverter_ac_energy_inverters_ap,
                                                             ac_energy_inverters=inverter_ac_energy_inverters,
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

            if duration_days == 0 :
                print("Current Energy Loss computation for plant : {0}".format(str(plant_meta_source.plant)))
                initial_time = current_time.replace(hour=6, minute=0, second=0, microsecond=0)
                final_time = current_time
                plant_shut_down_time = final_time.replace(hour=19, minute=0, second=0, microsecond=0)
                plant_start_time = final_time.replace(hour=6, minute=0, second=0, microsecond=0)
                # get the entry daily Energy loss entry as per current time
                daily_energy_loss = EnergyLossTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                   count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                   identifier=plant_meta_source.sourceKey,
                                                                   ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0))
                try:
                    energy_loss_values = get_all_energy_losses_aggregated(plant_start_time,current_time,plant_meta_source.plant)
                    dc_energy_ajb = energy_loss_values['dc_energy_from_ajb'] if energy_loss_values['dc_energy_from_ajb'] is not 'NA' else None
                    dc_energy_inverters = energy_loss_values['dc_energy_from_inverters'] if energy_loss_values['dc_energy_from_inverters'] is not 'NA' else None
                    ac_energy_inverters_ap = energy_loss_values['ac_energy_from_inverters_ap'] if energy_loss_values['ac_energy_from_inverters_ap'] is not 'NA' else None
                    ac_energy_inverters = energy_loss_values['ac_energy_from_inverters'] if energy_loss_values['ac_energy_from_inverters'] is not 'NA' else None
                    ac_energy_meters = energy_loss_values['ac_energy_from_meters'] if energy_loss_values['ac_energy_from_meters'] is not 'NA' else None
                    dc_energy_loss = energy_loss_values['dc_energy_loss'] if energy_loss_values['dc_energy_loss'] is not 'NA' else None
                    conversion_loss = energy_loss_values['conversion_loss'] if energy_loss_values['conversion_loss'] is not 'NA' else None
                    ac_energy_loss = energy_loss_values['ac_energy_loss'] if energy_loss_values['ac_energy_loss'] is not 'NA' else None
                except Exception as ex:
                    print("Exception in energy loss calculation: %s", str(ex))
                    continue
                try:
                    # If entry does not exist for energy loss and it is for current data
                    if len(daily_energy_loss) == 0:
                        print("first Daily loss entry for current data")
                        daily_entry = EnergyLossTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                     count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                     identifier=plant_meta_source.sourceKey,
                                                                     ts=final_time.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                     dc_energy_ajb=dc_energy_ajb,
                                                                     dc_energy_inverters=dc_energy_inverters,
                                                                     ac_energy_inverters_ap=ac_energy_inverters_ap,
                                                                     ac_energy_inverters=ac_energy_inverters,
                                                                     ac_energy_meters=ac_energy_meters,
                                                                     dc_energy_loss=dc_energy_loss,
                                                                     conversion_loss=conversion_loss,
                                                                     ac_energy_loss=ac_energy_loss,
                                                                     updated_at=current_time)
                        daily_entry.save()

                        hourly_entry = EnergyLossTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                      count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                      identifier=plant_meta_source.sourceKey,
                                                                      ts=current_time.replace(minute=0,second=0,microsecond=0),
                                                                      dc_energy_ajb=dc_energy_ajb,
                                                                      dc_energy_inverters=dc_energy_inverters,
                                                                      ac_energy_inverters_ap=ac_energy_inverters_ap,
                                                                      ac_energy_inverters=ac_energy_inverters,
                                                                      ac_energy_meters=ac_energy_meters,
                                                                      dc_energy_loss=dc_energy_loss,
                                                                      conversion_loss=conversion_loss,
                                                                      ac_energy_loss=ac_energy_loss,
                                                                      updated_at=current_time)
                        hourly_entry.save()

                        inverters = plant_meta_source.plant.independent_inverter_units.all()
                        for inverter in inverters:
                            inverter_daily_energy_loss = EnergyLossTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                        count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                        identifier=inverter.sourceKey,
                                                                                        ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0))

                            inverter_dc_energy_ajb = energy_loss_values['dc_energy_ajb_'+inverter.name] if energy_loss_values['dc_energy_ajb_'+inverter.name] is not 'NA' else None
                            inverter_dc_energy_inverters = energy_loss_values['dc_energy_'+inverter.name] if energy_loss_values['dc_energy_'+inverter.name] is not 'NA' else None
                            inverter_ac_energy_inverters_ap = energy_loss_values['ac_energy_ap_'+inverter.name] if energy_loss_values['ac_energy_ap_'+inverter.name] is not 'NA' else None
                            inverter_ac_energy_inverters = energy_loss_values['ac_energy_'+inverter.name] if energy_loss_values['ac_energy_'+inverter.name] is not 'NA' else None
                            inverter_dc_energy_loss = inverter_dc_energy_ajb - inverter_dc_energy_inverters if inverter_dc_energy_ajb and inverter_dc_energy_inverters else None
                            inverter_conversion_loss = inverter_dc_energy_inverters - inverter_ac_energy_inverters_ap if inverter_dc_energy_inverters and inverter_ac_energy_inverters_ap else None

                            if len(inverter_daily_energy_loss)==0:
                                inverter_daily_entry = EnergyLossTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                             count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                             identifier=inverter.sourceKey,
                                                                             ts=final_time.replace(hour=0,minute=0,second=0,microsecond=0),
                                                                             dc_energy_ajb=inverter_dc_energy_ajb,
                                                                             dc_energy_inverters=inverter_dc_energy_inverters,
                                                                             ac_energy_inverters_ap=inverter_ac_energy_inverters_ap,
                                                                             ac_energy_inverters=inverter_ac_energy_inverters,
                                                                             dc_energy_loss=inverter_dc_energy_loss,
                                                                             conversion_loss=inverter_conversion_loss,
                                                                             updated_at=current_time)
                                inverter_daily_entry.save()

                                inverter_hourly_entry = EnergyLossTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                              count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                              identifier=inverter.sourceKey,
                                                                              ts=current_time.replace(minute=0,second=0,microsecond=0),
                                                                              dc_energy_ajb=inverter_dc_energy_ajb,
                                                                              dc_energy_inverters=inverter_dc_energy_inverters,
                                                                              ac_energy_inverters_ap=inverter_ac_energy_inverters_ap,
                                                                              ac_energy_inverters=inverter_ac_energy_inverters,
                                                                              dc_energy_loss=inverter_dc_energy_loss,
                                                                              conversion_loss=inverter_conversion_loss,
                                                                              updated_at=current_time)
                                inverter_hourly_entry.save()

                    # If entry exists for daily energy loss and current time is withing the range of plant operational time
                    elif len(daily_energy_loss) > 0 and final_time < plant_shut_down_time and final_time > plant_start_time:
                        print("updating Energy loss in operational hour")
                        daily_energy_loss.update(dc_energy_ajb=dc_energy_ajb,
                                                 dc_energy_inverters=dc_energy_inverters,
                                                 ac_energy_inverters_ap=ac_energy_inverters_ap,
                                                 ac_energy_inverters=ac_energy_inverters,
                                                 ac_energy_meters=ac_energy_meters,
                                                 dc_energy_loss=dc_energy_loss,
                                                 conversion_loss=conversion_loss,
                                                 ac_energy_loss=ac_energy_loss,
                                                 updated_at=final_time)

                        hourly_entry = EnergyLossTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                      count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                      identifier=plant_meta_source.sourceKey,
                                                                      ts=current_time.replace(minute=0,second=0,microsecond=0),
                                                                      dc_energy_ajb=dc_energy_ajb,
                                                                      dc_energy_inverters=dc_energy_inverters,
                                                                      ac_energy_inverters_ap=ac_energy_inverters_ap,
                                                                      ac_energy_inverters=ac_energy_inverters,
                                                                      ac_energy_meters=ac_energy_meters,
                                                                      dc_energy_loss=dc_energy_loss,
                                                                      conversion_loss=conversion_loss,
                                                                      ac_energy_loss=ac_energy_loss,
                                                                      updated_at=current_time)
                        hourly_entry.save()

                        inverters = plant_meta_source.plant.independent_inverter_units.all()
                        for inverter in inverters:
                            inverter_daily_energy_loss = EnergyLossTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                        count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                        identifier=inverter.sourceKey,
                                                                                        ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0))

                            inverter_dc_energy_ajb = energy_loss_values['dc_energy_ajb_'+inverter.name] if energy_loss_values['dc_energy_ajb_'+inverter.name] is not 'NA' else None
                            inverter_dc_energy_inverters = energy_loss_values['dc_energy_'+inverter.name] if energy_loss_values['dc_energy_'+inverter.name] is not 'NA' else None
                            inverter_ac_energy_inverters_ap = energy_loss_values['ac_energy_ap_'+inverter.name] if energy_loss_values['ac_energy_ap_'+inverter.name] is not 'NA' else None
                            inverter_ac_energy_inverters = energy_loss_values['ac_energy_'+inverter.name] if energy_loss_values['ac_energy_'+inverter.name] is not 'NA' else None
                            inverter_dc_energy_loss = inverter_dc_energy_ajb - inverter_dc_energy_inverters if inverter_dc_energy_ajb and inverter_dc_energy_inverters else None
                            inverter_conversion_loss = inverter_dc_energy_inverters - inverter_ac_energy_inverters_ap if inverter_dc_energy_inverters and inverter_ac_energy_inverters_ap else None

                            inverter_daily_energy_loss.update(dc_energy_ajb=inverter_dc_energy_ajb,
                                                              dc_energy_inverters=inverter_dc_energy_inverters,
                                                              ac_energy_inverters_ap=inverter_ac_energy_inverters_ap,
                                                              ac_energy_inverters=inverter_ac_energy_inverters,
                                                              dc_energy_loss=inverter_dc_energy_loss,
                                                              conversion_loss=inverter_conversion_loss,
                                                              updated_at=current_time)

                            inverter_hourly_entry = EnergyLossTable.objects.create(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                   count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                                                   identifier=inverter.sourceKey,
                                                                                   ts=current_time.replace(minute=0,second=0,microsecond=0),
                                                                                   dc_energy_ajb=inverter_dc_energy_ajb,
                                                                                   dc_energy_inverters=inverter_dc_energy_inverters,
                                                                                   ac_energy_inverters_ap=inverter_ac_energy_inverters_ap,
                                                                                   ac_energy_inverters=inverter_ac_energy_inverters,
                                                                                   dc_energy_loss=inverter_dc_energy_loss,
                                                                                   conversion_loss=inverter_conversion_loss,
                                                                                   updated_at=current_time)
                            inverter_hourly_entry.save()
                    else:
                        daily_energy_loss.update(updated_at=final_time)
                        inverters = plant_meta_source.plant.independent_inverter_units.all()
                        for inverter in inverters:
                            inverter_daily_energy_loss = EnergyLossTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                        count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                                                                                        identifier=inverter.sourceKey,
                                                                                        ts=final_time.replace(hour=0, minute=0, second=0, microsecond=0))
                            inverter_daily_energy_loss.update(updated_at=final_time)
                except Exception as ex:
                    print("Exception in energy loss calculation: %s", str(ex))
                    continue

    except Exception as exception:
        print(str(exception))