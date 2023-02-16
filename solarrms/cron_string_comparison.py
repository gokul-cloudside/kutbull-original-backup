from solarrms.models import SolarPlant, SolarField, IndependentInverter, MPPT
from dataglen.models import ValidDataStorageByStream
from django.utils import timezone
import datetime
import numpy as np
from helpdesk.dg_functions import create_ticket
from solarrms.settings import AJBS_COMPARISON_STANDARD_DEVIATION, AJBS_COMPARISON_PERCENTAGE
from helpdesk.models import Ticket, Queue
from solarrms.cron_new_tickets import close_ticket

COMPARISON_METHOD = 'PERCENT'

SKIP_CLIENTS = ['renew-power','jackson','harsha-abakus-solar','hero-future-energies', 'cleanmax-solar']

def create_strings_under_performing_ticket(plant, priority, due_date):
    try:
        ticket_name = "AJBs under performing event occurred at : " + str(plant.location)
        ticket_description = "AJBs are under performing at : " + str(plant.location)
        event_type = "AJB_UNDERPERFORMING"
        open_comment = "Tickets created automatically based on the low current values of AJBs."
        new_ajbs_under_performing_ticket = create_ticket(plant=plant, priority=priority, due_date=due_date, ticket_name=ticket_name,
                                                         ticket_description=ticket_description, open_comment=open_comment, event_type=event_type)
        return new_ajbs_under_performing_ticket
    except Exception as exception:
        print("Error in creating ticket for ajbs under performing : " + str(exception))


# This cronjob will run hourly
def compare_strings():
    try:
        current_time = timezone.now()
        end_time = current_time
        start_time = end_time - datetime.timedelta(hours=1)
        plants = SolarPlant.objects.all()
        #plants = SolarPlant.objects.filter(slug='yerangiligi')
        for plant in plants:
            if str(plant.groupClient.slug) in SKIP_CLIENTS:
                print "inside skip"
                pass
            else:
                print ("String comparision for plant : " + str(plant.slug))
                try:
                    queue = Queue.objects.get(plant=plant)
                except Exception as exception:
                    print ("Queue does not exist for plant : " + str(plant.slug))
                    continue

                under_performing_ajb_list = []
                final_under_performing_ajb_dict = {}
                ajbs = plant.ajb_units.all()
                for ajb in ajbs:
                    under_performing_string_dict_list = []
                    mean_current_values_list = []
                    mean_current_values_dict = {}
                    ajb_streams = []
                    active_streams = ajb.fields.all().filter(isActive=True)
                    for stream in active_streams:
                        if str(stream.name).startswith("S"):
                            ajb_streams.append(stream.name)

                    for stream in ajb_streams:
                        string_current_values = []
                        string_values = ValidDataStorageByStream.objects.filter(source_key=ajb.sourceKey,
                                                                                stream_name=stream,
                                                                                timestamp_in_data__gte=start_time,
                                                                                timestamp_in_data__lte=end_time)
                        for value in string_values:
                            string_current_values.append(float(value.stream_value))
                        mean_current_value = np.mean(string_current_values)

                        if not np.isnan(mean_current_value):
                            mean_current_values_list.append(mean_current_value)
                            mean_current_values_dict[str(stream)] = mean_current_value

                    mean_of_mean_current = np.mean(mean_current_values_list)
                    std_deviation_of_mean = np.std(mean_current_values_list)

                    for key in mean_current_values_dict.keys():
                        under_performing_string_temp = {}

                        if COMPARISON_METHOD == 'STANDARD_DEVIATION':
                            if mean_current_values_dict[key] < mean_of_mean_current - AJBS_COMPARISON_STANDARD_DEVIATION*std_deviation_of_mean:
                                under_performing_string_temp['st'] = start_time
                                under_performing_string_temp['et'] = end_time
                                under_performing_string_temp['identifier'] = key
                                under_performing_string_temp['actual_current'] = mean_current_values_dict[key]
                                under_performing_string_temp['mean_current'] = mean_of_mean_current
                                under_performing_string_temp['delta_current'] = float(mean_of_mean_current) - float(mean_current_values_dict[key])
                                under_performing_string_dict_list.append(under_performing_string_temp)
                                under_performing_ajb_list.append(ajb.sourceKey)

                        elif COMPARISON_METHOD == 'PERCENT':
                            if (100.0 - (mean_current_values_dict[key]/mean_of_mean_current)*100.0) > AJBS_COMPARISON_PERCENTAGE:
                                under_performing_string_temp['st'] = start_time
                                under_performing_string_temp['et'] = end_time
                                under_performing_string_temp['identifier'] = key
                                under_performing_string_temp['actual_current'] = mean_current_values_dict[key]
                                under_performing_string_temp['mean_current'] = mean_of_mean_current
                                under_performing_string_temp['delta_current'] = float(mean_of_mean_current) - float(mean_current_values_dict[key])
                                under_performing_string_dict_list.append(under_performing_string_temp)
                                under_performing_ajb_list.append(ajb.sourceKey)

                        else:
                            pass

                    if len(under_performing_string_dict_list) > 0:
                        final_under_performing_ajb_dict[str(ajb.sourceKey)] = under_performing_string_dict_list
                final_under_performing_ajb_list = list(set(under_performing_ajb_list))

                # check if an open ticket exists for AJB under performing
                ajbs_underperforming_ticket = Ticket.objects.filter(queue=queue, event_type='AJB_UNDERPERFORMING', status=1)

                if len(ajbs_underperforming_ticket)>0:
                    # Tickets exists, update the association
                    ajbs_underperforming_ticket[0].update_ticket_associations(final_under_performing_ajb_list, performance_dict=final_under_performing_ajb_dict)
                    if len(final_under_performing_ajb_dict) == 0:
                        # Ticket exists, but the problem does not exist now, close the ticket
                        close_ticket(plant=plant, ticket=ajbs_underperforming_ticket[0], request_arrival_time=timezone.now())
                elif len(ajbs_underperforming_ticket) == 0 and len(final_under_performing_ajb_dict)>0:
                    # Ticket does not exist,problem has occurred just now, create a new ticket.
                    new_ajbs_underperforming_ticket = create_strings_under_performing_ticket(plant, 1, None)
                    new_ajbs_underperforming_ticket.update_ticket_associations(final_under_performing_ajb_list, performance_dict=final_under_performing_ajb_dict)
                else:
                    pass
    except Exception as exception:
        print str(exception)