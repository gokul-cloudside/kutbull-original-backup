from widgets.models import Widget
from features.models import Feature

WIDGETS_LIST = {
    'BRANDHEADER': {'id': 1, 'features': ['TOTAL_SITES',
                                          'TOTAL_CAPACITY',
                                          'TOTAL_ENERGY',
                                          'LOGO']},

    'POWERREPORT': {'id': 2, 'features': ['ENERGY_GENERATION',
                                          'CURRENT_POWER',
                                          'PREDICTED_ENERGY_TILL_NOW',
                                          'PREDICTION_DEVIATION']},

    'ENERGYGENERATIONGRAPH': {'id': 3, 'features': ['ENERGY_GENERATION',
                                                    'AC_LOSSES',
                                                    'DC_LOSSES',
                                                    'SOILING_LOSSES',
                                                    'CONVERSION_LOSSES']},

    'INFRASTRUCTUREDETAILS': {'id': 4, 'features': ['GRID_AVAILABILITY',
                                                    'EQUIPMENT_AVAILABILITY']},

    'DISCONNECTEDUNITS': {'id': 5, 'features': ['INVERTER_ALERTS',
                                                'SMB_ALERTS']},

    'GATEWAYSDOWN': {'id' : 6, 'features' : ['GATEWAY_ALERTS']},

    'ACTIVEALARM': {'id' : 7, 'features' : ['INVERTER_ALERTS',
                                            'CLEANING']},

    'PREDICTEDISSUES': {'id' : 8, 'features' : ['INVERTER_COMPARISON',
                                                'SMB_COMPARISON',
                                                'MPPT_COMPARISON']},

    'SITESMAPWIDGET': {'id': 9, 'features': ['PLANTS_OVERVIEW',
                                             'PR',
                                             'CUF',
                                             'SY',
                                             'OPEN_TICKETS',
                                             'CO2']},

    'PLANTTABLE': {'id': 10, 'features': ['PLANTS_OVERVIEW',
                                          'CURRENT_POWER',
                                          'ENERGY_GENERATION',
                                          'SY',
                                          'PR',
                                          'CUF',
                                          'INVERTERS_STATUS',
                                          'DATA_LOGGERS_STATUS',
                                          'IRRADIANCE']},

    'PLANTHEADER': {'id': 11, 'features': ['LOGO',
                                           'PLANTS_OVERVIEW']},

    'PLANTOVERVIEWGRAPH': {'id': 12, 'features': ['POWER_CHART',
                                                  'IRRADIATION_CHART']},


    'PLANTGENERATIONSTATUS': {'id': 13, 'features': ['ENERGY_GENERATION',
                                                     'TOTAL_ENERGY',
                                                     'PREDICTED_ENERGY',
                                                     'PVSYST_GENERATION'
                                                     'CO2',
                                                     'HOMES_POWERED',
                                                     'TREES_PLANTED',
                                                     'PREDICTION_DEVIATION']},

    'PLANTMETRICS': {'id': 14, 'features': ['PR',
                                            'PVSYST_PR',
                                            'CUF',
                                            'PVSYST_CUF',
                                            'SY',
                                            'PVSYST_SY'
                                            'PEAK_POWER',
                                            'INSOLATION',
                                            ]},

    'PLANTPANELS': {'id': 15, 'features': ['PANELS_INFORMATION',
                                           'MODULE_TEMPERATURE',
                                           'AMBIENT_TEMPERATURE',
                                           'CLEANING']},

    'PLANTINVERTERSINFO': {'id': 16, 'features': ['INVERTERS_INFORMATION',
                                                  'CURRENT_POWER']},

    'PLANTALERTS': {'id': 17, 'features': ['GATEWAY_ALERTS',
                                           'INVERTER_ALERTS',
                                           'SMB_ALERTS',
                                           'CLEANING',
                                           'INVERTER_COMPARISON',
                                           'SMB_COMPARISON',
                                           'MPPT_COMPARISON']},

    'WEEKLY_GENERATION': {'id': 18, 'features': ['WEEKLY_GENERATION']},
    'DEVICE_DETAILS': {'id': 19, 'features': ['DEVICE_DETAILS']},
    'INVERTERS_WIDGET':{'id':20, 'features':['INVERTERS_INFORMATION','INVERTER_POWER','INVERTER_ENERGY','INVERTER_ALERTS']},
    'GATEWAYS_WIDGET':{'id':21, 'features':['GATEWAY_ALERTS','GATEWAY_DETAILS']},
    'AJBS_WIDGET':{'id':22, 'features':['AJB_DETAILS','AJB_POWER','SMB_ALERTS']},
    'METERS_WIDGET':{'id':23, 'features':['METER_ALERTS','METER_POWER','METER_GENERATION','METER_DETAILS']},
    'LOSSES_WIDGET':{'id':24, 'features':['AC_LOSSES',
                                           'DC_LOSSES',
                                           'CONVERSION_LOSSES',
                                            'ENERGY_GENERATION']},
    'PREDICTION_TIMESERIES_WIDGET':{'id':25, 'features':['PREDICTION_TIMESERIES', 'PREDICTION_TODAY']},
    'ANALYTICS_DASHBOARD_WIDGET':{'id':26, 'features':['ANALYTICS_DASHBOARD']},

    # plant group widget
    'GROUPOVERVIEWGRAPH': {'id': 27, 'features': ['GROUP_POWER_CHART']},

    # plant group widget
    'PLANTSTICKETIMPACT': {'id': 28, 'features': ['TICKET_IMPACT']},

    # generation summary
    'GENERATION_SUMMARY': {'id': 29, 'features': ['PREDICTED_ENERGY_TILL_NOW',
                                                  'ENERGY_GENERATION',
                                                  'TOTAL_SITES',
                                                  'TOTAL_CAPACITY',
                                                  'INSOLATION',
                                                  'CURRENT_POWER',
                                                  'CUF',
                                                  'PVSYST_CUF',
                                                  'PVSYST_GENERATION',
                                                  'DAILY_REVENUE']},

    'PLANT_DAILY_GENERATION': {'id':30, 'features': ['DAILY_GENERATION']},

    'PLANT_MONTHLY_GENERATION': {'id':31, 'features': ['MONTHLY_GENERATION']},

    'PLANT_WEATHER_STATION': {'id':32, 'features': ['WIND_SPEED',
                                                    'MODULE_TEMPERATURE',
                                                    'AMBIENT_TEMPERATURE',
                                                    'PLANTS_OVERVIEW']},

    'PLANT_DEVICES_INFO': {'id': 33, 'features': ['PANELS_INFORMATION',
                                                  'INVERTERS_INFORMATION',
                                                  'TOTAL_ENERGY']},

    'PLANT_PREDICTION': {'id': 34, 'features': ['PREDICTION_TODAY',
                                                'PREDICTION_TOMORROW']}
}


def initialise_widgets():
    widgets = Widget.objects.all()
    for widget in widgets:
        widget.delete()

    for widget in WIDGETS_LIST.keys():
        w = Widget.objects.create(name=widget,
                                  widget_id=WIDGETS_LIST[widget]["id"])
        for feature in Feature.objects.filter(name__in=WIDGETS_LIST[widget]["features"]):
            w.features.add(feature)



