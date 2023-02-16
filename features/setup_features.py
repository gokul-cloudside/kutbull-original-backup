from features.models import Feature, FeatureCategory, SubscriptionPlan, DGClientSubscription, RoleAccess
from dashboards.models import Dashboard, DataglenClient
from features.models import SOLAR_USER_ROLE

FEATURES_LIST = {
    'PLANT_DETAILS': {
        'TOTAL_SITES': 'solarrms2.plant_details.plant_details.total_sites',
        'TOTAL_CAPACITY': 'solarrms2.plant_details.plant_details.total_capacity',
        'PLANTS_OVERVIEW': 'solarrms2.plant_details.plant_details.plants_overview',
        'LOGO': 'solarrms2.plant_details.plant_details.logo',
        'PANELS_INFORMATION': 'solarrms2.plant_details.plant_details.panels_information',
        'INVERTERS_INFORMATION': 'solarrms2.plant_details.plant_details.inverters_information',
        'DEVICE_DETAILS': 'solarrms2.plant_details.plant_details.device_details',
        'METER_DETAILS': 'solarrms2.plant_details.plant_details.meter_details',
        'AJB_DETAILS':'solarrms2.plant_details.plant_details.ajb_details',
        'GATEWAY_DETAILS':'solarrms2.plant_details.plant_details.gateway_details'
    },
    'GENERATION': {
        'CURRENT_POWER': 'solarrms2.generation.generation.total_power',
        'TOTAL_ENERGY': 'solarrms2.generation.generation.total_energy',
        'ENERGY_GENERATION': 'solarrms2.generation.generation.generation',
        'POWER_CHART': 'solarrms2.generation.generation.power_chart',
        'IRRADIATION_CHART': 'solarrms2.generation.generation.irradiation_chart',
        'PEAK_POWER': 'solarrms2.generation.generation.peak_power',
        'INSOLATION': 'solarrms2.generation.generation.insolation',
        'WEEKLY_GENERATION':'solarrms2.generation.generation.weekly_energy',
        'METER_POWER':'solarrms2.generation.generation.meter_power',
        'METER_GENERATION':'solarrms2.generation.generation.meter_energy',
        'INVERTER_POWER':'solarrms2.generation.generation.inverter_power',
        'INVERTER_ENERGY':'solarrms2.generation.generation.inverter_energy',
        'AJB_POWER':'solarrms2.generation.generation.ajb_power',
        'PPA':'solarrms2.generation.generation.ppa_pricing',
        'DAILY_REVENUE': 'solarrms2.generation.generation.daily_revenue',
        # group widget
        'GROUP_POWER_CHART': 'solarrms2.generation.generation.group_power_chart',
        'IRRADIANCE': 'solarrms2.generation.generation.current_irradiance',
        'DAILY_GENERATION': 'solarrms2.generation.generation.daily_generation',
        'MONTHLY_GENERATION': 'solarrms2.generation.generation.monthly_generation',
    },
    'WEATHER_STATION' : {
      'WIND_SPEED': 'solarrms2.weather_station.weather_station.windspeed',
      'MODULE_TEMPERATURE': 'solarrms2.weather_station.weather_station.module_temperature',
      'AMBIENT_TEMPERATURE': 'solarrms2.weather_station.weather_station.ambient_temperature'
    },
    'METRICS': {
        'PR': 'solarrms2.metrics.metrics.pr',
        'CUF': 'solarrms2.metrics.metrics.cuf',
        'SY': 'solarrms2.metrics.metrics.sy',
    },
    'ALERTS': {
        'GATEWAY_ALERTS': 'solarrms2.alerts.alerts.gateway',
        'INVERTER_ALERTS': 'solarrms2.alerts.alerts.inverters',
        'SMB_ALERTS': 'solarrms2.alerts.alerts.smb',
        'METER_ALERTS': 'solarrms2.alerts.alerts.meter',
        'WEATHER_STATION_ALERTS': 'solarrms2.alerts.alerts.weather',
        'EMAIL_NOTIFICATIONS': 'solarrms2.alerts.alerts.email_notification',
        'SMS_NOTIFICATIONS': 'solarrms2.alerts.alerts.sms_notification',
        'OPEN_TICKETS': 'solarrms2.alerts.alerts.open_tickets',
        # get inverter down, up for plant,
        'INVERTERS_STATUS': 'solarrms2.alerts.alerts.inverter_disconnect_count',
        'DATA_LOGGERS_STATUS': 'solarrms2.alerts.alerts.gateway_disconnect_count',
        'TICKET_IMPACT': 'solarrms2.alerts.alerts.ticket_impact',
    },
    'LOSSES': {
        'SOILING_LOSSES': 'solarrms2.losses.losses.soiling',
        'DC_LOSSES': 'solarrms2.losses.losses.dc',
        'AC_LOSSES': 'solarrms2.losses.losses.ac',
        'CONVERSION_LOSSES': 'solarrms2.losses.losses.conversion',
    },
    'ANALYTICS': {
        'PREDICTION_TODAY': 'solarrms2.analytics.analytics.predicted_energy',
        'CLEANING': 'solarrms2.analytics.analytics.cleaning',
        'INVERTER_COMPARISON': 'solarrms2.analytics.analytics.inverter_comparison',
        'SMB_COMPARISON': 'solarrms2.analytics.analytics.smb_comparison',
        'MPPT_COMPARISON': 'solarrms2.analytics.analytics.mppt_comparison',
        'PREDICTION_TIMESERIES':'solarrms2.analytics.analytics.predicted_timeseries',
        'ANALYTICS_DASHBOARD':'solarrms2.analytics.analytics.analytics_dashboard',
        'PREDICTION_DEVIATION':'solarrms2.analytics.analytics.prediction_deviation',
        'PREDICTED_ENERGY_TILL_NOW': 'solarrms2.analytics.analytics.predicted_energy_till_time',
        'PREDICTION_TOMORROW': 'solarrms2.analytics.analytics.predicted_energy_tomorrow',
    },
    'AVAILABILITY': {
        'GRID_AVAILABILITY': 'solarrms2.availability.availability.grid',
        'EQUIPMENT_AVAILABILITY': 'solarrms2.availability.availability.equipment',
    },
    'ECONOMIC_BENEFITS': {
        'CO2': 'solarrms2.economic_benefits.economic_benefits.co2',
        'HOMES_POWERED': 'solarrms2.economic_benefits.economic_benefits.homes_powered',
        'TREES_PLANTED': 'solarrms2.economic_benefits.economic_benefits.trees_planted',
    },
    'REPORTS': {
        'DAILY': 'solarrms2.reports.reports.daily',
        'MONTHLY': 'solarrms2.reports.reports.monthly',
        'YEARLY': 'solarrms2.reports.reports.yearly'
    },
    'PVSYST': {
        'PVSYST_PR': 'solarrms2.pvsyst.pvsyst.pr',
        'PVSYST_CUF': 'solarrms2.pvsyst.pvsyst.cuf',
        'PVSYST_SY': 'solarrms2.pvsyst.pvsyst.sy',
        'PVSYST_GENERATION': 'solarrms2.pvsyst.pvsyst.generation',
    }
}

