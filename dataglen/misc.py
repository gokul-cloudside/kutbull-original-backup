import base64, random, hashlib, logging, json
import datetime

logger = logging.getLogger('dataglen.views')
# TODO: Change the logging status to an appropriate level at the time of deployment
logger.setLevel(logging.DEBUG)


def generate_hash_key():
    key = base64.b64encode(hashlib.sha256(str(random.getrandbits(256))).digest(),
                            random.choice(['rA', 'aZ', 'gQ', 'hH', 'hG', 'aR', 'DD'])).rstrip('==')
    return key[:15]


# returns the casted value, otherwise, None TODO return a meaningful message, add support for DA/TI fields
def return_true_value(data_point, name, type):
    try:
        if type == "INTEGER":
            return int(data_point.ifields[name])
        elif type == "FLOAT":
            return float(data_point.ffields[name])
        elif type == "TIMESTAMP":
            return int(data_point.ts.strftime("%s")) * 1000
            return int(datetime.strptime(data_point.ts, "%Y-%m-%d %H:%M:%S%Z").strftime("%s")) * 1000
            return int(datetime.strptime(data_point.tfields[name], "%Y-%m-%d %H:%M:%S").strftime("%s")) * 1000
        return None
    except Exception as exception:
        return None


def return_value_with_ts(data_point, name, type):
    try:
        ts = int(datetime.strptime(data_point.ts, "%Y-%m-%d %H:%M:%S").strftime("%s")) * 1000
        if type == "INTEGER":
            return ts, int(data_point.ifields[name])
        elif type == "FLOAT":
            return ts, float(data_point.ffields[name])
        return None
    except Exception as exception:
        return None


def get_payload(source, request):
    payload = None
    try:
        if source.dataFormat == "CSV":
            if source.csvDataKeyName:
                payload = request.POST[source.csvDataKeyName].strip()
            else:
                payload = request.body.strip()
        elif source.dataFormat == 'JSON':
            raw_data = request.body
            payload = json.loads(raw_data)
        elif source.dataFormat == 'ATOLL':
            payload = request.body.strip()
            logger.debug("get_payload : returning", payload)
        else:
            payload = request.body
        return payload
    except:
        return None


def split_payload(source, payload):
    try:
        if source.dataFormat == "CSV":
            return payload.strip().split("\n")
        elif source.dataFormat == "JSON":
            if type(payload) is dict:
                # it's a single json entry
                return [payload]
            elif type(payload) is list:
                # it's a list already of multiple data packets
                return payload
        elif source.dataFormat == "ATOLL":
            # these guys always send a single data packet
            logger.debug("split_payload: returning", [payload])
            return [payload]
        else:
            return payload
    except:
        return None


def split_single_entry(source, entry):
    try:
        if source.dataFormat == "CSV":
            return entry.strip().split(",")
        elif source.dataFormat == "ATOLL":
            stream_values = entry.strip().split("&")
            # convert key pair values in stream_values into a dict - then it will be a similar parsing as of json
            values = {}
            for se in stream_values:
                try:
                    values[se.strip().split("=")[0]] = se.strip().split("=")[1]
                except:
                    continue
            logger.debug("split_single_entry: returning ", values)
            return values
        else: #TODO How to split XML and JSON entries? URGENT!
            return entry
    except:
        return None

"""
def cassandra_count(start, end, db, table, sensor_key, where=None):
    if table == "sensor_data":
        #TODO HACK! remove this later once timezones have been handled
        start = start + timedelta(minutes=330)
        end = end + timedelta(minutes=330)

    count = 0
    seconds = 86400
    delta = datetime.timedelta(seconds=seconds)
    try:
        try:
            start = timezone.make_aware(start, timezone.get_default_timezone())
        except:
            pass
        try:
            end = timezone.make_aware(end, timezone.get_default_timezone())
        except:
            # no records
            pass
        cursor = connections[db].cursor()
        while start < end:
            if start + delta < end:
                end_time = start + delta
            else:
                end_time = end
            start_time = start
            # increase the count
            if where is None:
                query = "SELECT count(*) FROM " + table + " WHERE sk=" + "'"+str(sensor_key)+"'" + " AND ts >=" + "'"+(start_time.strftime("%Y-%m-%d %H:%M:%S%z"))+"'" + " AND ts <" + "'"+end_time.strftime("%Y-%m-%d %H:%M:%S%z")+"'" + " LIMIT"
            else:
                query = "SELECT count(*) FROM " + table + " WHERE sk=" + "'"+str(sensor_key)+"'" + " AND ts >=" + "'"+(start_time.strftime("%Y-%m-%d %H:%M:%S%z"))+"'" + " AND ts <" + "'"+end_time.strftime("%Y-%m-%d %H:%M:%S%z")+"'" + "AND " + where
            logger.debug(query)
            count += int(cursor.execute(query)[0]['count'])
            start = end_time
        return count
    except Exception as exception:
        logger.debug(exception)
        # some error
        return None

def count_data_records(start, end, sensor_key):
    return cassandra_count(start, end, "cassandra", "sensor_data", sensor_key)

def count_all_data_records(sensor_key, end):
    try:
        results = Sensor_Data.objects.filter(sk=sensor_key).order_by('ts').limit(1)
        # check if there are 0 data records
        if len(results) is 0:
            return 0
        start = results[0].ts
        return cassandra_count(start, end, "cassandra", "sensor_data", sensor_key)
    except Exception as exception:
        logger.debug(exception)
        return None

def count_success_logs(start, end, sensor_key):
    return cassandra_count(start, end, "cassandra", "action_log", sensor_key, "success = True LIMIT ALLOW FILTERING")

def count_discarded_logs(start, end, sensor_key):
    return cassandra_count(start, end, "cassandra", "action_log", sensor_key, "success = False LIMIT ALLOW FILTERING")

def count_all_success_logs(sensor_key, end):
    try:
        # no need to order by as that's inherently done by cassandra
        results = ActionLog.objects.filter(sk=sensor_key).limit(1)
        if len(results) == 0:
            # there are no log records, so check for all records starting valid time we retain the logs for
            start = end - datetime.timedelta(seconds=settings.DATAGLEN['LOG_EXPIRY'])
        else:
            start = results[0].ts
        return cassandra_count(start, end, "cassandra", "action_log", sensor_key, "success = True LIMIT ALLOW FILTERING")
    except Exception as exception:
        logger.debug(exception)
        return None

def count_all_discarded_records(sensor_key, end=timezone.now()):
    try:
        results = ActionLog.objects.filter(sk=sensor_key).limit(1)
        if len(results) == 0:
            # there are no log records, so check for all records starting valid time we retain the logs for
            start = end - datetime.timedelta(seconds=settings.DATAGLEN['LOG_EXPIRY'])
        else:
            start = results[0].ts
        return cassandra_count(start, end, "cassandra", "action_log", sensor_key, "success = False LIMIT ALLOW FILTERING")
    except Exception as exception:
        logger.debug(exception)
        return None """