from solarrms.models import SolarPlant, IndependentInverter
from solarrms.settings import INVERTERS_COMPARISON_STANDARD_DEVIATION, INVERTERS_COMPARISON_PERCENTAGE
from solarrms.solarutils import get_minutes_aggregated_energy
from django.utils import timezone
import datetime
import numpy as np
from helpdesk.dg_functions import create_ticket
from helpdesk.models import Ticket, Queue
from solarrms.cron_new_tickets import close_ticket
import pytz
from dashboards.models import DataglenClient

SKIP_CLIENTS = ['renew-power','jackson','harsha-abakus-solar','hero-future-energies', 'cleanmax-solar', 'edp']

COMPARISON_METHOD = 'PERCENT'

def create_inverters_under_performing_ticket(plant, priority, due_date):
    try:
        ticket_name = "Inverters under performing event occurred at : " + str(plant.location)
        ticket_description = "Inverters are under performing at : " + str(plant.location)
        event_type = "INVERTERS_UNDERPERFORMING"
        open_comment = "Tickets created automatically based on the low generation of inverters."
        new_inverters_under_performing_ticket = create_ticket(plant=plant, priority=priority, due_date=due_date, ticket_name=ticket_name,
                                                    ticket_description=ticket_description, open_comment=open_comment, event_type=event_type)
        return new_inverters_under_performing_ticket
    except Exception as exception:
        print("Error in creating ticket for inverters under performing : " + str(exception))


