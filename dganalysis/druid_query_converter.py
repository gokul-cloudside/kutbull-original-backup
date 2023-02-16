import pytz
import copy
import json
from pydruid.client import *
from pydruid import *
from pydruid.utils.aggregators import *
from pydruid.utils.filters import *
from pydruid.utils.postaggregator import *
from pydruid.utils.having import Having
import pandas as pd
import numpy as np
from dganalysis.models import DataAnalysis
from solarrms.models import SolarPlant, IndependentInverter, EnergyMeter, SolarGroup, IOSensorField
from dataglen.models import Sensor
from django.db.models import Sum, Max
from datetime import datetime, timedelta
from operator import iand
from solarrms2.views import get_ppa_price


DRUID_SERVER_PORT = 'http://10.148.0.16:8082'
DRUID_API = 'druid/v2'
DATASOURCE = 'dgc_prod_warehouse'
client_query = PyDruid(DRUID_SERVER_PORT, DRUID_API)

TIMESERIES = 'timeseries'
GROUPBY = 'groupby'
TOPN = 'topn'
QUERY_TYPE = ((TIMESERIES, TIMESERIES),
              (GROUPBY, GROUPBY),
              (TOPN, TOPN))
ANALYSIS_TYPE = (('system', 'SYSTEM'), ('user', 'USER'))
VIEW_TYPE = (('user', 'USER'), ('client', 'CLIENT'), ('customer', 'customer'))

GRANULARITY_IN_NUMBER = {"fifteen_minute": 15,
               "thirty_minute": 30,
               "hour": 60,
               "day": 24*60,
               "month": 30*24*60}

GRANULARITY = {"fifteen_minute": "instantaneous_aggregation",
               "thirty_minute": "instantaneous_aggregation",
               "hour": "instantaneous_aggregation",
               "day": "daily_aggregation",
               "month": "monthly_aggregation"}

GRANULARITY_PERIOD = {"fifteen_minute": "PT15M",
               "thirty_minute": "PT30M",
               "hour": "PT1H",
               "day": "P1D",
               "month": "P1M"}

granuality_dict = {"type": "period", "period": "", "origin": ""}
having_clause_dict = {"type": "and", "havingSpecs": []}

