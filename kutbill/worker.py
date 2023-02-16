from __future__ import absolute_import
from cassandra.auth import PlainTextAuthProvider
from cassandra.cqlengine import connection
from cassandra.cqlengine.connection import (cluster as cql_cluster)
from cassandra.cqlengine.connection import (session as cql_session)
from celery.signals import *
from celery.utils.log import get_task_logger
from django.conf import settings

# if the log file is NOT specified in the config file, it will HANG.
# grab the logger for the Celery app
logger = get_task_logger(__name__)

CASSANDRA_HOSTS = []
CASSANDRA_KEYSPACE = ''
CASSANDRA_USER = ''
CASSANDRA_PASSWORD = ''

@worker_process_init.connect
def init_worker(**kwargs):
    logger.debug("initializing worker")
    init_db()


def init_db():
    global CASSANDRA_HOSTS, CASSANDRA_KEYSPACE
    global CASSANDRA_USER, CASSANDRA_PASSWORD
    cassandra_info = settings.DATABASES['cassandra']

    CASSANDRA_HOSTS = settings.HOST_IP
    CASSANDRA_USER = cassandra_info['USER']
    CASSANDRA_PASSWORD = cassandra_info['PASSWORD']
    CASSANDRA_KEYSPACE = cassandra_info['NAME']

    logger.debug("host: " + str(CASSANDRA_HOSTS))
    logger.debug("keyspace: " + CASSANDRA_KEYSPACE)
    logger.debug("user: " + CASSANDRA_USER)
    logger.debug("password: " + CASSANDRA_PASSWORD)

    # TODO - we must not be storing passwords in plain text format like this
    ap = PlainTextAuthProvider(username=CASSANDRA_USER, password=CASSANDRA_PASSWORD)

    if cql_cluster is not None:
        cql_cluster.shutdown()
    if cql_session is not None:
        cql_session.shutdown()

    connection.setup(CASSANDRA_HOSTS, CASSANDRA_KEYSPACE, auth_provider=ap)
    logger.debug("connected to the database")

@worker_shutdown.connect
def finalize_worker(**kwargs):
    logger.info("shutting the worker down")
    if cql_cluster is not None:
        cql_cluster.shutdown()

    if cql_session is not None:
        cql_session.shutdown()
