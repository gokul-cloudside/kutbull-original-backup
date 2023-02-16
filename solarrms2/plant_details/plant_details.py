from solarrms.api_views import fix_capacity_units
from solarrms2.alerts.alerts import gateway

# get total capacity for client, plant, inverter based on the scope.
def total_capacity(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        inverter=kwargs.pop('inverter', None)
        total_capacity = 0.0
        if plants_group is not None:
            for plant in plants_group:
                total_capacity += float(plant.capacity)
        elif plant is not None and inverter is not None:
            total_capacity = inverter.total_capacity if inverter.total_capacity else inverter.actual_capacity
        elif plant is not None:
            total_capacity = plant.capacity
        return total_capacity
    except Exception as exception:
        print str(exception)
        return 0.0


# get the panel information of the plant
def panels_information(*args, **kwargs):
    try:
        plant=kwargs.pop('plant', None)
        panel_details = {}
        panel_numbers = int(plant.metadata.plantmetasource.no_of_panels) if plant.metadata.plantmetasource.no_of_panels else 0
        panel_make = str(plant.metadata.plantmetasource.panel_manufacturer)
        panel_model = str(plant.metadata.plantmetasource.model_number)
        panel_capacity = float(plant.metadata.plantmetasource.panel_capacity)
        panel_details['numbers'] = panel_numbers
        panel_details['make'] = panel_make
        panel_details['model'] = panel_model
        panel_details['capacity'] = panel_capacity
        return panel_details
    except Exception as exception:
        print str(exception)
        return {}


# get the plants overview (name, location)
def plants_overview(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        # plant group
        group_call = kwargs.pop('group_call', False)
        solar_groups = kwargs.pop('solar_groups', None)
        group = kwargs.pop('group', None)
        plants_overview = {}
        groups_overview = {}
        # group call
        if group_call:
            if solar_groups is not None:
                for group in solar_groups:
                    group_overview = {}
                    group_overview['plant_name'] = "%s (%s)" % (group.name, group.plant.name)
                    group_overview['plant_capacity'] = \
                        sum(list(group.groupIndependentInverters.all().values_list('total_capacity', flat=True)))
                    group_overview['latitude'] = group.latitude
                    group_overview['longitude'] = group.longitude
                    group_overview['plant_type'] = group.group_type
                    group_overview['installer_type'] = group.roof_type
                    group_overview['slug'] = group.plant.slug
                    groups_overview["%s" % group.varchar_id] = group_overview
                return groups_overview
            elif group is not None:
                groups_overview['plant_name'] = "%s (%s)" % (group.name, group.plant.name)
                groups_overview['plant_capacity'] = \
                    sum(list(group.groupIndependentInverters.all().values_list('total_capacity', flat=True)))
                groups_overview['latitude'] = group.latitude
                groups_overview['longitude'] = group.longitude
                groups_overview['plant_type'] = group.group_type
                groups_overview['installer_type'] = group.roof_type
                groups_overview['slug'] = group.plant.slug
                return groups_overview
        else:
            if plants_group is not None:
                for plant in plants_group:
                    plant_overview = {}
                    plant_overview['plant_name'] = str(plant.name)
                    plant_overview['plant_location'] = str(plant.location)
                    plant_overview['plant_capacity'] = plant.capacity
                    plant_overview['latitude'] = plant.latitude
                    plant_overview['longitude'] = plant.longitude
                    try:
                        plant_overview['plant_type'] = plant.metadata.plantmetasource.plant_type
                    except:
                        plant_overview['plant_type'] = None
                    try:
                        plant_overview['installer_type'] = plant.metadata.plantmetasource.installer_type
                    except:
                        plant_overview['installer_type'] = None
                    if not plant.metadata.plantmetasource.isMonitored:
                       plant_overview['status'] = 'Unmonitored'
                    else:
                        gateway_alerts = gateway(plant=plant)
                        if int(gateway_alerts['gateways_disconnected']) >0 or int(gateway_alerts['gateways_powered_off'])>0:
                            plant_overview['status'] = 'Disconnected'
                        else:
                            plant_overview['status'] = 'Connected'
                    plants_overview[str(plant.slug)] = plant_overview
                return plants_overview
            elif plant is not None:
                if plant.slug == "hirschvogelcomponents":
                    plants_overview['plant_name'] = str("Hirschvogel Components")
                else:
                    plants_overview['plant_name'] = str(plant.name)
                plants_overview['plant_location'] = str(plant.location)
                plants_overview['plant_capacity'] = plant.capacity
                plants_overview['latitude'] = plant.latitude
                plants_overview['longitude'] = plant.longitude
                try:
                    plants_overview['plant_type'] = plant.metadata.plantmetasource.plant_type
                except:
                    plants_overview['plant_type'] = None
                try:
                    plants_overview['installer_type'] = plant.metadata.plantmetasource.installer_type
                except:
                    plants_overview['installer_type'] = None
                if not plant.metadata.plantmetasource.isMonitored:
                   plants_overview['status'] = 'Unmonitored'
                else:
                    gateway_alerts = gateway(plant=plant)
                    if int(gateway_alerts['gateways_disconnected']) >0 or int(gateway_alerts['gateways_powered_off'])>0:
                        plants_overview['status'] = 'Disconnected'
                    else:
                        plants_overview['status'] = 'Connected'
                return plants_overview
    except Exception as exception:
        print str(exception)
        return {}

# get the logo
def logo(*args, **kwargs):
    try:
        logo_details = {}
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        if plants_group is not None:
            if len(plants_group)>0:
                plant = plants_group[0]
                try:
                    client = plant.groupClient
                    logo = str(client.dataglenclient.clientLogo) if client.dataglenclient and client.dataglenclient.clientLogo else ""
                except:
                    logo = ""
            logo_details['client_logo'] = logo
        elif plant is not None:
            try:
                logo = plant.dataglengroup.groupLogo if plant.dataglengroup and plant.dataglengroup.groupLogo else plant.groupClient.clientLogo
            except:
                logo = ""
            logo_details['plant_logo'] = logo
        return logo_details
    except Exception as exception:
        print str(exception)
        return {}

# get inverter details for ant plant
def inverters_information(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        group_inverter_details = {}
        if plants_group is not None:
            for plant in plants_group:
                inverter_details = {}
                inverter_numbers = len(plant.independent_inverter_units.all().filter(isActive=True))
                inverter_make = plant.independent_inverter_units.all()[0].manufacturer
                inverter_model = plant.independent_inverter_units.all()[0].model if plant.independent_inverter_units.all()[0].model else None
                capacities = {}
                for inverter in plant.independent_inverter_units.all():
                    try:
                        capacities[inverter.total_capacity] += 1
                    except KeyError:
                        capacities[inverter.total_capacity] = 1
                    except:
                        continue
                inverters_capacity_string = []
                for capacity, number in capacities.iteritems():
                    inverters_capacity_string.append(str(capacity) + " kW X " + str(number))
                inverter_details['numbers'] = inverter_numbers
                inverter_details['make'] = inverter_make
                inverter_details['model'] = inverter_model
                inverter_details['capacity'] = ",".join(inverters_capacity_string)
                group_inverter_details[str(plant.slug)] = inverter_details
        elif plant is not None:
            inverter_numbers = len(plant.independent_inverter_units.all().filter(isActive=True))
            inverter_make = plant.independent_inverter_units.all()[0].manufacturer
            inverter_model = plant.independent_inverter_units.all()[0].model if plant.independent_inverter_units.all()[0].model else None
            capacities = {}
            for inverter in plant.independent_inverter_units.all():
                try:
                    capacities[inverter.total_capacity] += 1
                except KeyError:
                    capacities[inverter.total_capacity] = 1
                except:
                    continue
            inverters_capacity_string = []
            for capacity, number in capacities.iteritems():
                inverters_capacity_string.append(str(capacity) + " kW X " + str(number))
            group_inverter_details['numbers'] = inverter_numbers
            group_inverter_details['make'] = inverter_make
            group_inverter_details['model'] = inverter_model
            group_inverter_details['capacity'] = ",".join(inverters_capacity_string)
        return group_inverter_details
    except Exception as exception:
        print str(exception)
        return {}

# get total number of sites
def total_sites(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        total_sites_number = 0
        if plants_group is not None and len(plants_group)>0:
            total_sites_number =  len(plants_group)
        elif plant is not None:
            total_sites_number = 1
        return total_sites_number
    except Exception as exception:
        print str(exception)
        return 0

# get total device details
def device_details(*args, **kwargs):
    try:
        plants_group=kwargs.pop('plants_group', None)
        plant=kwargs.pop('plant', None)
        inverters = 0
        ajbs = 0
        energy_meters=0
        transformers=0
        result = {}
        if plants_group is not None:
            for plant in plants_group:
                device_details_dict = {}
                inverters += len(plant.independent_inverter_units.all())
                ajbs += len(plant.ajb_units.all())
                energy_meters += len(plant.energy_meters.all())
                transformers += len(plant.transformers.all())
                if plant.slug == "instaproducts":
                    device_details_dict['inverters'] = 0
                else:
                    device_details_dict['inverters'] = len(plant.independent_inverter_units.all())
                device_details_dict['ajbs'] = len(plant.ajb_units.all())
                # if plant.slug == "instaproducts":
                #     device_details_dict['energy_meters'] = 0
                # else:
                device_details_dict['energy_meters'] = len(plant.energy_meters.all())
                device_details_dict['transformers'] = len(plant.transformers.all())
                device_details_dict['dsm'] = plant.metadata.plantmetasource.dsm_enabled
                result[str(plant.slug)] = device_details_dict
        elif plant is not None:
            device_details_dict = {}
            inverters += len(plant.independent_inverter_units.all())
            ajbs += len(plant.ajb_units.all())
            energy_meters += len(plant.energy_meters.all())
            transformers += len(plant.transformers.all())
            if plant.slug == "instaproducts":
                device_details_dict['inverters'] = 0
            else:
                device_details_dict['inverters'] = len(plant.independent_inverter_units.all())
            device_details_dict['ajbs'] = len(plant.ajb_units.all())
            # if plant.slug == "instaproducts":
            #     device_details_dict['energy_meters'] = 0
            # else:
            device_details_dict['energy_meters'] = len(plant.energy_meters.all())
            device_details_dict['transformers'] = len(plant.transformers.all())
            device_details_dict['dsm'] = plant.metadata.plantmetasource.dsm_enabled
            result[str(plant.slug)] = device_details_dict
        result['total_inverters'] =inverters
        result['total_ajbs'] =ajbs
        result['total_energy_meters'] = energy_meters
        result['total_transformers'] = transformers
        return result
    except Exception as exception:
        print str(exception)

def meter_details(*args, **kwargs):
    try:
        plant=kwargs.pop('plant', None)
        meters = plant.energy_meters.all()
        result={}
        if len(meters)==0:
            return "NA"
        else:
            ht_meters = plant.energy_meters.all().filter(energy_calculation=True)
            ht_meters_dict = {}
            if len(ht_meters)>0:
                ht_meters_dict['count'] = len(ht_meters)
                ht_meters_dict['make'] = ht_meters[0].manufacturer
                ht_meters_dict['model'] = ht_meters[0].model
                result['HT_METERS'] = ht_meters_dict
            lt_meters = plant.energy_meters.all().filter(energy_calculation=False)
            if len(lt_meters)>0:
                lt_meters_dict = {}
                lt_meters_dict['count'] = len(lt_meters)
                lt_meters_dict['make'] = lt_meters[0].manufacturer
                lt_meters_dict['model'] = lt_meters[0].model
                result['OTHER_METERS'] = lt_meters_dict
            return result
    except Exception as exception:
        print str(exception)

def ajb_details(*args, **kwargs):
    try:
        plant=kwargs.pop('plant', None)
        ajbs = plant.ajb_units.all()
        result = {}
        if len(ajbs)==0:
            return "NA"
        else:
            if len(ajbs)>0:
                result['count'] = len(ajbs)
                result['make'] = ajbs[0].manufacturer
            return result
    except Exception as exception:
        print str(exception)

def gateway_details(*args, **kwargs):
    try:
        plant=kwargs.pop('plant', None)
        gateways = []
        if len(plant.solar_groups.all()) >0 and plant.gateway.all()[0].isVirtual:
            for group in plant.solar_groups.all():
                gateways.extend(group.groupGatewaySources.all())
        else:
            gateways = plant.gateway.all()
        result = {}
        if len(gateways)==0:
            return "NA"
        else:
            result['count'] = len(gateways)
            # try:
            #     if gateways[0].isVirtual and plant.groupClient.slug=='jackson':
            #         result['make'] = 'DelRemo'
            #     elif gateways[0].isVirtual:
            #         result['make'] = 'Webdyn'
            #     else:
            #         result['make'] = 'Soekris'
            # except Exception as exception:
            #     print str(exception)
            #     result['make'] = 'Webdyn'
            try:
                result['make'] = plant.metadata.plantmetasource.gateway_manufacturer
            except:
                result['make'] = 'DataGlen'
            return result
    except Exception as exception:
        print str(exception)