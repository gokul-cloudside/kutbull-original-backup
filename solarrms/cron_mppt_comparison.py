from solarrms.models import SolarPlant, SolarField, IndependentInverter, MPPT
from dataglen.models import ValidDataStorageByStream
from django.utils import timezone
import datetime
import numpy as np
from helpdesk.dg_functions import create_ticket
from solarrms.settings import MPPTS_COMPARISON_STANDARD_DEVIATION, MPPTS_COMPARISON_PERCENTAGE
from helpdesk.models import Ticket, Queue
from solarrms.cron_new_tickets import close_ticket

COMPARISON_METHOD = 'PERCENT'

SKIP_CLIENTS = ['renew-power','jackson','harsha-abakus-solar','hero-future-energies', 'cleanmax-solar']

def create_mppts_under_performing_ticket(plant, priority, due_date):
    try:
        ticket_name = "MPPTs under performing event occurred at : " + str(plant.location)
        ticket_description = "MPPTs are under performing at : " + str(plant.location)
        event_type = "MPPT_UNDERPERFORMING"
        open_comment = "Tickets created automatically based on the low power values of MPPTs."
        new_mppts_under_performing_ticket = create_ticket(plant=plant, priority=priority, due_date=due_date, ticket_name=ticket_name,
                                                    ticket_description=ticket_description, open_comment=open_comment, event_type=event_type)
        return new_mppts_under_performing_ticket
    except Exception as exception:
        print("Error in creating ticket for inverters under performing : " + str(exception))