# This cronjon will run hourly
def compare_inverters_generation():
    try:
        current_time = timezone.now()
        end_time = current_time
        start_time = end_time - datetime.timedelta(hours=1)
        #client = DataglenClient.objects.get(slug='hero-future-energies')
        #plants = SolarPlant.objects.filter(groupClient=client)
        plants = SolarPlant.objects.all()
        for plant in plants:
            if str(plant.groupClient.slug) in SKIP_CLIENTS:
                print "inside skip"
                pass
            else:
                print ("Inverters comparision for plant : " + str(plant.slug))
                try:
                    queue = Queue.objects.get(plant=plant)
                except Exception as exception:
                    print ("Queue does not exist for plant : " + str(plant.slug))
                    continue
                under_performing_inverters_dict = {}
                under_performing_inverters = []
                inverters = plant.independent_inverter_units.all()
                normalized_inverters_energy_list = []
                normalized_inverters_energy_dict = {}

                # get the energy values in past 6 hours
                inverters_energy_values = get_minutes_aggregated_energy(start_time, end_time, plant, 'MINUTE', 60, True, False)
                for inverter in inverters:
                    try:
                        inverter_energy = inverters_energy_values[inverter.name][len(inverters_energy_values[inverter.name])-1]['energy']
                    except Exception as exception:
                        print str(exception)
                        inverter_energy = 0.0

                    # TODO: Later on this normalization should be done based on the module capacity and number of mudules per inverter
                    # get the normalized energy values for each inverter
                    try:
                        normalized_inverters_energy = float(inverter_energy)/float(inverter.total_capacity) if inverter.total_capacity else float(inverter_energy)/float(inverter.actual_capacity)
                    except:
                        normalized_inverters_energy = float(inverter_energy)/(float(plant.capacity)/len(inverters))

                    normalized_inverters_energy_list.append(normalized_inverters_energy)
                    normalized_inverters_energy_dict[str(inverter.name)] = normalized_inverters_energy

                # get the mean of normalized energy values
                normalized_energy_values_mean = np.mean(normalized_inverters_energy_list)

                # get the standard deviation of normalized energy values
                normalized_energy_values_standard_deviation = np.std(normalized_inverters_energy_list)
                for inverter in inverters:
                    under_performing_dict_temp = {}
                    under_performing_list_temp = []

                    if COMPARISON_METHOD == 'STANDARD_DEVIATION':
                        if normalized_inverters_energy_dict[str(inverter.name)] < normalized_energy_values_mean - INVERTERS_COMPARISON_STANDARD_DEVIATION*normalized_energy_values_standard_deviation:
                            under_performing_inverters.append(str(inverter.sourceKey))
                            inverter_capacity = float(inverter.total_capacity) if inverter.total_capacity else float(inverter_energy)/float(inverter.actual_capacity)
                            under_performing_dict_temp['st'] = start_time
                            under_performing_dict_temp['et'] = end_time
                            under_performing_dict_temp['identifier'] = str(inverter.name)
                            under_performing_dict_temp['actual_energy'] = float(normalized_inverters_energy_dict[str(inverter.name)]) * float(inverter_capacity)
                            under_performing_dict_temp['mean_energy'] = float(normalized_energy_values_mean) * float(inverter_capacity)
                            under_performing_dict_temp['delta_energy'] = float(under_performing_dict_temp['mean_energy']) - float(under_performing_dict_temp['actual_energy'])
                            under_performing_list_temp.append(under_performing_dict_temp)
                            under_performing_inverters_dict[str(inverter.sourceKey)] = under_performing_list_temp

                    elif COMPARISON_METHOD == 'PERCENT':
                        if (100.0 - (normalized_inverters_energy_dict[str(inverter.name)]/normalized_energy_values_mean)*100.0) > INVERTERS_COMPARISON_PERCENTAGE:
                            under_performing_inverters.append(str(inverter.sourceKey))
                            inverter_capacity = float(inverter.total_capacity) if inverter.total_capacity else float(inverter_energy)/float(inverter.actual_capacity)
                            under_performing_dict_temp['st'] = start_time
                            under_performing_dict_temp['et'] = end_time
                            under_performing_dict_temp['identifier'] = str(inverter.name)
                            under_performing_dict_temp['actual_energy'] = float(normalized_inverters_energy_dict[str(inverter.name)]) * float(inverter_capacity)
                            under_performing_dict_temp['mean_energy'] = float(normalized_energy_values_mean) * float(inverter_capacity)
                            under_performing_dict_temp['delta_energy'] = float(under_performing_dict_temp['mean_energy']) - float(under_performing_dict_temp['actual_energy'])
                            under_performing_list_temp.append(under_performing_dict_temp)
                            under_performing_inverters_dict[str(inverter.sourceKey)] = under_performing_list_temp

                    else:
                        pass

                print under_performing_inverters_dict
                print under_performing_inverters

                # check if an open ticket exists for Inverters Under performing
                inverters_underperforming_ticket = Ticket.objects.filter(queue=queue, event_type='INVERTERS_UNDERPERFORMING', status=1)
                if len(inverters_underperforming_ticket)>0:
                    # Ticket exists, update the association
                    inverters_underperforming_ticket[0].update_ticket_associations(under_performing_inverters, performance_dict=under_performing_inverters_dict)
                    if len(under_performing_inverters_dict)==0:
                        # Ticket exist, but the problem does not exist now, close the ticket
                        close_ticket(plant=plant, ticket=inverters_underperforming_ticket[0], request_arrival_time=timezone.now())
                elif len(inverters_underperforming_ticket) == 0 and len(under_performing_inverters_dict)>0:
                    # Ticket does not exist,problem has occurred just now, create a new ticket.
                    new_inverters_underperforming_ticket = create_inverters_under_performing_ticket(plant, 1, None)
                    new_inverters_underperforming_ticket.update_ticket_associations(under_performing_inverters, performance_dict=under_performing_inverters_dict)
                else:
                    pass
    except Exception as exception:
        print str(exception)


