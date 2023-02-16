from django.utils import timezone
from helpdesk.models import Ticket, TicketAssociation
from solarrms.models import SolarGroup, IndependentInverter, GatewaySource, VirtualGateway
from django.db.models import Sum

# get the total number of open tickets
def open_tickets(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        tickets = 0
        if plants_group is not None:
            for plant in plants_group:
                ticket_detail = Ticket.get_plant_live_priority_summary(plant)
                for key in ticket_detail.keys():
                    tickets += ticket_detail[key]
        if plant is not None:
            ticket_detail = Ticket.get_plant_live_priority_summary(plant)
            for key in ticket_detail.keys():
                tickets += ticket_detail[key]
        return tickets
    except Exception as exception:
        print str(exception)


# get meter alerts
def meter(*args, **kwargs):
    try:
        return {}
    except Exception as exception:
        print str(exception)


# get gateway alerts
def gateway(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        meter=kwargs.pop('meter', None)
        inverter=kwargs.pop('inverter', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        gateways_disconnected_list = []
        gateways_powered_off_list = []
        gateway_details = []
        final_result = {}
        if plants_group is not None:
            for plant in plants_group:
                errors = []
                plant_gateway_disconnected_details = {}
                plant_gateway_powered_off_details = {}
                plant_result = {}
                plant_result['plant_name'] = str(plant.name)
                plant_result['plant_slug'] = str(plant.slug)
                plant_network_details = Ticket.get_plant_live_ops_summary(plant, ['GATEWAY_POWER_OFF','GATEWAY_DISCONNECTED'])
                if len(plant_network_details)>0:
                    try:
                        gateways_disconnected_list.extend(plant_network_details['GATEWAY_DISCONNECTED']['details'].keys())
                    except:
                        pass
                    try:
                        gateways_powered_off_list.extend(plant_network_details['GATEWAY_POWER_OFF']['details'].keys())
                    except:
                        pass

                    try:
                        if len(plant_network_details['GATEWAY_DISCONNECTED'])>0:
                            plant_gateway_disconnected_details['ticket_id'] = int(plant_network_details['GATEWAY_DISCONNECTED']['ticket_id'])
                            plant_gateway_disconnected_details['devices'] = ",".join(plant_network_details['GATEWAY_DISCONNECTED']['details'].keys())
                            plant_gateway_disconnected_details['event_type'] = 'GATEWAY_DISCONNECTED'
                            if len(plant_gateway_disconnected_details)>0:
                                errors.append(plant_gateway_disconnected_details)
                    except:
                        pass
                    try:
                        if len(plant_network_details['GATEWAY_POWER_OFF'])>0:
                            plant_gateway_powered_off_details['ticket_id'] = int(plant_network_details['GATEWAY_POWER_OFF']['ticket_id'])
                            plant_gateway_powered_off_details['devices'] = ",".join(plant_network_details['GATEWAY_POWER_OFF']['details'].keys())
                            plant_gateway_powered_off_details['event_type'] = 'GATEWAY_POWER_OFF'
                            if len(plant_gateway_powered_off_details)>0:
                                errors.append(plant_gateway_powered_off_details)
                    except:
                        pass
                    plant_result["errors"] = errors
                    gateway_details.append(plant_result)
        elif plant is not None:
            errors = []
            plant_gateway_disconnected_details = {}
            plant_gateway_powered_off_details = {}
            plant_result = {}
            plant_result['plant_name'] = str(plant.name)
            plant_result['plant_slug'] = str(plant.slug)
            plant_network_details = Ticket.get_plant_live_ops_summary(plant, ['GATEWAY_POWER_OFF','GATEWAY_DISCONNECTED'])
            if len(plant_network_details)>0:
                try:
                    gateways_disconnected_list.extend(plant_network_details['GATEWAY_DISCONNECTED']['details'].keys())
                except:
                    pass
                try:
                    gateways_powered_off_list.extend(plant_network_details['GATEWAY_POWER_OFF']['details'].keys())
                except:
                    pass

                try:
                    if len(plant_network_details['GATEWAY_DISCONNECTED'])>0:
                        plant_gateway_disconnected_details['ticket_id'] = int(plant_network_details['GATEWAY_DISCONNECTED']['ticket_id'])
                        plant_gateway_disconnected_details['devices'] = ",".join(plant_network_details['GATEWAY_DISCONNECTED']['details'].keys())
                        plant_gateway_disconnected_details['event_type'] = 'GATEWAY_DISCONNECTED'
                        if len(plant_gateway_disconnected_details)>0:
                            errors.append(plant_gateway_disconnected_details)
                except:
                    pass
                try:
                    if len(plant_network_details['GATEWAY_POWER_OFF'])>0:
                        plant_gateway_powered_off_details['ticket_id'] = int(plant_network_details['GATEWAY_POWER_OFF']['ticket_id'])
                        plant_gateway_powered_off_details['devices'] = ",".join(plant_network_details['GATEWAY_POWER_OFF']['details'].keys())
                        plant_gateway_powered_off_details['event_type'] = 'GATEWAY_POWER_OFF'
                        if len(plant_gateway_powered_off_details)>0:
                            errors.append(plant_gateway_powered_off_details)
                except:
                    pass
                plant_result["errors"] = errors
                gateway_details.append(plant_result)

        final_result['error_details'] = gateway_details
        final_result['gateways_disconnected'] = len(gateways_disconnected_list)
        final_result['gateways_powered_off'] = len(gateways_powered_off_list)
        return final_result
    except Exception as exception:
        print str(exception)


# get weather station alerts
def weather(*args, **kwargs):
    try:
        return {}
    except Exception as exception:
        print str(exception)


# get smb alerts
def smb(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        meter=kwargs.pop('meter', None)
        inverter=kwargs.pop('inverter', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        smbs_disconnected_list = []
        smb_details = []
        final_result = {}
        if plants_group is not None:
            for plant in plants_group:
                errors = []
                plant_smb_disconnected_details = {}
                plant_result = {}
                plant_result['plant_name'] = str(plant.name)
                plant_result['plant_slug'] = str(plant.slug)
                plant_network_details = Ticket.get_plant_live_ops_summary(plant, ['AJBS_DISCONNECTED'])
                if len(plant_network_details)>0:
                    try:
                        smbs_disconnected_list.extend(plant_network_details['AJBS_DISCONNECTED']['details'].keys())
                    except:
                        pass

                    try:
                        if len(plant_network_details['AJBS_DISCONNECTED'])>0:
                            plant_smb_disconnected_details['ticket_id'] = int(plant_network_details['AJBS_DISCONNECTED']['ticket_id'])
                            plant_smb_disconnected_details['devices'] = ",".join(plant_network_details['AJBS_DISCONNECTED']['details'].keys())
                            plant_smb_disconnected_details['event_type'] = 'AJBS_DISCONNECTED'
                            if len(plant_smb_disconnected_details)>0:
                                errors.append(plant_smb_disconnected_details)
                    except:
                        pass
                    plant_result["errors"] = errors
                    smb_details.append(plant_result)
        elif plant is not None:
            errors = []
            plant_smb_disconnected_details = {}
            plant_result = {}
            plant_result['plant_name'] = str(plant.name)
            plant_result['plant_slug'] = str(plant.slug)
            plant_network_details = Ticket.get_plant_live_ops_summary(plant, ['AJBS_DISCONNECTED'])
            if len(plant_network_details)>0:
                try:
                    smbs_disconnected_list.extend(plant_network_details['AJBS_DISCONNECTED']['details'].keys())
                except:
                    pass

                try:
                    if len(plant_network_details['AJBS_DISCONNECTED'])>0:
                        plant_smb_disconnected_details['ticket_id'] = int(plant_network_details['AJBS_DISCONNECTED']['ticket_id'])
                        plant_smb_disconnected_details['devices'] = ",".join(plant_network_details['AJBS_DISCONNECTED']['details'].keys())
                        plant_smb_disconnected_details['event_type'] = 'AJBS_DISCONNECTED'
                        if len(plant_smb_disconnected_details)>0:
                            errors.append(plant_smb_disconnected_details)
                except:
                    pass
                plant_result["errors"] = errors
                smb_details.append(plant_result)

        final_result['error_details'] = smb_details
        final_result['smbs_disconnected'] = len(smbs_disconnected_list)
        return final_result
    except Exception as exception:
        print str(exception)


# get inverter alerts
def inverters(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        meter=kwargs.pop('meter', None)
        inverter=kwargs.pop('inverter', None)
        starttime=kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime=kwargs.pop('endtime',timezone.now())
        inverters_disconnected_list = []
        inverters_alarms_list = []
        inverter_details = []
        final_result = {}
        if plants_group is not None:
            for plant in plants_group:
                errors = []
                plant_inverters_disconnected_details = {}
                plant_inverters_alarms_details = {}
                plant_result = {}
                plant_result['plant_name'] = str(plant.name)
                plant_result['plant_slug'] = str(plant.slug)
                plant_network_details = Ticket.get_plant_live_ops_summary(plant, ['INVERTERS_DISCONNECTED','INVERTERS_ALARMS'])
                if len(plant_network_details)>0:
                    try:
                        inverters_disconnected_list.extend(plant_network_details['INVERTERS_DISCONNECTED']['details'].keys())
                    except:
                        pass
                    try:
                        inverters_alarms_list.extend(plant_network_details['INVERTERS_ALARMS']['details'].keys())
                    except:
                        pass

                    try:
                        if len(plant_network_details['INVERTERS_DISCONNECTED'])>0:
                            plant_inverters_disconnected_details['ticket_id'] = int(plant_network_details['INVERTERS_DISCONNECTED']['ticket_id'])
                            plant_inverters_disconnected_details['devices'] = ",".join(plant_network_details['INVERTERS_DISCONNECTED']['details'].keys())
                            plant_inverters_disconnected_details['event_type'] = 'INVERTERS_DISCONNECTED'
                            if len(plant_inverters_disconnected_details)>0:
                                errors.append(plant_inverters_disconnected_details)
                    except:
                        pass
                    try:
                        if len(plant_network_details['INVERTERS_ALARMS'])>0:
                            plant_inverters_alarms_details['ticket_id'] = int(plant_network_details['INVERTERS_ALARMS']['ticket_id'])
                            plant_inverters_alarms_details['devices'] = ",".join(plant_network_details['INVERTERS_ALARMS']['details'].keys())
                            plant_inverters_alarms_details['event_type'] = 'INVERTERS_ALARMS'
                            if len(plant_inverters_alarms_details)>0:
                                errors.append(plant_inverters_alarms_details)
                    except:
                        pass
                    plant_result["errors"] = errors
                    inverter_details.append(plant_result)
        elif plant is not None:
            errors = []
            plant_inverters_disconnected_details = {}
            plant_inverters_alarms_details = {}
            plant_result = {}
            plant_result['plant_name'] = str(plant.name)
            plant_result['plant_slug'] = str(plant.slug)
            plant_network_details = Ticket.get_plant_live_ops_summary(plant, ['INVERTERS_DISCONNECTED','INVERTERS_ALARMS'])
            if len(plant_network_details)>0:
                try:
                    inverters_disconnected_list.extend(plant_network_details['INVERTERS_DISCONNECTED']['details'].keys())
                except:
                    pass
                try:
                    inverters_alarms_list.extend(plant_network_details['INVERTERS_ALARMS']['details'].keys())
                except:
                    pass

                try:
                    if len(plant_network_details['INVERTERS_DISCONNECTED'])>0:
                        plant_inverters_disconnected_details['ticket_id'] = int(plant_network_details['INVERTERS_DISCONNECTED']['ticket_id'])
                        plant_inverters_disconnected_details['devices'] = ",".join(plant_network_details['INVERTERS_DISCONNECTED']['details'].keys())
                        plant_inverters_disconnected_details['event_type'] = 'INVERTERS_DISCONNECTED'
                        if len(plant_inverters_disconnected_details)>0:
                            errors.append(plant_inverters_disconnected_details)
                except:
                    pass
                try:
                    if len(plant_network_details['INVERTERS_ALARMS'])>0:
                        plant_inverters_alarms_details['ticket_id'] = int(plant_network_details['INVERTERS_ALARMS']['ticket_id'])
                        plant_inverters_alarms_details['devices'] = ",".join(plant_network_details['INVERTERS_ALARMS']['details'].keys())
                        plant_inverters_alarms_details['event_type'] = 'INVERTERS_ALARMS'
                        if len(plant_inverters_alarms_details)>0:
                            errors.append(plant_inverters_alarms_details)
                except:
                    pass
                plant_result["errors"] = errors
                inverter_details.append(plant_result)

        final_result['error_details'] = inverter_details
        final_result['inverters_disconnected'] = len(inverters_disconnected_list)
        final_result['inverters_alarms'] = len(inverters_alarms_list)
        return final_result

    except Exception as exception:
        print str(exception)

# email_notification
def email_notification(*args, **kwargs):
    try:
        pass
    except Exception as exception:
        print str(exception)

# sms_notification
def sms_notification(*args, **kwargs):
    try:
        pass
    except Exception as exception:
        print str(exception)


def inverter_disconnect_count(*args, **kwargs):
    """

    :param args:
    :param kwargs:
    :return:
    """
    try:
        plants_group = kwargs.pop('plants_group', None)
        plant = kwargs.pop('plant', None)
        # plant group
        group_call = kwargs.pop('group_call', False)
        solar_groups = kwargs.pop('solar_groups', None)
        group = kwargs.pop('group', None)
        starttime = kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime = kwargs.pop('endtime',timezone.now())
        split = kwargs.pop('split', None)
        inverter_disconnect_dict = {}
        total_disconnect = 0
        total_inverters = 0
        total_connect = 0
        # group filter call
        if group_call:
            group_count = False
            if solar_groups is not None:
                group_count = True
                for group in solar_groups:
                    all_inverters = set(group.groupIndependentInverters.values_list('sourceKey', flat=True))
                    disconnected_inverter = set(
                        TicketAssociation.objects.filter(ticket__queue__plant_id=group.plant_id, active=True,
                                                         event_type="INVERTERS_DISCONNECTED",
                                                         identifier__in=all_inverters).\
                            values_list('identifier', flat=True))
                    inverter_count = len(all_inverters)
                    up_inverters = inverter_count - len(disconnected_inverter)
                    inverter_disconnect_dict["%s" % group.varchar_id] = "%s/%s" % (up_inverters, inverter_count)

                    total_connect += up_inverters
                    total_disconnect += len(disconnected_inverter)
                    total_inverters += inverter_count
                # for all group level
            elif group is not None:
                all_inverters = set(group.groupIndependentInverters.values_list('sourceKey', flat=True))
                disconnected_inverter = set(
                    TicketAssociation.objects.filter(ticket__queue__plant_id=group.plant_id, active=True,
                                                     event_type="INVERTERS_DISCONNECTED",
                                                     identifier__in=all_inverters).\
                        values_list('identifier', flat=True))
                inverter_count = len(all_inverters)
                up_inverters = inverter_count - len(disconnected_inverter)
                inverter_disconnect_dict["%s" % group.varchar_id] = "%s/%s" % (up_inverters, inverter_count)

                total_connect += up_inverters
                total_disconnect += len(disconnected_inverter)
                total_inverters += inverter_count
            if group_count:
                inverter_disconnect_dict['TOTAL'] = "%s/%s" %(total_connect, total_inverters)
                return inverter_disconnect_dict
            else:
                return "%s/%s" %(total_connect, total_inverters)
        else:
            if plants_group is not None:
                for plant in plants_group:
                    all_inverters = set(plant.independent_inverter_units.all().values_list('sourceKey', flat=True))
                    disconnected_inverter = set(
                        TicketAssociation.objects.filter(ticket__queue__plant_id=plant.id, active=True,
                                                         event_type="INVERTERS_DISCONNECTED",
                                                         identifier__in=all_inverters).\
                            values_list('identifier', flat=True))
                    inverter_count = len(all_inverters)
                    up_inverters = inverter_count - len(disconnected_inverter)
                    inverter_disconnect_dict["%s" % plant.slug] = "%s/%s" % (up_inverters, inverter_count)

                    total_connect += up_inverters
                    total_disconnect += len(disconnected_inverter)
                    total_inverters += inverter_count
            elif plant is not None:
                all_inverters = set(plant.independent_inverter_units.all().values_list('sourceKey', flat=True))
                disconnected_inverter = set(
                    TicketAssociation.objects.filter(ticket__queue__plant_id=plant.id, active=True,
                                                     event_type="INVERTERS_DISCONNECTED",
                                                     identifier__in=all_inverters).\
                        values_list('identifier', flat=True))
                inverter_count = len(all_inverters)
                up_inverters = inverter_count - len(disconnected_inverter)
                inverter_disconnect_dict["%s" % plant.slug] = "%s/%s" % (up_inverters, inverter_count)

                total_connect += up_inverters
                total_disconnect += len(disconnected_inverter)
                total_inverters += inverter_count
            if split is True:
                inverter_disconnect_dict['TOTAL'] = "%s/%s" % (total_connect, total_inverters)
                return inverter_disconnect_dict
            else:
                return "%s/%s" % (total_connect, total_inverters)
    except Exception as exception:
        print "%s" % exception


def gateway_disconnect_count(*args, **kwargs):
    """

    :param args:
    :param kwargs:
    :return:
    """
    try:
        plants_group = kwargs.pop('plants_group', None)
        plant = kwargs.pop('plant', None)
        # plant group
        group_call = kwargs.pop('group_call', False)
        solar_groups = kwargs.pop('solar_groups', None)
        group = kwargs.pop('group', None)
        starttime = kwargs.pop('starttime',timezone.now().replace(hour=0, minute=0, second=0, microsecond=0))
        endtime = kwargs.pop('endtime',timezone.now())
        split = kwargs.pop('split', None)
        gatway_disconnect_dict = {}
        total_disconnect = 0
        total_gatways = 0
        total_connect = 0
        # group filter call
        if group_call:
            group_count = False
            if solar_groups is not None:
                group_count = True
                for group in solar_groups:
                    all_gateways = set(group.groupGatewaySources.values_list('sourceKey', flat=True))
                    with_virtual_gateways = all_gateways.union(set(group.group_virtual_gateway_units.values_list('sourceKey', flat=True)))

                    disconnected_gateway = set(
                        TicketAssociation.objects.filter(ticket__queue__plant_id=group.plant_id, active=True,
                                                         event_type__in=('GATEWAY_POWER_OFF','GATEWAY_DISCONNECTED'),
                                                         identifier__in=with_virtual_gateways).values_list('id', flat=True))
                    gateway_count = len(all_gateways)
                    up_gateways = gateway_count - len(disconnected_gateway)
                    gatway_disconnect_dict["%s" % group.varchar_id] = "%s/%s" % (up_gateways, gateway_count)

                    total_connect += up_gateways
                    total_disconnect += len(disconnected_gateway)
                    total_gatways += gateway_count
                # for all group level
            elif group is not None:
                all_gateways = set(group.groupGatewaySources.values_list('sourceKey', flat=True))
                with_virtual_gateways = all_gateways.union(set(group.group_virtual_gateway_units.values_list('sourceKey', flat=True)))

                disconnected_gateway = set(
                    TicketAssociation.objects.filter(ticket__queue__plant_id=group.plant_id, active=True,
                                                     event_type__in=('GATEWAY_POWER_OFF','GATEWAY_DISCONNECTED'),
                                                     identifier__in=with_virtual_gateways).\
                        values_list('identifier', flat=True))
                gateway_count = len(all_gateways)
                up_gateways = gateway_count - len(disconnected_gateway)
                gatway_disconnect_dict["%s" % group.varchar_id] = "%s/%s" % (up_gateways, gateway_count)

                total_connect += up_gateways
                total_disconnect += len(disconnected_gateway)
                total_gatways += gateway_count
            if group_count:
                gatway_disconnect_dict['TOTAL'] = "%s/%s" %(total_connect, total_gatways)
                return gatway_disconnect_dict
            else:
                return "%s/%s" %(total_connect, total_gatways)
        else:
            if plants_group is not None:
                for plant in plants_group:
                    if len(plant.solar_groups.all()) > 0:
                        all_gateways = set(GatewaySource.objects.filter(solar_groups__in=plant.solar_groups.all()).values_list('sourceKey', flat=True))
                        with_virtual_gateways = all_gateways.union(set(VirtualGateway.objects.filter(solar_group__in=plant.solar_groups.all()).values_list('sourceKey', flat=True)))
                    else:
                        all_gateways = set(plant.gateway.all().values_list('sourceKey', flat=True))
                        with_virtual_gateways = all_gateways.union(set(plant.virtual_gateway_units.all().values_list('sourceKey', flat=True)))


                    disconnected_gateway = set(
                        TicketAssociation.objects.filter(ticket__queue__plant_id=plant.id, active=True,
                                                         event_type__in=('GATEWAY_POWER_OFF','GATEWAY_DISCONNECTED'),
                                                         identifier__in=with_virtual_gateways).\
                            values_list('identifier', flat=True))
                    gateway_count = len(all_gateways)
                    up_gateways = gateway_count - len(disconnected_gateway)
                    gatway_disconnect_dict["%s" % plant.slug] = "%s/%s" % (up_gateways, gateway_count)

                    total_connect += up_gateways
                    total_disconnect += len(disconnected_gateway)
                    total_gatways += gateway_count
            elif plant is not None:
                if len(plant.solar_groups.all()) > 0:
                    all_gateways = set(GatewaySource.objects.filter(solar_groups__in=plant.solar_groups.all()).values_list('sourceKey', flat=True))
                    with_virtual_gateways = all_gateways.union(set(
                        VirtualGateway.objects.filter(solar_group__in=plant.solar_groups.all()).values_list('sourceKey',
                                                                                                            flat=True)))
                else:
                    all_gateways = set(plant.gateway.all().values_list('sourceKey', flat=True))
                    with_virtual_gateways = all_gateways.union(set(plant.virtual_gateway_units.all().values_list('sourceKey', flat=True)))

                disconnected_gateway = set(
                    TicketAssociation.objects.filter(ticket__queue__plant_id=plant.id, active=True,
                                                     event_type__in=('GATEWAY_POWER_OFF','GATEWAY_DISCONNECTED'),
                                                     identifier__in=with_virtual_gateways).\
                        values_list('identifier', flat=True))
                gateway_count = len(all_gateways)
                up_gateways = gateway_count - len(disconnected_gateway)
                gatway_disconnect_dict["%s" % plant.slug] = "%s/%s" % (up_gateways, gateway_count)

                total_connect += up_gateways
                total_disconnect += len(disconnected_gateway)
                total_gatways += gateway_count
            if split is True:
                gatway_disconnect_dict['TOTAL'] = "%s/%s" % (total_connect, total_gatways)
                return gatway_disconnect_dict
            else:
                return "%s/%s" % (total_connect, total_gatways)
    except Exception as exception:
        print "%s" % exception


def ticket_impact(*args, **kwargs):
    """

    :param args:
    :param kwargs:
    :return:
    """
    try:
        plants_group = kwargs.pop('plants_group', None)
        plant = kwargs.pop('plant', None)
        impact_capacity = {}
        impact_capacity['total_capacity'] = 0.0
        all_plants = []
        if plants_group is not None:
            for plant in plants_group:
                all_plants.append(plant.id)
                impact_capacity['total_capacity'] += plant.capacity
        elif plant is not None:
            all_plants.append(plant.id)
            impact_capacity['total_capacity'] += plant.capacity
        if all_plants:
            # all gateway disconnected
            gateway_down_identifiers = TicketAssociation.objects.filter(ticket__queue__plant_id__in=all_plants,
                                                                        active=True,
                                                                        event_type__in=(
                                                                        'GATEWAY_POWER_OFF', 'GATEWAY_DISCONNECTED')) \
                .values_list('identifier', flat=True)
            gateway_impact = 0.0
            for group in set(SolarGroup.objects.filter(groupGatewaySources__sourceKey__in=gateway_down_identifiers)):
                capacity_t = group.groupIndependentInverters.all().aggregate(total_capacity=Sum('actual_capacity'))
                gateway_impact += capacity_t['total_capacity'] if capacity_t['total_capacity'] else 0.0
            impact_capacity['plant_unreachable'] = gateway_impact
            # all inverter disconnected
            inverter_impact = 0.0
            inverter_down_identifiers = TicketAssociation.objects.filter(ticket__queue__plant_id__in=all_plants,
                                                                         active=True, event_type="INVERTERS_DISCONNECTED") \
                .values_list('identifier', flat=True)
            for group in set(SolarGroup.objects.filter(groupIndependentInverters__sourceKey__in=inverter_down_identifiers)):
                capacity_t = group.groupIndependentInverters.all().aggregate(total_capacity=Sum('total_capacity'))
                inverter_impact += capacity_t['total_capacity'] if capacity_t['total_capacity'] else 0.0
            impact_capacity['inverter_unreachable'] = inverter_impact
            # all inverter alarm
            alarm_inverter_impact = 0.0
            inverter_down_identifiers = TicketAssociation.objects.filter(ticket__queue__plant_id__in=all_plants,
                                                                         active=True, event_type="INVERTERS_ALARMS") \
                .values_list('identifier', flat=True)
            alarm_inverter_impact = IndependentInverter.objects.filter(sourceKey__in=inverter_down_identifiers).\
                aggregate(total_capacity=Sum('total_capacity'))
            impact_capacity['inverter_alarm'] = alarm_inverter_impact['total_capacity']
            return impact_capacity
    except Exception as exception:
        print "error on ticket_impact" % exception