class DruidQueryConverter(object):

    def __init__(self):
        """

        """
        self.query_druid_params = {}
        self.others_params = {}
        self.plant = None
        self.inverter = []
        self.energy_meter = []
        self.data_analysis_dict = {}

    def fetch_query_dataset(self, analysis=None, column_name="stream_value"):
        """
        this function will build the slice dict as below

        {1001L: {'child': {1002L: {'fixed_instantaneous_granularity': False, 'data_unit': u'kWh',
        'name': u'Plant Generation from Inverter Raw Last-First', 'filter_stream_name': u'TOTAL_YIELD',
        'having': [{'having_clause': u'{ "type": "greaterThan", "aggregation": "%s", "value": %d }',
        'having_clause_key': u''}, {'having_clause': u'{ "type": "lessThan", "aggregation": "%s", "value": %d }',
        'having_clause_key': u''}], 'parent_id': 1001L, 'instantaneous_aggregation': {'name': u'(Last-First)
        Value of the period', 'post_aggregations': u"{'last_minus_first': (HyperUniqueCardinality('last_value')
        - HyperUniqueCardinality('first_value'))}", 'post_aggregation_key': u'last_minus_first', 'aggregations':
        u'{"first_value": doublefirst("%s"), "last_value": doublelast("%s")}', 'aggregation_key': u'first_value,
        last_value', 'default_data_key': u'stream_value', 'data_key': u'last_minus_first'}, 'query_id': 52L,
        'normalized': False, 'instantaneous_minutes': 15L, 'css_options': {'viz_type': u'column', 'css': u''},
        'data_family': u'INVERTER', 'display_name': u'Inverter - Total Generation', 'daily_aggregation':
        {'name': u'(Last-First) Value of the period', 'post_aggregations': u"{'last_minus_first':
        (HyperUniqueCardinality('last_value') - HyperUniqueCardinality('first_value'))}", 'post_aggregation_key':
        u'last_minus_first', 'aggregations': u'{"first_value": doublefirst("%s"), "last_value": doublelast("%s")}',
        'aggregation_key': u'first_value, last_value', 'default_data_key': u'stream_value', 'data_key':
        u'last_minus_first'}, 'dimension': u'source_key', 'monthly_aggregation': {'name': u'(Last-First)
        Value of the period', 'post_aggregations': u"{'last_minus_first': (HyperUniqueCardinality('last_value') -
         HyperUniqueCardinality('first_value'))}", 'post_aggregation_key': u'last_minus_first', 'aggregations':
         u'{"first_value": doublefirst("%s"), "last_value": doublelast("%s")}', 'aggregation_key': u'first_value,
         last_value', 'default_data_key': u'stream_value', 'data_key': u'last_minus_first'}}},
         'fixed_instantaneous_granularity': False, 'data_unit': u'kWh', 'name': u'Plant Generation from Inverter
         Raw Sum', 'filter_stream_name': u'TOTAL_YIELD', 'having': [{'having_clause': u'{ "type": "greaterThan",
         "aggregation": "%s", "value": %d }', 'having_clause_key': u''}, {'having_clause': u'{ "type": "lessThan",
         "aggregation": "%s", "value": %d }', 'having_clause_key': u''}], 'parent_id': None, 'instantaneous_aggregation'
         : {'name': u'Values Sum', 'post_aggregations': u'', 'post_aggregation_key': u'', 'aggregations':
         u'{"sum_value": doublesum("%s")}', 'aggregation_key': u'sum_value', 'default_data_key': u'stream_value',
         'data_key': u'sum_value'}, 'query_id': 62L, 'normalized': False, 'instantaneous_minutes': 15L, 'css_options':
         {'viz_type': u'column', 'css': u''}, 'data_family': u'PLANT', 'display_name': u'Plant Generation (Inverters)',
          'daily_aggregation': {'name': u'Values Sum', 'post_aggregations': u'', 'post_aggregation_key': u'',
          'aggregations': u'{"sum_value": doublesum("%s")}', 'aggregation_key': u'sum_value', 'default_data_key':
          u'stream_value', 'data_key': u'sum_value'}, 'dimension': u'plant_slug', 'monthly_aggregation':
          {'name': u'Values Sum', 'post_aggregations': u'', 'post_aggregation_key': u'', 'aggregations': u'{"sum_value":
           doublesum("%s")}', 'aggregation_key': u'sum_value', 'default_data_key': u'stream_value', 'data_key':
           u'sum_value'}}}

        :return:
        """
        if analysis:
            data_analysis = DataAnalysis.objects.get(id=analysis)
            self.data_analysis_dict['operation_text'] = data_analysis.operation_text
            self.data_analysis_dict['analysis_name'] = data_analysis.name
            self.data_analysis_dict['analysis_unit'] = data_analysis.analysis_unit
            for slice in data_analysis.slices.all(): #filter(parent_slice=None)
                slice_dict = {}
                slice_dict['data_family'] = slice.query_options.data_family
                slice_dict['display_name'] = slice.query_options.display_name
                slice_dict['filter_stream_name'] = slice.query_options.filter_stream_name
                slice_dict['dimension'] = slice.query_options.dimension
                slice_dict['data_unit'] = slice.query_options.data_unit
                slice_dict['query_id'] = slice.query_options.query_id
                # added for another colum filter
                slice_dict['filter_column_name'] = slice.query_options.filter_column_name
                slice_dict['name'] = slice.name
                slice_dict['parent_id'] = slice.parent_slice_id
                slice_dict['normalized'] = slice.normalized
                slice_dict['fixed_instantaneous_granularity'] = slice.fixed_instantaneous_granularity
                slice_dict['data_source'] = slice.data_source
                slice_dict['which_irradiation'] = slice.irradiation
                slice_dict['granularity_origin'] = slice.granularity_origin

                #fetch css property
                slice_dict['css_options'] = {'css': json.loads(slice.css_options.css),
                                             'viz_type': slice.css_options.viz_type}
                # fetch daily aggregation
                #include only pydruid library on eval
                aggregations_string = slice.daily_aggregation.aggregations
                #aggregations_string = eval(aggregations_string.replace("%s", column_name))
                post_aggregations_string = slice.daily_aggregation.post_aggregations
                #post_aggregations_string = eval(post_aggregations_string.replace("%s", column_name)) if post_aggregations_string.replace("%s", column_name) else ''
                slice_dict['daily_aggregation'] = {'name': slice.daily_aggregation.name,
                                                   'aggregation_key': slice.daily_aggregation.aggregation_key,
                                                   'aggregations': aggregations_string,
                                                   'post_aggregation_key': slice.daily_aggregation.post_aggregation_key,
                                                   'post_aggregations': post_aggregations_string,
                                                   'data_key': slice.daily_aggregation.data_key,
                                                   'default_data_key': slice.daily_aggregation.default_column_name
                                                   }

                # fetch instantaneous aggregation
                aggregations_string = slice.instantaneous_aggregation.aggregations
                #aggregations_string = aggregations_string.replace("%s", column_name)
                post_aggregations_string = slice.instantaneous_aggregation.post_aggregations
                #post_aggregations_string = eval(post_aggregations_string.replace("%s", column_name)) if post_aggregations_string.replace("%s", column_name) else ''
                slice_dict['instantaneous_aggregation'] = {'name': slice.instantaneous_aggregation.name,
                                                           'aggregation_key': slice.instantaneous_aggregation.aggregation_key,
                                                           'aggregations': aggregations_string,
                                                           'post_aggregation_key': slice.instantaneous_aggregation.post_aggregation_key,
                                                           'post_aggregations': post_aggregations_string,
                                                           'data_key': slice.instantaneous_aggregation.data_key,
                                                           'default_data_key': slice.instantaneous_aggregation.default_column_name
                                                           }

                # fetch monthly aggregation
                aggregations_string = slice.monthly_aggregation.aggregations
                #aggregations_string = aggregations_string.replace("%s", column_name)
                #post_aggregations_string = slice.monthly_aggregation.post_aggregations
                #post_aggregations_string = eval(post_aggregations_string.replace("%s", column_name)) if post_aggregations_string.replace("%s", column_name) else ''
                slice_dict['monthly_aggregation'] = {'name': slice.monthly_aggregation.name,
                                                     'aggregation_key': slice.monthly_aggregation.aggregation_key,
                                                     'aggregations': aggregations_string,
                                                     'post_aggregation_key': slice.monthly_aggregation.post_aggregation_key,
                                                     'post_aggregations': post_aggregations_string,
                                                     'data_key': slice.monthly_aggregation.data_key,
                                                     'default_data_key': slice.monthly_aggregation.default_column_name
                                                     }

                slice_dict['instantaneous_minutes'] = slice.instantaneous_minutes
                #having clause append
                slice_dict['having'] = slice.having_clauses.values('having_clause', 'having_clause_key')
                #ppa multiplier
                slice_dict['ppa_multiplier'] = slice.ppa_multiplier
                #multiplier
                slice_dict['multiplier'] = slice.multiplier
                # assignment of each slice
                if slice.parent_slice:
                    if slice.parent_slice_id in self.others_params:
                        self.others_params[slice.parent_slice_id]['child'] = {}
                        self.others_params[slice.parent_slice_id]['child'][slice.id] = slice_dict
                    else:
                        self.others_params[slice.parent_slice_id] = {}
                        self.others_params[slice.parent_slice_id]['child'] = {}
                        self.others_params[slice.parent_slice_id]['child'][slice.id] = slice_dict
                else:
                    self.others_params[slice.id] = slice_dict

        else:
            pass

    def convert_to_query(self, granularity, intervals, aggregation_type, plants, other_params):
        """
        this function will build the query dict as below

        {1007L: {'dimensions': ['plant_slug'], 'aggregations': {'sum_value': {'fieldName': 'last_minus_first', 'type':
        'doubleSum'}}, 'intervals': '2018-04-01/2018-05-31', 'datasource': {'query': {'dimensions': ['plant_slug',
        'source_key'], 'aggregations': [{'fieldName': 'stream_value', 'type': 'doubleFirst', 'name': 'first_value'},
        {'fieldName': 'stream_value', 'type': 'doubleLast', 'name': 'last_value'}], 'filter': {'fields': [{'values':
        ['omya'], 'type': 'in', 'dimension': 'plant_slug'}, {'values': [u'DAILY_YIELD'], 'type': 'in', 'dimension':
        'stream_name'}, {'values': [u'INVERTER'], 'type': 'in', 'dimension': 'device_type'}, {'values': [u'wXEKRHbH3BorAu3',
         u'fxwl2d4P4ScOpVa', u'quio3ydk3Q0Cjg0', u'cAd0SgOQvwRGorz', u'8QJE1yLmC189nDZ', u'4Z3Rn17bk9Vneky',
         u'HorudEmakOb1pfY', u'NRe6EgD9FqLvO8O', u'WM3boKR2p7gmaN8', u'luBR9cQpW4JMEy9', u'GcVQmSJMLLjajmk',
         u'8IXAhvNUGH83KUm', u'muDf2k6B20ea2WB', u'dKSflRB6cnrZwWP', u'hHBXhImzipwbQ4p'], 'type': 'in', 'dimension':
         'source_key'}], 'type': 'and'}, 'intervals': '2018-04-01/2018-05-31', 'dataSource': 'dgc_prod_warehouse',
         {'granularity': {'origin': '2018-04-29T18:00:00Z', 'type': 'period', 'period': 'P1D'}},
         'postAggregations': [{'fields': [{'fieldName': 'last_value', 'type': 'hyperUniqueCardinality'},
         {'fieldName': 'first_value', 'type': 'hyperUniqueCardinality'}], 'type': 'arithmetic',
         'name': 'last_minus_first', 'fn': '-'}], 'queryType': 'groupBy'}, 'type': 'query'}, {'granularity': {'origin':
          '2018-04-29T18:00:00Z', 'type': 'period', 'period': 'P1D'}}}}


        :param granularity:
        :param intervals:
        :param aggregation_type:
        :param plants:
        :param other_params:
        :return:

        """
        for query_params in self.others_params:
            query_druid_params = {}
            having_clause_dict['havingSpecs'] = []
            query_druid_params['datasource'] = self.others_params[query_params]['data_source']
            last_data_key = "stream_value"
            if 'child' in self.others_params[query_params]:
                child_query_druid_params = DruidQueryConverter.child_subquery_execution(
                                                    self.others_params[query_params]['child'],
                                                    granularity, aggregation_type, intervals, plants, other_params)
                last_data_key = child_query_druid_params.pop('data_key')
                query_druid_params['datasource'] = client_query.sub_query(**child_query_druid_params)

            else:
                query_druid_params['datasource'] = self.others_params[query_params]['data_source']

            stream_name = []
            device_type = []
            # all query will have default dimensions as plant slug
            dimensions = ["plant_slug"]
            source_keys = []
            if self.others_params[query_params]['data_family'] == "PLANT":
                self.others_params[query_params]['capacity'] = \
                    dict(SolarPlant.objects.filter(slug__in=plants).values_list('slug', 'capacity'))


            if self.others_params[query_params]['data_family'] == "INVERTER":
                if other_params['inverters']:
                    source_keys.extend(other_params['inverters'])
                else:
                    source_keys.extend(list(IndependentInverter.objects.filter(plant__slug__in=plants).
                                            values_list('sourceKey', flat=True)))
                self.others_params[query_params]['capacity'] = \
                    dict(IndependentInverter.objects.filter(sourceKey__in=source_keys).values_list('sourceKey',
                                                                                              'total_capacity'))
                dimensions.append("source_key")

            if self.others_params[query_params]['data_family'] == "METER":
                if other_params['meters']:
                    source_keys.extend(other_params['meters'])
                else:
                    source_keys.extend(list(EnergyMeter.objects.filter(energy_calculation=True, plant__slug__in=plants).
                                            values_list('sourceKey', flat=True)))
                dimensions.append("source_key")

            if self.others_params[query_params]['data_family'] == "PLANTMETA":
                stream_type = self.others_params[query_params]['filter_stream_name']
                if other_params['weather_stations']:
                    stream_name.extend(other_params['weather_stations'])
                else:
                    stream_name.extend(list(IOSensorField.objects.filter(plant_meta__plant__slug__in=plants,
                                            stream_type=stream_type).values_list('solar_field__name', flat=True)))

                if self.others_params[query_params]['which_irradiation']:
                    stream_name = ['IRRADIATION']
                dimensions.append("stream_name")

            if other_params['solar_group']:
                dimensions.append("source_key")

            stream_name.append(self.others_params[query_params]['filter_stream_name'])
            device_type.append(self.others_params[query_params]['data_family'])
            dimensions.append(self.others_params[query_params]['dimension'])

            query_druid_params['granularity'] = granularity
            if self.others_params[query_params]['fixed_instantaneous_granularity']:
                query_druid_params['granularity'] = "fifteen_minute"
                having_clause_granularity = 'fifteen_minute'
            else:
                query_druid_params['granularity'] = copy.copy(granularity)
                having_clause_granularity = query_druid_params['granularity'].pop('default')

            # origin fix as interval date
            if self.others_params[query_params]['granularity_origin']:
                query_druid_params['granularity']['origin'] = other_params['raw_interval'].split("/")[0].split("T")[0]

            query_druid_params['intervals'] = intervals
            query_druid_params['dimensions'] = list(set(dimensions))

            if self.others_params[query_params]["%s" % aggregation_type]['aggregations']:
                query_druid_params['aggregations'] = self.others_params[query_params]["%s" % aggregation_type]['aggregations']
                #default_data_key = self.others_params[query_params]["%s" % aggregation_type]['default_data_key']
                query_druid_params['aggregations'] = eval(query_druid_params['aggregations'].replace("%s", last_data_key))

            if self.others_params[query_params]["%s" % aggregation_type]['post_aggregations']:
                query_druid_params['post_aggregations'] = self.others_params[query_params]["%s" % aggregation_type]['post_aggregations']
                #default_data_key = self.others_params[query_params]["%s" % aggregation_type]['default_data_key']
                query_druid_params['post_aggregations'] = eval(query_druid_params['post_aggregations'].replace("%s", last_data_key))

            if self.others_params[query_params]['having']:
                having_data_key = self.others_params[query_params]["%s" % aggregation_type]['data_key']
                query_level = self.others_params[query_params]['data_family']
                lower_bound, upper_bound,  = DruidQueryConverter.get_lower_or_upper_bounds(plants, "ENERGY",
                                                GRANULARITY_IN_NUMBER[having_clause_granularity], query_level)
                for having in self.others_params[query_params]['having']:
                    clause_dict = having['having_clause'].replace("%s", having_data_key)
                    #replace lower, upper bound
                    if "lower_bound" in clause_dict:
                        clause_dict = clause_dict.replace("lower_bound", "%s" % lower_bound)
                    if "upper_bound" in having['having_clause']:
                        clause_dict = clause_dict.replace("upper_bound", "%s" % upper_bound)
                    clause_dict = eval(clause_dict)
                    having_clause_dict['havingSpecs'].append(Having.build_having(Having(**clause_dict)))
                query_druid_params['having'] = Having(**having_clause_dict)

            # used for filter soiling loss data from different algo
            filter_column_name = []
            if self.others_params[query_params]['filter_column_name']:
                filter_column_name.append(self.others_params[query_params]['filter_column_name'])

            if query_druid_params['datasource'] == self.others_params[query_params]['data_source']:
                base_filter = [(Filter(type='in', dimension='plant_slug', values=plants)),
                                (Filter(type='in', dimension='stream_name', values=list(set(stream_name)))),
                                (Filter(type='in', dimension='device_type', values=list(set(device_type))))]
                if source_keys:
                    base_filter.append((Filter(type='in', dimension='source_key', values=list(set(source_keys)))))

                if(filter_column_name):
                    base_filter.append((Filter(type='in', dimension='model_name', values=list(set(filter_column_name)))))

                query_druid_params['filter'] = reduce(iand, base_filter)

            self.query_druid_params[query_params] = query_druid_params

    @staticmethod
    def child_subquery_execution(child_query_params, granularity, aggregation_type, intervals, plants, other_params):
        """
        this will return the query dict as datasource

        'datasource': {'query': {'dimensions': ['plant_slug', 'source_key'], 'aggregations':
        [{'fieldName': 'stream_value', 'type': 'doubleFirst', 'name': 'first_value'}, {'fieldName': 'stream_value',
        'type': 'doubleLast', 'name': 'last_value'}], 'filter': {'fields': [{'values': ['omya'], 'type': 'in',
        'dimension': 'plant_slug'}, {'values': [u'DAILY_YIELD'], 'type': 'in', 'dimension': 'stream_name'},
        {'values': [u'INVERTER'], 'type': 'in', 'dimension': 'device_type'}, {'values': [u'wXEKRHbH3BorAu3',
        u'fxwl2d4P4ScOpVa', u'quio3ydk3Q0Cjg0', u'cAd0SgOQvwRGorz', u'8QJE1yLmC189nDZ', u'4Z3Rn17bk9Vneky',
        u'HorudEmakOb1pfY', u'NRe6EgD9FqLvO8O', u'WM3boKR2p7gmaN8', u'luBR9cQpW4JMEy9', u'GcVQmSJMLLjajmk',
        u'8IXAhvNUGH83KUm', u'muDf2k6B20ea2WB', u'dKSflRB6cnrZwWP', u'hHBXhImzipwbQ4p'], 'type': 'in',
        'dimension': 'source_key'}], 'type': 'and'}, 'intervals': '2018-04-01/2018-05-31', 'dataSource':
        'dgc_prod_warehouse', {'granularity': {'origin': '2018-04-29T18:00:00Z', 'type': 'period', 'period': 'P1D'}},
         'postAggregations': [{'fields': [{'fieldName': 'last_value', 'type': 'hyperUniqueCardinality'},
         {'fieldName': 'first_value', 'type': 'hyperUniqueCardinality'}], 'type': 'arithmetic', 'name':
         'last_minus_first', 'fn': '-'}], 'queryType': 'groupBy'}

        :param child_query_params:
        :param granularity:
        :param aggregation_type:
        :param intervals:
        :param plants:
        :param other_params:
        :return:
        """
        query_druid_params = {}
        having_clause_dict['havingSpecs'] = []
        #plant = SolarPlant.objects.filter(slug=plants)
        for query_params in child_query_params:
            if 'child' in child_query_params[query_params]:
                query_druid_params['datasource'] = DruidQueryConverter.child_subquery_execution(
                                                        child_query_params[query_params]['child'], granularity,
                                                        aggregation_type, intervals, plants, other_params)
            else:
                query_druid_params['datasource'] = child_query_params[query_params]['data_source']
            stream_name = []
            device_type = []
            # all query will have default dimensions as plant slug
            dimensions = ["plant_slug"]
            source_keys = []

            if child_query_params[query_params]['data_family'] == "INVERTER":
                if other_params['inverters']:
                    source_keys.extend(other_params['inverters'])
                else:
                    source_keys.extend(list(IndependentInverter.objects.filter(plant__slug__in=plants).
                                            values_list('sourceKey', flat=True)))
                dimensions.append("source_key")

            if child_query_params[query_params]['data_family'] == "METER":
                if other_params['meters']:
                    source_keys.extend(other_params['meters'])
                else:
                    source_keys.extend(list(EnergyMeter.objects.filter(energy_calculation=True, plant__slug__in=plants).
                                            values_list('sourceKey', flat=True)))
                dimensions.append("source_key")

            if child_query_params[query_params]['data_family'] == "PLANTMETA":
                stream_type = child_query_params[query_params]['filter_stream_name']
                if other_params['weather_stations']:
                    stream_name.extend(other_params['weather_stations'])
                else:
                    stream_name.extend(list(IOSensorField.objects.filter(plant_meta__plant__slug__in=plants,
                                            stream_type=stream_type).values_list('solar_field__name', flat=True)))
                if child_query_params[query_params]['which_irradiation']:
                    stream_name = ['IRRADIATION']
                dimensions.append("stream_name")

            stream_name.append(child_query_params[query_params]['filter_stream_name'])
            device_type.append(child_query_params[query_params]['data_family'])
            dimensions.append(child_query_params[query_params]['dimension'])

            query_druid_params['granularity'] = granularity
            if child_query_params[query_params]['fixed_instantaneous_granularity']:
                 query_druid_params['granularity'] = "fifteen_minute"
                 having_clause_granularity = 'fifteen_minute'
            else:
                query_druid_params['granularity'] = copy.copy(granularity)
                having_clause_granularity = query_druid_params['granularity'].pop('default')

            # origin fix as interval date
            if child_query_params[query_params]['granularity_origin']:
                query_druid_params['granularity']['origin'] = other_params['raw_interval'].split("/")[0].split("T")[0]

            query_druid_params['intervals'] = intervals
            query_druid_params['dimensions'] = list(set(dimensions))

            if child_query_params[query_params]["%s" % aggregation_type]['aggregations']:
                query_druid_params['aggregations'] = child_query_params[query_params]["%s" % aggregation_type]['aggregations']
                default_data_key = child_query_params[query_params]["%s" % aggregation_type]['default_data_key']
                query_druid_params['aggregations'] = eval(query_druid_params['aggregations'].replace("%s", default_data_key))

            query_druid_params['data_key'] = child_query_params[query_params]["%s" % aggregation_type]['data_key']

            if child_query_params[query_params]["%s" % aggregation_type]['post_aggregations']:
                query_druid_params['post_aggregations'] = child_query_params[query_params]["%s" % aggregation_type]['post_aggregations']
                default_data_key = child_query_params[query_params]["%s" % aggregation_type]['default_data_key']
                query_druid_params['post_aggregations'] = eval(query_druid_params['post_aggregations'].replace("%s", default_data_key))

            #having query only work with outer data
            if child_query_params[query_params]['having']:
                having_data_key = child_query_params[query_params]["%s" % aggregation_type]['data_key']
                query_level = child_query_params[query_params]['data_family']
                lower_bound, upper_bound,  = DruidQueryConverter.get_lower_or_upper_bounds(plants, "ENERGY",
                                                GRANULARITY_IN_NUMBER[having_clause_granularity], query_level)
                for having in child_query_params[query_params]['having']:
                    clause_dict = having['having_clause'].replace("%s", having_data_key)
                    #replace lower, upper bound
                    if "lower_bound" in clause_dict:
                        clause_dict = clause_dict.replace("lower_bound", "%s" % lower_bound)
                    if "upper_bound" in having['having_clause']:
                        clause_dict = clause_dict.replace("upper_bound", "%s" % upper_bound)
                    clause_dict = eval(clause_dict)
                    having_clause_dict['havingSpecs'].append(Having.build_having(Having(**clause_dict)))
                query_druid_params['having'] = Having(**having_clause_dict)

            # used for filter soiling loss data from different algo
            filter_column_name = []
            if child_query_params[query_params]['filter_column_name']:
                filter_column_name.append(child_query_params[query_params]['filter_column_name'])

            base_filter = [(Filter(type='in', dimension='plant_slug', values=plants)),
                            (Filter(type='in', dimension='stream_name', values=list(set(stream_name)))),
                            (Filter(type='in', dimension='device_type', values=list(set(device_type))))]
            if source_keys:
                base_filter.append((Filter(type='in', dimension='source_key', values=list(set(source_keys)))))

            if filter_column_name:
                base_filter.append((Filter(type='in', dimension='model_name', values=list(set(filter_column_name)))))

            query_druid_params['filter'] = reduce(iand, base_filter)

            return query_druid_params

    @staticmethod
    def get_lower_or_upper_bounds(plant_or_sources, query_type, granularity, query_level):
        """

        :param query_type:
        :param granularity:
        :param query_level:
        :return:
        """
        if query_type == "PR":
            return 0, 100
        elif query_type == "CUF":
            return 0, 25
        elif query_type == "SY":
            return 0, 10
        elif query_type == "ENERGY":
            if query_level == "PLANT" or query_level == "METER":
                max_capacity = SolarPlant.objects.filter(slug__in=plant_or_sources).aggregate(Max('capacity'))[
                    'capacity__max']
                if max_capacity is not None:
                    return 0, max_capacity * float(granularity) / 60.0
                else:
                    return 0, 0
            elif query_level == "INVERTER":
                max_capacity = \
                    IndependentInverter.objects.filter(plant__slug__in=plant_or_sources).aggregate(
                        Max('total_capacity'))[
                        'total_capacity__max']
                if max_capacity is not None:
                    return 0, max_capacity * float(granularity) / 60.0
                else:
                    return 0, 0
        return 0, 0