def compare_inverters_generation_edp():
    try:
        current_time = timezone.now()
        end_time = current_time
        plant_list = ['faro','santarem','seia','castelo']
        for plant_name in plant_list:
            plant = SolarPlant.objects.get(slug=plant_name)
            try:
                end_time = end_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
                end_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
            except:
                end_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            start_time = end_time - datetime.timedelta(days=1)
            print ("Inverters comparision for plant : " + str(plant.slug))
            try:
                queue = Queue.objects.get(plant=plant)
            except Exception as exception:
                print ("Queue does not exist for plant : " + str(plant.slug))
                continue
            under_performing_inverters_dict = {}
            under_performing_inverters = []
            inverters = plant.independent_inverter_units.all()
            normalized_inverters_energy_list = []
            normalized_inverters_energy_dict = {}

            # get the energy values in past 6 hours
            inverters_energy_values = get_minutes_aggregated_energy(start_time, end_time, plant, 'DAY', 1, True, False)
            for inverter in inverters:
                try:
                    inverter_energy = inverters_energy_values[inverter.name][len(inverters_energy_values[inverter.name])-1]['energy']
                except Exception as exception:
                    print str(exception)
                    inverter_energy = 0.0

                # TODO: Later on this normalization should be done based on the module capacity and number of mudules per inverter
                # get the normalized energy values for each inverter
                try:
                    normalized_inverters_energy = float(inverter_energy)/float(inverter.total_capacity) if inverter.total_capacity else float(inverter_energy)/float(inverter.actual_capacity)
                except:
                    normalized_inverters_energy = float(inverter_energy)/(float(plant.capacity)/len(inverters))

                normalized_inverters_energy_list.append(normalized_inverters_energy)
                normalized_inverters_energy_dict[str(inverter.name)] = normalized_inverters_energy

            # get the mean of normalized energy values
            normalized_energy_values_mean = np.mean(normalized_inverters_energy_list)

            # get the standard deviation of normalized energy values
            normalized_energy_values_standard_deviation = np.std(normalized_inverters_energy_list)
            for inverter in inverters:
                under_performing_dict_temp = {}
                under_performing_list_temp = []

                if COMPARISON_METHOD == 'STANDARD_DEVIATION':
                    if normalized_inverters_energy_dict[str(inverter.name)] < normalized_energy_values_mean - INVERTERS_COMPARISON_STANDARD_DEVIATION*normalized_energy_values_standard_deviation:
                        under_performing_inverters.append(str(inverter.sourceKey))
                        inverter_capacity = float(inverter.total_capacity) if inverter.total_capacity else float(inverter_energy)/float(inverter.actual_capacity)
                        under_performing_dict_temp['st'] = start_time
                        under_performing_dict_temp['et'] = end_time
                        under_performing_dict_temp['identifier'] = str(inverter.name)
                        under_performing_dict_temp['actual_energy'] = float(normalized_inverters_energy_dict[str(inverter.name)]) * float(inverter_capacity)
                        under_performing_dict_temp['mean_energy'] = float(normalized_energy_values_mean) * float(inverter_capacity)
                        under_performing_dict_temp['delta_energy'] = float(under_performing_dict_temp['mean_energy']) - float(under_performing_dict_temp['actual_energy'])
                        under_performing_list_temp.append(under_performing_dict_temp)
                        under_performing_inverters_dict[str(inverter.sourceKey)] = under_performing_list_temp

                elif COMPARISON_METHOD == 'PERCENT':
                    if (100.0 - (normalized_inverters_energy_dict[str(inverter.name)]/normalized_energy_values_mean)*100.0) > INVERTERS_COMPARISON_PERCENTAGE:
                        under_performing_inverters.append(str(inverter.sourceKey))
                        inverter_capacity = float(inverter.total_capacity) if inverter.total_capacity else float(inverter_energy)/float(inverter.actual_capacity)
                        under_performing_dict_temp['st'] = start_time
                        under_performing_dict_temp['et'] = end_time
                        under_performing_dict_temp['identifier'] = str(inverter.name)
                        under_performing_dict_temp['actual_energy'] = float(normalized_inverters_energy_dict[str(inverter.name)]) * float(inverter_capacity)
                        under_performing_dict_temp['mean_energy'] = float(normalized_energy_values_mean) * float(inverter_capacity)
                        under_performing_dict_temp['delta_energy'] = float(under_performing_dict_temp['mean_energy']) - float(under_performing_dict_temp['actual_energy'])
                        under_performing_list_temp.append(under_performing_dict_temp)
                        under_performing_inverters_dict[str(inverter.sourceKey)] = under_performing_list_temp

                else:
                    pass

            print under_performing_inverters_dict
            print under_performing_inverters

            # check if an open ticket exists for Inverters Under performing
            inverters_underperforming_ticket = Ticket.objects.filter(queue=queue, event_type='INVERTERS_UNDERPERFORMING', status=1)
            if len(inverters_underperforming_ticket)>0:
                # Ticket exists, update the association
                inverters_underperforming_ticket[0].update_ticket_associations(under_performing_inverters, performance_dict=under_performing_inverters_dict)
                if len(under_performing_inverters_dict)==0:
                    # Ticket exist, but the problem does not exist now, close the ticket
                    close_ticket(plant=plant, ticket=inverters_underperforming_ticket[0], request_arrival_time=timezone.now())
            elif len(inverters_underperforming_ticket) == 0 and len(under_performing_inverters_dict)>0:
                # Ticket does not exist,problem has occurred just now, create a new ticket.
                new_inverters_underperforming_ticket = create_inverters_under_performing_ticket(plant, 1, None)
                new_inverters_underperforming_ticket.update_ticket_associations(under_performing_inverters, performance_dict=under_performing_inverters_dict)
            else:
                pass
    except Exception as exception:
        print str(exception)