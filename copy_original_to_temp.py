import sys
import os
import django
os.environ["DJANGO_SETTINGS_MODULE"] = "kutbill.settings"
django.setup()

from events.models import EventsByTime, EventsByTimeTemp, EventsByError, EventsByErrorTemp

try:
	events_time = EventsByTime.objects.all().limit(134970)
	for event_time in events_time:
		event_time_temp = EventsByTimeTemp.objects.create(identifier=event_time.identifier,
														  insertion_time=event_time.insertion_time,
														  event_name=event_time.event_name,
														  event_time=event_time.event_time)
		event_time_temp.save()
	print("EventsByTime table entries copied")
except Exception as exception:
	print(str(exception))


try:
	events_errors = EventsByError.objects.all().limit(134970)
	for event_error in events_errors:
		event_error_temp = EventsByErrorTemp.objects.create(identifier=event_error.identifier,
														  	insertion_time=event_error.insertion_time,
														  	event_name=event_error.event_name,
														  	event_time=event_error.event_time)
		event_error_temp.save()
	print("EventsByError table entries copied")
except Exception as exception:
	print(str(exception))