from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model


# write history by user
class DataWriteHistoryByUser(Model):
    """
    Defining class
    """
    user_id = columns.Integer(partition_key=True, primary_key=True)
    success = columns.Boolean(partition_key=True, primary_key=True)
    date = columns.Date(partition_key=True, primary_key=True)
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    source_key = columns.Text(partition_key=False, primary_key=True)
    validated = columns.Boolean(partition_key=False, primary_key=True)


# write history by source
class DataWriteHistoryBySource(Model):
    source_key = columns.Text(partition_key=True, primary_key=True)
    success = columns.Boolean(partition_key=True, primary_key=True)
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    user_id = columns.Integer(index=True)
    validated = columns.Boolean(partition_key=False, primary_key=True)


# action log by user
class ActionLogByUser(Model):
    user_id = columns.Integer(partition_key=True, primary_key=True)
    success = columns.Boolean(partition_key=True, primary_key=True)
    date = columns.Date(partition_key=True, primary_key=True)
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    action = columns.Text(partition_key=False, primary_key=True)
    uuid = columns.TimeUUID(partition_key=False, primary_key=True)

    response_code = columns.Integer(index=True)
    source_key = columns.Text()
    ip_address = columns.Inet()
    comments = columns.Map(columns.Text, columns.Text)


# action log by source
class ActionLogBySource(Model):
    source_key = columns.Text(partition_key=True, primary_key=True)
    success = columns.Boolean(partition_key=True, primary_key=True)
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    action = columns.Text(partition_key=False, primary_key=True)
    response_code = columns.Integer(index=True)
    ip_address = columns.Inet()
    comments = columns.Map(columns.Text, columns.Text)


# action log by error [to write security and debug logs]
class ActionLogByError(Model):
    error = columns.Text(partition_key=True, primary_key=True)
    date = columns.Date(partition_key=True, primary_key=True)
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    user_id = columns.Integer(partition_key=False, primary_key=True)
    action = columns.Text(partition_key=False, primary_key=True)
    success = columns.Boolean(partition_key=False, primary_key=True)
    uuid = columns.TimeUUID(partition_key=False, primary_key=True)

    ip_address = columns.Inet()
    comments = columns.Map(columns.Text, columns.Text)


# log independent errors, such as key_error
class IndependentErrors(Model):
    error = columns.Text(partition_key=True, primary_key=True)
    date = columns.Date(partition_key=True, primary_key=True)
    ts = columns.DateTime(partition_key=False, primary_key=True)
    action = columns.Text(partition_key=False, primary_key=True)
    uuid = columns.TimeUUID(partition_key=False, primary_key=True)

    response_code = columns.Integer(index=True)
    ip_address = columns.Inet()
    comments = columns.Map(columns.Text, columns.Text)


class DataCountTable(Model):
    # settings.DATA_COUNT_TYPES
    timestamp_type = columns.Text(partition_key=True, primary_key=True)
    # settings.DATA_COUNT_PERIODS
    count_time_period = columns.Integer(partition_key=True, primary_key=True)

    # primary keys
    identifier = columns.Text(partition_key=True, primary_key=True)
    ts = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")

    valid_records = columns.Counter()
    invalid_records = columns.Counter()