def ppa_multiplier_define(df, plant_contract):
    """

    :param df:
    :param value:
    :return:
    """
    for contract in plant_contract.get("%s" % df.plant_slug, []):
        if contract['start_date'] <= datetime.fromtimestamp(df.timestamp/1000).date() <= contract['end_date']:
            return df.sum_value * float(contract['ppa_price'])
    return df.sum_value * 1

def fetch_data_from_druid(granularity, interval, plants, analysis_id, other_options):
    """

    :param granularity:
    :param interval:
    :param plants:
    :param analysis_id:
    :param other_options:
    :return:
    """
    lv_druid_query = DruidQueryConverter()
    lv_druid_query.fetch_query_dataset(int(analysis_id))
    group_source_mapping = {}
    group_capacity_mapping = {}
    if other_options['solar_group']:
        inverter_source = dict(SolarGroup.objects.filter(plant__slug__in=plants,
                                                                   id__in=other_options['solar_group']).
                                  values_list('groupIndependentInverters__sourceKey', 'name'))
        other_options['inverters'] =  inverter_source.keys()
        group_source_mapping.update(inverter_source)
        meter_source = dict(SolarGroup.objects.filter(plant__slug__in=plants,
                                                                   id__in=other_options['solar_group']).
                                  values_list('groupEnergyMeters__sourceKey', 'name'))
        other_options['meters'] = meter_source.keys()
        group_source_mapping.update(meter_source)

        group_capacity_mapping = dict(SolarGroup.objects.filter(plant__slug__in=plants,
                                                   id__in=other_options['solar_group']).annotate(
            sum_capacity=Sum('groupIndependentInverters__total_capacity')).values_list('name', 'sum_capacity'))

    # define granularity dict
    common_timezone = list(set(SolarPlant.objects.filter(slug__in=plants).
                               values_list('metadata__dataTimezone', flat=True)))
    granuality_dict['period'] = GRANULARITY_PERIOD[granularity]
    interval_startdatetime = datetime.strptime(interval.split("/")[0], "%Y-%m-%d")
    interval_enddatetime = datetime.strptime(interval.split("/")[1], "%Y-%m-%d")
    if len(common_timezone) == 1:
        tz = pytz.timezone(common_timezone[0])
        interval_startdatetime = tz.localize(interval_startdatetime)
        interval_startdatetime = interval_startdatetime.astimezone(pytz.utc)
        interval_enddatetime = tz.localize(interval_enddatetime)
        interval_enddatetime = interval_enddatetime.astimezone(pytz.utc)
    granuality_dict['origin'] = (interval_startdatetime).strftime("%Y-%m-%dT%H:%M:%SZ")
    interval = "%s/%s" %(interval_startdatetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                         interval_enddatetime.strftime("%Y-%m-%dT%H:%M:%SZ"))
    granuality_dict['default'] = granularity
    # lv_druid_query.others_params
    lv_druid_query.convert_to_query(granuality_dict, interval, GRANULARITY["%s" % granularity], plants, other_options)
    # lv_druid_query.query_druid_params
    query_output = []
    merge_output = pd.DataFrame()
    slice_ids = []
    for slice in lv_druid_query.query_druid_params:
        group = client_query.groupby(**lv_druid_query.query_druid_params[slice])
        df = group.export_pandas()
        if df is None:
            continue
        # done for javascript epoce time
        df['timestamp'] = pd.to_datetime(df['timestamp']).astype(np.int64) // 10 ** 9
        df['timestamp'] = df['timestamp']*1000
        sliced_data = {}
        sliced_data['css_options'] = lv_druid_query.others_params[slice]['css_options']
        sliced_data['name'] = lv_druid_query.others_params[slice]['name']
        sliced_data['unit'] = lv_druid_query.others_params[slice]['data_unit']

        query_id = lv_druid_query.others_params[slice]['query_id']
        data_key = lv_druid_query.others_params[slice][GRANULARITY["%s" % granularity]]['data_key']

        if 'source_key' in df.columns.values.tolist() and not other_options['solar_group']:
            name_of_source = dict(Sensor.objects.filter(sourceKey__in=set(df['source_key'])).
                                  values_list('sourceKey', 'name'))
            df['source_name'] = df['source_key'].apply(lambda x: name_of_source[x])
            # run only when it is normalized
            if lv_druid_query.others_params[slice]['normalized']:
                source_capacity = lv_druid_query.others_params[slice]['capacity']
                df['capacity'] = df['source_key'].apply(lambda x: source_capacity[x])
                df['%s' % data_key] = df['%s' % data_key] / df['capacity']
            sliced_data['data'] = dict(df.groupby('source_name')[['timestamp', '%s' % data_key]].apply(lambda x: x.to_dict('split')))
            query_output.append(sliced_data)

        elif 'stream_name' in df.columns.values.tolist():
            df['plant_slug_stream_name'] = df['plant_slug'] + df['stream_name']
            sliced_data['data'] = dict(df.groupby(['plant_slug_stream_name'])[['timestamp', '%s' % data_key]].apply(lambda x: x.to_dict('split')))
            query_output.append(sliced_data)

        elif lv_druid_query.data_analysis_dict['operation_text']:
            plant_or_group = "plant_slug"
            source_capacity = lv_druid_query.others_params[slice]['capacity']
            if other_options['solar_group']:
                source_capacity = group_capacity_mapping
                plant_or_group = "group_name"
                df['group_name'] = df['source_key'].apply(lambda x: group_source_mapping[x])
                df = (df.groupby(['group_name', 'timestamp']).sum().reset_index())

            # run only when it is normalized
            if lv_druid_query.others_params[slice]['normalized']:
                df['capacity'] = df['%s' % plant_or_group].apply(lambda x: source_capacity[x])
                df['%s' % data_key] = df['%s' % data_key] / df['capacity']

            df = df[['%s' % plant_or_group, 'timestamp', '%s' % data_key]]
            sliced_data['data'] = df.rename(columns={'%s' % data_key: '%s' % sliced_data['name']})
            df = df.rename(columns={'%s' % data_key: 'slice%s' % (query_id)})
            slice_ids.append("slice%s" % query_id)
            query_output.append(sliced_data)
            if merge_output.empty:
                merge_output = df
            else:
                if set(group_source_mapping.values()):
                    df2 = pd.DataFrame()
                    for gp in set(group_source_mapping.values()):
                        df['%s' % plant_or_group] = gp
                        df2 = df2.append(df)
                    df = df2
                merge_output = merge_output.merge(df, how='inner', on=['timestamp', '%s' % plant_or_group])

        else:
            if other_options['solar_group']:
                df['group_name'] = df['source_key'].apply(lambda x: group_source_mapping[x])
                df1 = (df.groupby(['group_name', 'timestamp']).sum().reset_index())
                # run only when it is normalized
                if lv_druid_query.others_params[slice]['normalized']:
                    df1['capacity'] = df1['group_name'].apply(lambda x: group_capacity_mapping[x])
                    df1['%s' % data_key] = df1['%s' % data_key] / df1['capacity']
                # for insolation query
                if lv_druid_query.others_params[slice]['multiplier']:
                    df1['%s' % data_key] = df1['%s' % data_key] * lv_druid_query.others_params[slice]['multiplier']
                sliced_data['data'] = dict(df1.groupby('group_name')[['timestamp', '%s' % data_key]].apply(lambda x: x.to_dict('split')))
            else:
                # run only when it is normalized
                if lv_druid_query.others_params[slice]['normalized']:
                    source_capacity = lv_druid_query.others_params[slice]['capacity']
                    df['capacity'] = df['plant_slug'].apply(lambda x: source_capacity[x])
                    df['%s' % data_key] = df['%s' % data_key] / df['capacity']
                # for insolation query
                if lv_druid_query.others_params[slice]['multiplier']:
                    df['%s' % data_key] = df['%s' % data_key] * lv_druid_query.others_params[slice]['multiplier']
                # ppa pricing only work for plants
                if lv_druid_query.others_params[slice]['ppa_multiplier']:
                    contract_dict = get_ppa_price(plants, interval_startdatetime, interval_enddatetime)
                    df['sum_value'] = df.apply(lambda row: ppa_multiplier_define(row, contract_dict), axis=1)
                sliced_data['data'] = dict(df.groupby('plant_slug')[['timestamp', '%s' % data_key]].apply(lambda x: x.to_dict('split')))
            query_output.append(sliced_data)

    if lv_druid_query.data_analysis_dict['operation_text']:
        equation = lv_druid_query.data_analysis_dict['operation_text']
        analysis_name = lv_druid_query.data_analysis_dict['analysis_name']
        analysis_unit = lv_druid_query.data_analysis_dict['analysis_unit']
        mo = merge_output.eval(equation)
        merge_output1 = pd.concat((merge_output, mo.rename(analysis_name)), axis=1)
        for sid in slice_ids:
            merge_output1.drop('%s' % sid, axis=1, inplace=True)
        query_output1 = {}
        query_output1['css_options'] = query_output[0]['css_options']
        query_output1['unit'] = query_output[0]['unit']
        query_output1['data'] = {}
        if other_options['solar_group']:
            query_output1['data'] = dict(merge_output1.groupby('group_name')[['timestamp', '%s' % analysis_name]].apply(
                lambda x: x.to_dict('split')))
        else:
            query_output1['data'] = dict(merge_output1.groupby('plant_slug')[['timestamp', '%s' % analysis_name]].apply(lambda x: x.to_dict('split')))
        query_output1['name'] = analysis_name
        query_output1['unit'] = analysis_unit
        query_output = list()
        query_output.append(query_output1)
    del lv_druid_query
    return query_output

