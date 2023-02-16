from solarrms.models import SolarPlant
from helpdesk.models import Ticket, TicketAssociation, SLADefinition
from django.utils import timezone
from helpdesk.dg_functions import update_ticket
from django.contrib.auth.models import User
import datetime
import pytz

default_sla_l1 = {1: 15, 2: 60, 3: 120, 4: 180, 5: 360}
default_sla_l2 = {1: 90, 2: 180, 3: 300, 4: 450, 5: 560}
default_sla_l3 = {1: 300, 2: 400, 3: 600, 4:800, 5: 9000}

# TODO: Add code to send emails whenever the ticket is getting escalated

def escalate_ticket():
    try:
        plants = SolarPlant.objects.all()
        for plant in plants:
            try:
                current_time = timezone.now()
                current_time = current_time.astimezone(pytz.timezone(plant.metadata.plantmetasource.dataTimezone))
            except Exception as exc:
                current_time = timezone.now()
            print("Ticket escalation cronjob started for plant: " + str(plant.slug) + " at " + str(current_time))
            queues = plant.queues.all()
            if len(queues)>0:
                queue = queues[0]
            tickets = Ticket.objects.filter(queue=queue, status__in=[Ticket.OPEN_STATUS, Ticket.REOPENED_STATUS])
            for ticket in tickets:
                try:
                    if int(ticket.escalation_level) == 3:
                        pass
                    else:
                        ticket_slas = SLADefinition.objects.filter(queue=queue, priority=ticket.priority, level=int(ticket.escalation_level)+1)
                        if len(ticket_slas)>0:
                            ticket_sla = ticket_slas[0].SLA
                            try:
                                user = User.objects.get(email=ticket_slas[0].escalate_to_email)
                            except:
                                user = plant.owner.organization_user.user
                        else:
                            if int(ticket.escalation_level) == 0:
                               ticket_sla =  default_sla_l1[int(ticket.priority)]
                            elif int(ticket.escalation_level) == 1:
                               ticket_sla =  default_sla_l2[int(ticket.priority)]
                            elif int(ticket.escalation_level) == 2:
                               ticket_sla =  default_sla_l3[int(ticket.priority)]
                            else:
                                pass
                            user = plant.owner.organization_user.user
                        time_difference = current_time - ticket.created
                        time_difference_minutes = time_difference.total_seconds()/60
                        if time_difference_minutes > ticket_sla:
                            #escalate the ticket to a higher level
                            update_ticket(plant=plant, ticket_id=ticket.id, followup_user=user,
                                          comment="Ticket got escalated to level "+str(int(ticket.escalation_level)+1),
                                          new_status=ticket.status, title = str(ticket.title) + " - Level-" +
                                                                            str(int(ticket.escalation_level)+1) + " Escalation " + " at " + str(current_time),
                                          due_date = current_time + datetime.timedelta(minutes=ticket_sla),escalation_level = int(ticket.escalation_level)+1)
                except Exception as exception:
                    print(str(exception))
                    continue
    except Exception as exception:
        print ("Error in escalating the ticket to a higher level: " + str(exception))