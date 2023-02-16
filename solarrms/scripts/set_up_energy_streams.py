from solarrms.models import SolarPlant

ENERGY_CALCULATION_STREAMS = {'waaneep':'KWH',
                              'dominicus':'kWhT(I)',
                              'yerangiligi':'Wh_RECEIVED',
                              'gsi':'Wh_RECEIVED',
                              'hyderabadhouse':'Wh_RECEIVED',
                              'rashtrapatibhawanauditorium':'Wh_RECEIVED',
                              'sardarpatelbhawan':'Wh_RECEIVED',
                              'nizampalace':'Wh_RECEIVED',
                              'airportmetrodepot':'Wh_RECEIVED',
                              'rashtrapatibhawangarage': 'Wh_RECEIVED',
                              'oldjnuclubbuilding': 'Wh_RECEIVED',
                              'oldjnulibraryandclubbuilding':'Wh_RECEIVED',
                              'hacgocomplex':'Wh_RECEIVED',
                              'rbl':'Wh_DELIVERED',
                              'ranetrw':'Wh_RECEIVED',
                              'gmr': 'Wh_RECEIVED',
                              'thunganivillage':'Wh_RECEIVED',
                              'shramsaktibhawan':'Wh_RECEIVED',
                              'unipatch':'Wh_RECEIVED',
                              'rrkabel':'Wh_RECEIVED',
                              'uran':'Wh_RECEIVED',
                              'councilhouse':'Wh_RECEIVED',
                              'mohanestate':'Wh_RECEIVED',
                              'goipresssantragachi':'Wh_RECEIVED',
                              'gisochurchlane':'Wh_RECEIVED',
                              'dgcis':'Wh_RECEIVED',
                              'goiformstoretemplestreet':'Wh_RECEIVED',
                              'ezcc':'Wh_RECEIVED',
                              'gupl': 'Wh_RECEIVED',
                              'ranergy':'Wh_RECEIVED',
                              'lohia':'Wh_FINAL',
                              'pavagada':'Wh_DELIVERED',
                              'demochemtrols':'Wh_RECEIVED'}

ENERGY_METER_STREAM_UNITS = {'waaneep' : 'MWH',
                             'yerangiligi': 'MWH',
                             'gsi':'W',
                             'nizampalace':'W',
                             'thunganivillage':'MWH',
                             'lohia': 'MWH',
                             'demochemtrols': 'MWH'}


def set_up_enegy_calculation_devices_and_streams():
    try:
        plants = SolarPlant.objects.all()
        for plant in plants:
            print ("setting up for : " + str(plant.name))
            meta = plant.metadata.plantmetasource
            if str(plant.slug)=='palladam':
                meta.energy_calculation_device = 'PLANT_META'
                meta.energy_calculation_stream = 'DAILY_PLANT_ENERGY'
                meta.save()
            elif str(plant.slug) in ['faro', 'santarem','seia', 'castelo']:
                meta.energy_calculation_device = 'INVERTER_POWER'
                meta.energy_calculation_stream = 'ACTIVE_POWER'
                meta.save()
            elif str(plant.slug) in ENERGY_CALCULATION_STREAMS:
                meta.energy_calculation_device = 'ENERGY_METER'
                meta.energy_calculation_stream = ENERGY_CALCULATION_STREAMS[str(plant.slug)]
                if str(plant.slug) in ENERGY_METER_STREAM_UNITS:
                    meta.energy_calculation_stream_unit = ENERGY_METER_STREAM_UNITS[str(plant.slug)]
                meta.save()
            else:
                if meta.inverters_sending_daily_generation is True:
                    meta.energy_calculation_device = 'INVERTER_ENERGY'
                    meta.energy_calculation_stream = 'DAILY_YIELD'
                    meta.save()
                else:
                    meta.energy_calculation_device = 'INVERTER_ENERGY'
                    meta.energy_calculation_stream = 'TOTAL_YIELD'
                    meta.save()
    except Exception as exception:
        print str(exception)