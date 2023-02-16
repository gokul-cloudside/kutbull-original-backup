from monitoring.models import SourceMonitoring
import sys, logging, traceback
from dataglen.models import Sensor
import traceback

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# write monitoring errors
def write_monitoring_errors(func_name):
    logger.debug("%s,%s,%s",
                 func_name, traceback.format_exc(),
                 repr(traceback.extract_stack()))


# Create your views here.
def write_a_data_write_ttl(user_id, source_key, source_timeout, valid, request_arrival_time):
    try:
        SourceMonitoring.ttl(source_timeout).create(source_key=source_key,
                                                    valid_entry=valid,
                                                    ts=request_arrival_time)
    except:
        write_monitoring_errors(sys._getframe().f_code.co_name)


def get_user_data_monitoring_status(sensors):
    try:
        all_activated_sources = sensors.filter(isTemplate=False, isActive=True,
                                               isMonitored=True).values_list('sourceKey', 'name')
        all_activated_sources = [value[0] for value in all_activated_sources]

        all_deactivated_sources = sensors.filter(isTemplate=False, isActive=False,
                                                 isMonitored=True).values_list('sourceKey', 'name')
        all_deactivated_sources = [value[0] for value in all_deactivated_sources]

        active_alive_valid = SourceMonitoring.objects.filter(source_key__in=all_activated_sources,
                                                             valid_entry=True).values_list('source_key')
        active_alive_valid = [value[0] for value in active_alive_valid]

        active_alive_invalid = SourceMonitoring.objects.filter(source_key__in=all_activated_sources,
                                                               valid_entry=False).values_list('source_key')
        active_alive_invalid = [value[0] for value in active_alive_invalid]
        active_dead = list(set(all_activated_sources) - set(active_alive_valid) - set(active_alive_invalid))

        deactivated_alive = SourceMonitoring.objects.filter(source_key__in=all_deactivated_sources).values_list('source_key')
        deactivated_alive = [value[0] for value in deactivated_alive]
        deactivated_dead = list(set(all_deactivated_sources) - set(deactivated_alive))

        unmonitored_sources = sensors.filter(isMonitored=False).values_list('sourceKey', 'name')
        return active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored_sources
    except:
        write_monitoring_errors(sys._getframe().f_code.co_name)
        return None