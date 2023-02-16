from dataglen.models import ValidDataStorageByStream

def get_stream_data(source, stream_name, limit):
    try:
        stream_data = ValidDataStorageByStream.objects.filter(source_key=source.sourceKey,
                                                              stream_name=stream_name).limit(limit)
        data = []
        for value in reversed(stream_data):
            data.append({"x": int(value.timestamp_in_data.strftime("%s")) * 1000,
                         "y": value.stream_value})
        return data
    except Exception as E:
        return None


# returns stream data as a dictionary
def get_sensor_data_in_utc(source, streams_names, data_len_limit):
    data = {}

    for stream in streams_names:
        stream_data = get_stream_data(source, stream, data_len_limit)
        if stream_data:
            data[stream] = [{'key': stream, 'values': stream_data}]

    return data
