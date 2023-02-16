from sklearn.cluster import KMeans
import numpy as np
from solarrms.models import SolarPlant
import logging
logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)
from helpdesk.models import Ticket

def k_means_groups(plant_slugs, number_of_groups, include_tickets=False):
    try:
        solar_plants = SolarPlant.objects.filter(slug__in=plant_slugs)
        coordinates = []
        for plant in solar_plants:
            coordinates.append((plant.latitude, plant.longitude))
        data = np.array(coordinates)
        k_means = KMeans(n_clusters=number_of_groups, random_state=0).fit(data)
        groups = {}
        for i in range(len(k_means.cluster_centers_)):
            entry = k_means.cluster_centers_[i]
            groups[i] = {}
            groups[i]['plants'] = []
            groups[i]['plant_slugs'] = []
            groups[i]['plant_names'] = []
            groups[i]['lat'] = entry[0]
            groups[i]['long'] = entry[1]
        try:
            assert(len(k_means.labels_) == len(solar_plants))
        except Exception as exc:
            logger.debug("Assertion error, labels and solar plants len don't match")
            return {}
        plants_len = len(solar_plants)
        for i in range(plants_len):
            plant = solar_plants[i]
            group_num = k_means.labels_[i]
            groups[group_num]['plants'].append(plant)
            groups[group_num]['plant_slugs'].append(plant.slug)
            groups[group_num]['plant_names'].append(plant.name)

        for group in groups.keys():
            if len(groups[group]['plants']) == 0:
                groups.pop(group)
            elif len(groups[group]['plants']) == 1:
                groups[group]["group_name"] = str(len(groups[group]['plants'])) + " plant"#, " + str(round(tcap/1000.0,1)) + " MWp" #", ".join(groups[group]['plant_names'][0:2]) + ",..."
            else:
                groups[group]["group_name"] = str(len(groups[group]['plants'])) + " plants"#, " + str(round(tcap/1000.0,1)) + " MWp" #", ".join(groups[group]['plant_names'][0:2]) + ",..."

        if include_tickets :
            groups = get_tickets_information(groups)
        return groups
    except Exception as exc:
        logger.debug("Error while creating solar groups: " + str(exc))
        return {}


def get_tickets_information(groups):
    for group in groups.keys():
        data = {'CRITICAL': 0, 'HIGH': 0, 'NORMAL': 0}
        tcap = 0.0
        for plant in groups[group]['plants']:
            try:
                tcap += plant.capacity
            except:
                pass
            plant_data = Ticket.get_plant_live_priority_summary(plant)
            for key in plant_data.keys():
                data[key] += plant_data[key]
        groups[group]["tickets_summary"] = data
        # if len(groups[group]['plants']) == 1:
        #     groups[group]["group_name"] = str(len(groups[group]['plants'])) + " plant"#, " + str(round(tcap/1000.0,1)) + " MWp" #", ".join(groups[group]['plant_names'][0:2]) + ",..."
        # else:
        #     groups[group]["group_name"] = str(len(groups[group]['plants'])) + " plants"#, " + str(round(tcap/1000.0,1)) + " MWp" #", ".join(groups[group]['plant_names'][0:2]) + ",..."
        #groups[group]["group_name"] = ", ".join(groups[group]['plant_names'][0:2]) + ",..."
    return groups
