from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model


'''class SourceMonitoringTable(Model):
    user_id = columns.Integer(primary_key=True, partition_key=True)
    source_key = columns.Text(partition_key=True, primary_key=True)
    valid_entry = columns.Boolean(partition_key=False, primary_key=True)
    ts = columns.DateTime()'''


class SourceMonitoring(Model):
    source_key = columns.Text(partition_key=True, primary_key=True)
    valid_entry = columns.Boolean(partition_key=False, primary_key=True)
    ts = columns.DateTime()