SUBSCRIPTION_PLANS = {
    'FREE': ['TOTAL_CAPACITY', 'CURRENT_POWER', 'TOTAL_ENERGY', 'ENERGY_GENERATION', 'POWER_CHART', 'IRRADIATION_CHART','DEVICE_DETAILS'],
    'BASIC': ['TOTAL_CAPACITY', 'CURRENT_POWER', 'TOTAL_ENERGY', 'ENERGY_GENERATION', 'POWER_CHART','PLANTS_OVERVIEW','TOTAL_SITES',
              'IRRADIATION_CHART', 'PR', 'CUF', 'SY', 'GATEWAY_ALERTS', 'CO2','DEVICE_DETAILS','LOGO','INVERTERS_INFORMATION','PANELS_INFORMATION',
              'METER_DETAILS','AJB_DETAILS','GATEWAY_DETAILS','INSOLATION','WEEKLY_GENERATION','METER_POWER','METER_GENERATION','INVERTER_POWER',
              'INVERTER_ENERGY','AJB_POWER','WIND_SPEED','MODULE_TEMPERATURE','AMBIENT_TEMPERATURE','GRID_AVAILABILITY','EQUIPMENT_AVAILABILITY',
              'CO2','TREES_PLANTED','DAILY','MONTHLY','YEARLY'],
    'PREMIUM': ['']
}


