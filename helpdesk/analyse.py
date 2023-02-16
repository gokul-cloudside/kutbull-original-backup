from celery import shared_task
import logging
from solarrms.solarutils import get_expected_energy, get_minutes_aggregated_energy
from solarrms.models import VirtualGateway, GatewaySource, IndependentInverter

logger = logging.getLogger('helpdesk.models')
logger.setLevel(logging.DEBUG)


'''
EVENT_TYPE = [('GATEWAY_POWER_OFF', 'GATEWAY_POWER_OFF'),
            ('GATEWAY_DISCONNECTED', 'GATEWAY_DISCONNECTED'),
            ('INVERTERS_DISCONNECTED', 'INVERTERS_DISCONNECTED'),
            ('AJBS_DISCONNECTED', 'AJBS_DISCONNECTED'),
            ('INVERTERS_NOT_GENERATING', 'INVERTERS_NOT_GENERATING'),
            ('INVERTERS_ALARMS', 'INVERTERS_ALARMS'),
            ('PANEL_CLEANING', 'PANEL_CLEANING'),
            ('INVERTERS_UNDERPERFORMING', 'INVERTERS_UNDERPERFORMING'),
            ('MPPT_UNDERPERFORMING', 'MPPT_UNDERPERFORMING'),
            ('AJB_UNDERPERFORMING', 'AJB_UNDERPERFORMING')]
'''

@shared_task
def analyse_ticket(ticket_id):
    try:
        from .models import TicketAssociation, Ticket
        logger.debug("analyse function for ticket id: " + str(ticket_id))
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            associations = ticket.associations.all()
        except:
            return
        expected_energy = 0.0
        actual_energy = 0.0
        for association in associations:
            if association.actual_energy:
                actual_energy+=association.actual_energy
            if association.expected_energy:
                expected_energy+=association.expected_energy
        ticket.actual_energy = actual_energy
        ticket.expected_energy = expected_energy
        ticket.save()
    except Exception as exc:
        logger.debug(str(exc))


@shared_task
def analyse_association(association_id):
    try:
        from .models import TicketAssociation, Ticket
        logger.debug("analyse function for association id: " + str(association_id))
        # get the ticket
        association = TicketAssociation.objects.get(id=association_id)
        if association.event_type == "GATEWAY_POWER_OFF" or association.event_type == 'GATEWAY_DISCONNECTED':
            # start time
            starttime = association.created
            endtime = association.closed

            # get the associated plant
            plant = association.ticket.queue.plant

            # get a list of inverters
            inverters = []
            if association.event_type == "GATEWAY_POWER_OFF":
                try:
                    vg = VirtualGateway.objects.get(sourceKey=association.identifier)
                except Exception as exc:
                    return
                if vg.solar_group:
                    inverters = vg.solar_group.groupIndependentInverters.all()
                else:
                    inverters = vg.plant.independent_inverter_units.all()
            elif association.event_type == 'GATEWAY_DISCONNECTED':
                try:
                    g = GatewaySource.objects.get(sourceKey=association.identifier)
                    inverters = g.plant.independent_inverter_units.all()
                except:
                    return

            expected_energy = 0.0
            for inverter in inverters:
                # get expected energy
                energy_info = get_expected_energy(inverter.sourceKey, 'SOURCE', starttime, endtime)
                if energy_info is not None and len(energy_info) == 3:
                    expected_energy += energy_info[0]
            association.expected_energy = expected_energy

            # get actual energy
            actual_energy_info = get_minutes_aggregated_energy(starttime, endtime,
                                                               plant, 'DAY', 1,
                                                               split=True, meter_energy=False)
            actual_energy = 0.0
            for inverter in inverters:
                try:
                    inverter_energy_info = actual_energy_info[inverter.name]
                except:
                    continue
                for item in inverter_energy_info:
                    actual_energy += float(item['energy'])
            association.actual_energy = actual_energy
            association.save()
            return
        elif association.event_type == "INVERTERS_DISCONNECTED" or association.event_type == 'INVERTERS_ALARMS':
            inverter = IndependentInverter.objects.get(sourceKey=association.identifier)
            # start time
            starttime = association.created
            endtime = association.closed

            # get the associated plant
            plant = association.ticket.queue.plant

            expected_energy = 0.0
            # get expected energy
            energy_info = get_expected_energy(inverter.sourceKey, 'SOURCE', starttime, endtime)
            if energy_info is not None and len(energy_info) == 3:
                expected_energy += energy_info[0]
            association.expected_energy = expected_energy

            # get actual energy
            actual_energy_info = get_minutes_aggregated_energy(starttime, endtime,
                                                               plant, 'DAY', 1,
                                                               split=True, meter_energy=False)
            actual_energy = 0.0
            try:
                inverter_energy_info = actual_energy_info[inverter.name]
            except:
                return
            for item in inverter_energy_info:
                actual_energy += float(item['energy'])
            association.actual_energy = actual_energy
            association.save()
            return

        elif association.event_type == "INVERTERS_UNDERPERFORMING" :
            energy_loss = 0.0
            for pa in association.performance_associations.all():
                energy_loss += float(pa.delta_energy)
            association.energy_loss = energy_loss
            association.save()
            return
        elif association.event_type == "MPPT_UNDERPERFORMING" or association.event_type == "AJB_UNDERPERFORMING":
            return
    except Exception as exc:
        logger.debug(str(exc))
