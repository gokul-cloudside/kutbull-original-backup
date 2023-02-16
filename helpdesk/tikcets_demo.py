from helpdesk.models import Ticket, Queue
from solarrms.models import SolarPlant
from helpdesk.dg_functions import create_ticket
from django.utils import timezone
from datetime import timedelta

plant = SolarPlant.objects.get(slug="waneepsolar")
# create a ticket with an invalid event type
# try:
#     new_ticket = create_ticket(plant, 1, timezone.now(), "test", "test", "INVALID_EVENT_TYPE", "NO COMMENT")
# except Exception as exc:
#     print exc
# create a ticket with a valid event type
q = Queue.objects.filter(plant=plant)
for t in q[0].ticket.all():
    t.delete()


gateway_power_off = create_ticket(plant, 1, timezone.now(), "test", "test", "GATEWAY_POWER_OFF", "NO COMMENT")

# add a new ticket association
gateway_power_off.update_ticket_associations(['QFp1qKhEA1In7Qa'])
print gateway_power_off.get_devices_association_report(timezone.now() - timedelta(hours=5), True)

# add a new device
gateway_power_off.update_ticket_associations(['QFp1qKhEA1In7Qa', '4jHrBS7JkGD18FA'])
print gateway_power_off.get_devices_association_report(timezone.now() - timedelta(hours=5), True)

gateway_power_off.update_ticket_associations([])

# get ticket status
stats = gateway_power_off.get_ticket_stats(True)
print stats
# returns [{u'inverter2': {u'associations': 1, u'events': 0}}, 1, 0] [dictionary of each identifiers association and events, total_associations, total_events]

# create another ticket
gateway_disconnected = create_ticket(plant, 1, timezone.now(), "test", "test", "GATEWAY_DISCONNECTED", "NO COMMENT")
inverters_disconnected = create_ticket(plant, 1, timezone.now(), "test", "test", "INVERTERS_DISCONNECTED", "NO COMMENT")
gateway_disconnected.update_ticket_associations(['4jHrBS7JkGD18FA'])
print gateway_disconnected.get_ticket_stats(True)

# prepare plant report
print Ticket.get_plant_live_ops_summary(plant)
'''
{u'GATEWAY_DISCONNECTED': [{u'inverter2': {u'associations': 1, u'events': 0}},
  1,
  0],
 u'GATEWAY_POWER_OFF': [{u'Inverter1': {u'associations': 1, u'events': 0},
   u'inverter2': {u'associations': 1, u'events': 0}},
  2,
  0]}

  Each ticket types total association and events with details per identifier. List of identifiers can be retrieved by doing a .keys() on a dict.
  '''
# remove the first device
gateway_power_off.update_ticket_associations(['vmrRpdTutEGqH1z'])
print gateway_power_off.get_devices_association_report(timezone.now() - timedelta(hours=5), True)

# remove the second device
gateway_power_off.update_ticket_associations([])
print gateway_power_off.get_devices_association_report(timezone.now() - timedelta(hours=5), True)

inverters_alarms = create_ticket(plant, 1, timezone.now(), "test", "test", "INVERTERS_ALARMS", "NO COMMENT")
# pass alarm codes as strings - can be changed, wasn't sure the format an alarm code can take.
inverters_alarms.update_ticket_associations(['4jHrBS7JkGD18FA'], alarms_dict={'4jHrBS7JkGD18FA':{'alarm_codes': ['201'], 'solar_status': 23}})
inverters_alarms.get_devices_association_report(timezone.now() - timedelta(hours=5), True)
# there's an active alarm with alarm_code 201 and device_status 23
inverters_alarms.update_ticket_associations(['4jHrBS7JkGD18FA'], alarms_dict={'4jHrBS7JkGD18FA':{'alarm_codes': ['202'], 'solar_status': 23}})
# there's an active alarm with alarm_code 202 and device_status 23 and
# inactive alarm with alarm_code 201 and device_status 23
inverters_alarms.update_ticket_associations(['4jHrBS7JkGD18FA'], alarms_dict={'4jHrBS7JkGD18FA':{'alarm_codes': [], 'solar_status': 23}})
# all alarms are inactive now

# RUN 2
inverters_alarms = create_ticket(plant, 1, timezone.now(), "test", "test", "INVERTERS_ALARMS", "NO COMMENT")
inverters_alarms.update_ticket_associations(['4jHrBS7JkGD18FA'], alarms_dict={'4jHrBS7JkGD18FA':{'alarm_codes': [], 'solar_status': 23}})
inverters_alarms.get_devices_association_report(timezone.now() - timedelta(hours=5), True)
# there won't be any alarms
# there will be alarms now
inverters_alarms.update_ticket_associations(['4jHrBS7JkGD18FA'],
                                            alarms_dict={'4jHrBS7JkGD18FA':{'alarm_codes': [], 'solar_status': 23}},
                                            alarms_disabled=True)
inverters_alarms.get_devices_association_report(timezone.now() - timedelta(hours=5), True)
# new alarms
inverters_alarms.update_ticket_associations(['4jHrBS7JkGD18FA'],
                                            alarms_dict={'4jHrBS7JkGD18FA':{'alarm_codes': [], 'solar_status': 22}},
                                            alarms_disabled=True)
inverters_alarms.get_devices_association_report(timezone.now() - timedelta(hours=5), True)
# what will happen now - association will remain True but no alarms will be
# created - hence status code will not be around
inverters_alarms.update_ticket_associations(['4jHrBS7JkGD18FA'],
                                            alarms_dict={'4jHrBS7JkGD18FA':{'alarm_codes': [], 'solar_status': 21}})
inverters_alarms.get_devices_association_report(timezone.now() - timedelta(hours=5), True)

inverters_alarms.get_ticket_stats(False)
inverters_alarms.get_ticket_stats(True)

device_underperforming = create_ticket(plant, 1, timezone.now(), "test",
                                       "test", "INVERTERS_UNDERPERFORMING", "NO COMMENT")
device_underperforming.update_ticket_associations(['4jHrBS7JkGD18FA'], performance_dict={'4jHrBS7JkGD18FA':[{'st': timezone.now(), 'et': timezone.now(), 'identifier': 'STREAM_NAME'}]})
device_underperforming.get_ticket_stats(False)
print device_underperforming.get_devices_association_report(timezone.now() - timedelta(hours=5), True)

mppt_underperforming = create_ticket(plant, 1, timezone.now(), "test", "test", "MPPT_UNDERPERFORMING", "NO COMMENT")
mppt_underperforming.update_ticket_associations(['4jHrBS7JkGD18FA'], performance_dict={'4jHrBS7JkGD18FA':[{'st': timezone.now(), 'et': timezone.now(), 'identifier': 'STREAM_NAME', 'mean_power': 504.2, 'actual_power': 500.9}]})
mppt_underperforming.get_ticket_stats(False)
print mppt_underperforming.get_devices_association_report(timezone.now() - timedelta(hours=5), True)