def initialise_features():
    for category in FeatureCategory.objects.all():
        category.delete()

    for category in FEATURES_LIST.keys():
        try:
            fc = FeatureCategory.objects.create(name=category, enabled=True)
        except Exception as exc:
            continue

        for feature in FEATURES_LIST[category].keys():
            try:
                f = Feature.objects.create(feature_category=fc,
                                           name=feature,
                                           enabled=True,
                                           function_path = FEATURES_LIST[category][feature])
            except Exception as exc:
                continue


def initialise_subscription_plans():
    for plan in SubscriptionPlan.objects.all():
        plan.delete()

    try:
        dashboard = Dashboard.objects.get(name="SOLAR")
    except Exception as exc:
        print "No dashboard as SOLAR"
        return

    for plan in SUBSCRIPTION_PLANS.keys():
        try:
            new_plan = SubscriptionPlan.objects.create(dashboard=dashboard,
                                                       name = plan)
            if plan == 'PREMIUM':
                for feature in Feature.objects.all():
                    new_plan.features.add(feature)
            else:
                for feature in Feature.objects.filter(name__in=SUBSCRIPTION_PLANS[plan]):
                    new_plan.features.add(feature)
        except Exception as exc:
            print (exc)
            continue


def initialise_client_subscriptions():

    for cs in DGClientSubscription.objects.all():
        cs.delete()
    clients = DataglenClient.objects.all()
    subscription = SubscriptionPlan.objects.get(name="PREMIUM")

    for client in clients:
        try:
            sp = DGClientSubscription.objects.create(dg_client=client,
                                                     subscription_plan = subscription)
        except Exception as exc:
            print (exc)
            continue


def initialise_roles_matrix():
    for rm in RoleAccess.objects.all():
        rm.delete()
    for client in DataglenClient.objects.all():
        try:
            for role in SOLAR_USER_ROLE:
                ra = RoleAccess.objects.create(dg_client=client,
                                               role=role[0])
                if role[0].startswith("CLIENT"):
                    for feature in Feature.objects.filter(name__in=SUBSCRIPTION_PLANS['BASIC']):
                        ra.features.add(feature)
                else:
                    for feature in Feature.objects.all():
                        ra.features.add(feature)

        except Exception as exc:
            print (exc)
            continue

def initialize_individual_client_subscription(client):
    subscription = SubscriptionPlan.objects.get(name="PREMIUM")
    sp = DGClientSubscription.objects.create(dg_client=client,
                                                     subscription_plan = subscription)
    sp.save()

def initialise_roles_matrix_individual_client(client):
    for role in SOLAR_USER_ROLE:
        ra = RoleAccess.objects.create(dg_client=client,
                                               role=role[0])
        if role[0].startswith("CLIENT"):
            for feature in Feature.objects.filter(name__in=SUBSCRIPTION_PLANS['BASIC']):
                ra.features.add(feature)
        else:
            for feature in Feature.objects.all():
                ra.features.add(feature)


# if __name__ == '__main__':
#     initialise_features()
#     initialise_subscription_plans()
#     initialise_client_subscriptions()
#     initialise_roles_matrix()