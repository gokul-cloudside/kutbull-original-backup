import pandas as pd
import numpy as np
import pytz, sys
from dataglen.models import ValidDataStorageByStream, Sensor
from datetime import datetime
import time

def get_integrated_stream_value(source_key, startTime, endTime, stream_name):
    try:
        try:
            source = Sensor.objects.get(sourceKey=source_key)
        except Exception as exception:
            print(str(exception))
        if source.dataTimezone:
            tz = pytz.timezone(source.dataTimezone)
        else:
            tz = pytz.timezone(pytz.utc.zone)
        stream_data = ValidDataStorageByStream.objects.filter(source_key=source_key,
                                                              stream_name=stream_name,
                                                              timestamp_in_data__gte=startTime,
                                                              timestamp_in_data__lte=endTime).values_list('stream_value', 'timestamp_in_data')

        timestamp_seconds = []
        # populate data
        values = [float(item[0]) for item in stream_data]
        values.reverse()
        # populate timestamps
        timestamps = [item[1].replace(tzinfo=pytz.utc).astimezone(tz).isoformat() for item in stream_data]
        timestamps.reverse()
        for value in timestamps:
            try:
                time_value = datetime.strptime(str(value), '%Y-%m-%dT%H:%M:%S.%f' + '+05:30')
            except Exception as exception:
                time_value = datetime.strptime(str(value), '%Y-%m-%dT%H:%M:%S' + '+05:30')
                pass
            time_seconds = time.mktime(time_value.timetuple())/60
            timestamp_seconds.append(time_seconds)
        #print(timestamp_seconds)
        #integrated_value = integrate.trapz(values,timestamps)
        integrated_value = np.trapz(values, x=timestamp_seconds)
        sum = 0
        for i in range(len(values)):
            sum += values[i]
        print('average', sum/len(values))
        print('integration', integrated_value)
        try:
            df_stream = pd.DataFrame(pd.Series(values), columns=[stream_name])
            df_stream['timestamp'] = timestamps
        except Exception as exception:
            print(str(exception))
        #print(df_stream.to_dict('records'))
        #print(df_stream)
        return integrated_value

    except Exception as exception:
        print(str(exception))