# This cronjob will run hourly
def compare_mppts():
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
                print ("MPPT comparision for plant : " + str(plant.slug))
                try:
                    queue = Queue.objects.get(plant=plant)
                except Exception as exception:
                    print ("Queue does not exist for plant : " + str(plant.slug))
                    continue
                under_performing_mppt_inverters_list = []
                final_under_performing_mppt_inverters_dict = {}
                inverters = plant.independent_inverter_units.all()

                for inverter in inverters:
                    normalized_mppt_values_dict = {}
                    normalized_mppt_values_list = []
                    under_performing_mppt_inverters_dict_list = []
                    no_of_mppts = inverter.number_of_mppts
                    mppt_dc_current_streams = []
                    if no_of_mppts > 0:
                        mppts = inverter.mppt_units.all()
                        for i in range(no_of_mppts):
                            mppt_dc_current_streams.append('MPPT'+str(i+1)+"_DC_CURRENT")
                        for count in range(len(mppt_dc_current_streams)):
                            mppt_current_values = []
                            mppt_values = ValidDataStorageByStream.objects.filter(source_key=inverter.sourceKey,
                                                                                  stream_name=mppt_dc_current_streams[count],
                                                                                  timestamp_in_data__gte=start_time,
                                                                                  timestamp_in_data__lte=end_time)
                            mppt_last_name = 'MPPT'+str(count+1)
                            try:
                                mppt = MPPT.objects.get(plant=plant, independent_inverter=inverter, name__endswith=mppt_last_name)
                            except:
                                continue
                            #no_of_modules = int(mppt.strings_per_mppt) * int(mppt.modules_per_string)
                            no_of_modules = int(mppt.total_panels())
                            for value in mppt_values:
                                mppt_current_values.append(float(value.stream_value))
                            mean_mppt_current_value = np.mean(mppt_current_values)
                            normalized_mean_mppt_current_value = mean_mppt_current_value/no_of_modules
                            if not np.isnan(mean_mppt_current_value):
                                normalized_mppt_values_list.append(normalized_mean_mppt_current_value)
                                normalized_mppt_values_dict[str(mppt.name)] = normalized_mean_mppt_current_value
                        normalized_current_mean_of_all_mppts = np.mean(normalized_mppt_values_list)
                        normalized_current_std_deviation_of_all_mppts = np.std(normalized_mppt_values_list)

                        for key in normalized_mppt_values_dict.keys():
                            under_performing_dict_temp = {}

                            if COMPARISON_METHOD == 'STANDARD_DEVIATION':
                                if normalized_mppt_values_dict[key] < normalized_current_mean_of_all_mppts - MPPTS_COMPARISON_STANDARD_DEVIATION*normalized_current_std_deviation_of_all_mppts:
                                    under_performing_dict_temp['st'] = start_time
                                    under_performing_dict_temp['et'] = end_time
                                    under_performing_dict_temp['identifier'] = key
                                    under_performing_dict_temp['actual_power'] = normalized_mppt_values_dict[key]
                                    under_performing_dict_temp['mean_power'] = normalized_current_mean_of_all_mppts
                                    under_performing_dict_temp['delta_power'] = float(normalized_current_mean_of_all_mppts) - float(normalized_mppt_values_dict[key])
                                    under_performing_mppt_inverters_dict_list.append(under_performing_dict_temp)
                                    under_performing_mppt_inverters_list.append(inverter.sourceKey)

                            elif COMPARISON_METHOD == 'PERCENT':
                                if (100.0 - (normalized_mppt_values_dict[key]/normalized_current_mean_of_all_mppts)*100.0) > MPPTS_COMPARISON_PERCENTAGE:
                                    under_performing_dict_temp['st'] = start_time
                                    under_performing_dict_temp['et'] = end_time
                                    under_performing_dict_temp['identifier'] = key
                                    under_performing_dict_temp['actual_power'] = normalized_mppt_values_dict[key]
                                    under_performing_dict_temp['mean_power'] = normalized_current_mean_of_all_mppts
                                    under_performing_dict_temp['delta_power'] = float(normalized_current_mean_of_all_mppts) - float(normalized_mppt_values_dict[key])
                                    under_performing_mppt_inverters_dict_list.append(under_performing_dict_temp)
                                    under_performing_mppt_inverters_list.append(inverter.sourceKey)

                            else:
                                pass

                        if len(under_performing_mppt_inverters_dict_list) >0:
                            final_under_performing_mppt_inverters_dict[str(inverter.sourceKey)] = under_performing_mppt_inverters_dict_list

                # under_performing_mppt_inverters_list = ['ECNQxl5BlY9vUR0']
                # final_under_performing_mppt_inverters_dict = {'ECNQxl5BlY9vUR0': [{'actual_power': 13.58191489361702, 'st': datetime.datetime.now()-datetime.timedelta(hours=1), 'delta_power': 8.588297872340425, 'mean_power': 22.170212765957444, 'et': datetime.datetime.now(), 'identifier': 'CGO_Complex_Inverter_5_MPPT2'}]}

                under_performing_mppt_inverters_list = list(set(under_performing_mppt_inverters_list))
                # create ticket for the under performing mppts.
                # check if an open ticket exists for MPPTS under performing
                mppts_underperforming_ticket = Ticket.objects.filter(queue=queue, event_type='MPPT_UNDERPERFORMING', status=1)
                if len(mppts_underperforming_ticket)>0:
                    # Ticket exists, update the association
                    mppts_underperforming_ticket[0].update_ticket_associations(under_performing_mppt_inverters_list, performance_dict=final_under_performing_mppt_inverters_dict)
                    if len(final_under_performing_mppt_inverters_dict)==0:
                        # Ticket exists, but the problem does not exist now, close the ticket
                        close_ticket(plant=plant, ticket=mppts_underperforming_ticket[0], request_arrival_time=timezone.now())
                elif len(mppts_underperforming_ticket) == 0 and len(final_under_performing_mppt_inverters_dict)>0:
                    # Ticket does not exist,problem has occurred just now, create a new ticket.
                    new_mppts_underperforming_ticket = create_mppts_under_performing_ticket(plant, 1, None)
                    new_mppts_underperforming_ticket.update_ticket_associations(under_performing_mppt_inverters_list, performance_dict=final_under_performing_mppt_inverters_dict)
                else:
                    pass
    except Exception as exception:
        print str(exception)