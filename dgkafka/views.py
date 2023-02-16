from django.shortcuts import render
#from kafka.errors import KafkaError
from confluent_kafka import Producer
from kutbill.settings import KAFKA_HOSTS
from .settings import kafka_producers
import json
import logging
import datetime

logger = logging.getLogger('dataglen.views')
logger.setLevel(logging.DEBUG)

def date_handler(obj):
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        return obj

class MyEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            #return int(mktime(obj.timetuple()))
            return obj.isoformat()

        return json.JSONEncoder.default(self, obj)



# Create your views here.
class KafkaUtil():
    producer = None
    broker_list = None
    doSYNC = None

    def __init__(self,broker_list, sync):
        '''
        Constructor for Kafka Util class
        :param broker_list:  list of broker with retention period of 24 hours
        :param sync:  if set to True then the producer will be a synchronous producer else asynchronous producer
        '''
        # Producer configuration
        self.broker_list = broker_list
        self.__get_connection()

    def __get_connection(self):
        #conf = {'bootstrap.servers': 'localhost:9092' }
        try:
            #self.producer = Producer(**conf)
            self.producer = Producer({'bootstrap.servers': self.broker_list, 'api.version.request' : True,
                                      'log.connection.close': False})
        except Exception as ex:
            logger.debug("%% Exception while creating kafka confluent producer client %s" % str(ex))


    # Optional per-message delivery callback (triggered by poll() or flush())
    # when a message has been successfully delivered or permanently
    # failed delivery (after retries).
    def delivery_callback(self,error, msg):
        if error:
            logger.debug('%% Message failed delivery: %s\n' % error)
        else:
            logger.debug('%% Message delivered to %s [%d]\n' % \
                             (msg.topic(), msg.partition()))

    def send_message(self, topic, key, json_msg, sync):
        '''
        Sends the JSONified keyed message to the kafka topic
        :param topic:  name of kafka topic to which the data has to sent
        :param key: key to be used by the default partitioner
        :param json_msg: JSON message
        :return: None
        '''
        logger.debug('Sending %s:%s' % (topic, key))
        try:
                logger.debug('producer %s' %str(self.producer))                                                                                                                                                                                                                 
                self.producer.produce(topic, key=key, value=json.dumps(json_msg,cls = MyEncoder), callback=self.delivery_callback)
                self.producer.poll(0)
        except Exception as ex:
            logger.debug('%% Exception in sending message to kafka: %s\n' % str(ex))


def create_kafka_producers():
    try:
        global kafka_producers
        kafka_producers = []
        for i in range(len(KAFKA_HOSTS)):
            kafka_producers.append(KafkaUtil(broker_list=KAFKA_HOSTS[i], sync=True))
    except Exception as ex:
        logger.debug("error while creating kafka producer %s" % str(ex))
    return kafka_producers


