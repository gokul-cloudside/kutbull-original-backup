__author__ = 'Tanuja'

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import dict_factory
#from dataglen.models import *
#from action.models import *
#import pandas as pd
from cassandra.cqlengine import connection
from cassandra.cqlengine import models
from cassandra.cqlengine.models import Model
from cassandra.cqlengine import columns

class ActionsStorageByStream(Model):
    source_key = columns.Text(partition_key=True, primary_key=True)
    acknowledgement = columns.Integer(partition_key=True, primary_key=True,default=0)
    stream_name = columns.Text()
    stream_value = columns.Text()
    insertion_time = columns.DateTime(partition_key=False, primary_key=True, clustering_order="DESC")
    comments = columns.Text()


class AddActionFields(object):

    def __init__(self):
        try:
            self.auth_provider = PlainTextAuthProvider(username='rkunnath', password='P@tt@nch3ry')
            self.cassandra_cluster = Cluster(['127.0.0.1'],
                                             auth_provider=self.auth_provider, protocol_version=3)

            self.cassandra_session = self.cassandra_cluster.connect()
            self.cassandra_session.row_factory = dict_factory
        except Exception as err:
            print("Exception while setting up cassandra connection: ", err)

    def get_cassandra_session(self):
        return self.cassandra_session

    def read_action(self):
        auth_provider = PlainTextAuthProvider(username='rkunnath', password='P@tt@nch3ry')
        cassandra_cluster = Cluster(['127.0.0.1'],
                                             auth_provider=self.auth_provider, protocol_version=3)

        cassandra_session = cassandra_cluster.connect()
        cassandra_session.row_factory = dict_factory
        connection.set_session(cassandra_session)
        models.DEFAULT_KEYSPACE = 'dataglen_data'

        action_len = ActionsStorageByStream.objects.filter(source_key='H7fcLT7fblILGPn',
                                                                          acknowledgement=0).count()
        print(action_len)

        '''
        template_name = 'RS_IOELabKit'
        # look for template
        template = Sensor.objects.get(isTemplate=True, name=template_name)

        sources_names = '2941001a45df,29410019b6e7'
        sources = sources_names.split(',')

        for source in sources:
            sensor = Sensor.objects.get(name=source)
            # copy action fields
            actionfields = ActionField.objects.filter(source=template)
            # copy all the fields
            for field in actionfields:
                existing_field_count = ActionField.objects.filter(source=sensor, name=field.name).count()
                if existing_field_count == 0:
                    new_field = ActionField()
                    new_field.source = sensor
                    new_field.name = field.name
                    new_field.streamDataType = field.streamDataType
                    new_field.streamPositionInCSV = field.streamPositionInCSV
                    new_field.streamDataUnit = field.streamDataUnit
                    new_field.streamDateTimeFormat = field.streamDateTimeFormat
                    # save the field
                    new_field.save()
        '''

if __name__ == "__main__":
    a = AddActionFields()
    a.read_action()


