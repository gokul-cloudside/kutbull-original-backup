import logging
from solarrms.models import *
from dataglen.models import *
import pytz

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

mappings = {'DdSxkdHWC7RQ4hk': '8nzZSCjx0l6x9TQ',
            'w3R6qm8goRCg8fs': 'b3tHFAv0tRQl7BV',
            'nMT5lQio14sVbUR': 'mLKUMGbVp7WK3Th'}

EASTERN = pytz.timezone('US/Eastern')
UTC = pytz.UTC
IST = pytz.timezone('Asia/Kolkata')

def update_tz(dt, tz_name):
    try:
        tz = pytz.timezone(tz_name)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
            return dt.astimezone(tz).replace(tzinfo=None)
        else:
            return dt.astimezone(tz).replace(tzinfo=None)
    except Exception as exc:
        return dt

def copy_demo_data():
    from_plant = SolarPlant.objects.get(slug="uran")
    to_plant = SolarPlant.objects.get(slug="boston")
    # for inverter in from_plant.independent_inverter_units.all():
    #     new_inverter = IndependentInverter.objects.create(user=User.objects.get(id=to_plant.owner.organization_user.user_id),
    #                                                       name=inverter.name,
    #                                                       dataFormat="JSON",
    #                                                       isActive=True,
    #                                                       isMonitored=True,
    #                                                       plant=to_plant,
    #                                                       orientation=inverter.orientation)

    for inverter in from_plant.independent_inverter_units.all():
        for stream_name in inverter.fields.all():
            data_points = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                  stream_name=stream_name.name)
            for dp in data_points:
                ValidDataStorageByStream.objects.create(source_key=mappings[dp.source_key],
                                                        stream_name=dp.stream_name,
                                                        timestamp_in_data=dp.timestamp_in_data.replace(tzinfo=UTC).astimezone(IST).replace(tzinfo=EASTERN),
                                                        stream_value=dp.stream_value)


