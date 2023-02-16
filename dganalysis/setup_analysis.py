

# dashboard, data_family, display_name, filter_stream_name, dimension
query_options = [
    # Availability, Grid availability
    (1, 'solar', 'plant', "Availability", "AVAILABILITY", "source_key", "%"),
    (3, 'solar', 'plant', "Grid Availability", "GRID_AVAILABILITY", "source_key", "%"),
    (4, 'solar', 'plantmeta', "Irradiance", "IRRADIATION", "source_key", "kW/m2"),
    (5, 'solar', 'plantmeta', "Irradiance - 2", "IRRADIATION_2", "source_key", "kW/m2"),
    (6, 'solar', 'plantmeta', "Irradiance - 3", "IRRADIATION_3", "source_key", "kW/m2"),
    (7, 'solar', 'plantmeta', "Irradiance - 4", "IRRADIATION_4", "source_key", "kW/m2"),
    (2, 'solar', 'inverter', "Availability", "AVAILABILITY", "source_key", "%"),
    (8, 'solar', 'inverter', "Total Operating Time", "TOTAL_OPERATIONAL_HOURS", "source_key", "s"),
    (9, 'solar', 'inverter', "Daily Operating Time", "DAILY_OPERATIONAL_HOURS", "source_key", "s"),
    (10, 'solar', 'inverter', "Active Power", "ACTIVE_POWER", "source_key", "kW"),
    (11, 'solar', 'inverter', "DC Power", "DC_POWER", "source_key", "kW"),
    (12, 'solar', 'inverter', "Active Power - R", "ACTIVE_POWER_R", "source_key", "kW"),
    (13, 'solar', 'inverter', "Active Power - Y", "ACTIVE_POWER_Y", "source_key", "kW"),
    (14, 'solar', 'inverter', "Active Power - B", "ACTIVE_POWER_B", "source_key", "kW"),
    (15, 'solar', 'inverter', "Operational Status", "SOLAR_STATUS", "source_key", None),
    (16, 'solar', 'inverter', "AC Voltage R", "AC_VOLTAGE_R", "source_key", "V"),
    (17, 'solar', 'inverter', "AC Voltage Y", "AC_VOLTAGE_Y", "source_key", "V"),
    (18, 'solar', 'inverter', "AC Voltage B", "AC_VOLTAGE_B", "source_key", "V"),
    (19, 'solar', 'inverter', "Current R", "CURRENT_R", "source_key", "A"),
    (20, 'solar', 'inverter', "Current Y", "CURRENT_Y", "source_key", "A"),
    (21, 'solar', 'inverter', "Current B", "CURRENT_B", "source_key", "A"),
    (22, 'solar', 'inverter', "AC Frequency R", "AC_FREQUENCY_R", "source_key", "Hz"),
    (23, 'solar', 'inverter', "AC Frequency Y", "AC_FREQUENCY_Y", "source_key", "Hz"),
    (24, 'solar', 'inverter', "AC Frequency B", "AC_FREQUENCY_B", "source_key", "Hz"),
    (25, 'solar', 'inverter', "MPPT-1 DC Voltage", "MPPT1_DC_VOLTAGE", "source_key", "V"),
    (26, 'solar', 'inverter', "MPPT-1 DC Current", "MPPT1_DC_CURRENT", "source_key", "A"),
    (27, 'solar', 'inverter', "MPPT-1 DC Power", "MPPT1_DC_POWER", "source_key", "kW"),
    (28, 'solar', 'inverter', "MPPT-2 DC Voltage", "MPPT2_DC_VOLTAGE", "source_key", "V"),
    (29, 'solar', 'inverter', "MPPT-2 DC Current", "MPPT2_DC_CURRENT", "source_key", "A"),
    (30, 'solar', 'inverter', "MPPT-2 DC Power", "MPPT2_DC_POWER", "source_key", "kW"),
    (31, 'solar', 'inverter', "MPPT-3 DC Voltage", "MPPT3_DC_VOLTAGE", "source_key", "V"),
    (32, 'solar', 'inverter', "MPPT-3 DC Current", "MPPT3_DC_CURRENT", "source_key", "A"),
    (33, 'solar', 'inverter', "MPPT-3 DC Power", "MPPT3_DC_POWER", "source_key", "kW"),
    (34, 'solar', 'inverter', "MPPT-4 DC Voltage", "MPPT4_DC_VOLTAGE", "source_key", "V"),
    (35, 'solar', 'inverter', "MPPT-4 DC Current", "MPPT4_DC_CURRENT", "source_key", "A"),
    (36, 'solar', 'inverter', "MPPT-4 DC Power", "MPPT4_DC_POWER", "source_key", "kW"),
    (37, 'solar', 'plantmeta', "Module Temperature", "MODULE_TEMPERATURE", "source_key", "C"),
    (38, 'solar', 'plantmeta', "Module Temperature - 2", "MODULE_TEMPERATURE_2", "source_key", "C"),
    (39, 'solar', 'plantmeta', "Module Temperature - 3", "MODULE_TEMPERATURE_3", "source_key", "C"),
    (40, 'solar', 'plantmeta', "Module Temperature - 4", "MODULE_TEMPERATURE_4", "source_key", "C"),
    (41, 'solar', 'plantmeta', "Ambient Temperature", "AMBIENT_TEMPERATURE", "source_key", "C"),
    (42, 'solar', 'plantmeta', "Ambient Temperature - 2", "AMBIENT_TEMPERATURE_2", "source_key", "C"),
    (43, 'solar', 'plantmeta', "Ambient Temperature - 3", "AMBIENT_TEMPERATURE_3", "source_key", "C"),
    (44, 'solar', 'plantmeta', "Ambient Temperature - 4", "AMBIENT_TEMPERATURE_4", "source_key", "C"),
    (45, 'solar', 'plantmeta', "Windspeed", "WINDSPEED", "source_key", "km/hr"),
    (46, 'solar', 'plantmeta', "Wind Direction", "WIND_DIRECTION", "source_key", None),
    (47, 'solar', 'plant', "Plant Generation - Processed", "PLANT_GENERATION", "source_key", "kWh"),
    (48, 'solar', 'plant', "Forecasted Generation", "PLANT_PREDICTED_GENERATION", "source_key", "kWh"),
    (49, 'solar', 'plant', "PVSyst Generation", "PVSYST_GENERATION", "source_key", "kWh"),
    (50, 'solar', 'meter', "Meter - Imported", "Wh_RECEIVED", "source_key", "kWh"),
    (51, 'solar', 'meter', "Meter - Exported", "Wh_DELIVERED", "source_key", "kWh"),
    (53, 'solar', 'inverter', "Inverter - Daily Generation", "DAILY_YIELD", "source_key", "kWh"),
    (54, 'solar', 'plant', "Performance Ratio", "PR", "source_key", "%"),
    (55, 'solar', 'inverter', "Performance Ratio", "PR", "source_key", "%"),
    (56, 'solar', 'plant', "Specific Yield", "SY", "source_key", None),
    (57, 'solar', 'inverter', "Specific Yield", "SY", "source_key", None),
    (58, 'solar', 'plant', "CUF", "CUF", "source_key", "%"),
    (59, 'solar', 'inverter', "CUF", "CUF", "source_key", "%"),
    (60, 'solar', 'plantmeta', "Insolation", "INSOLATION", "source_key", "kW/m2"),
    (61, 'solar', 'plant', "PVSyst PR", "PVSYST_PR", "source_key", "kWh"),

    (52, 'solar', 'inverter', "Inverter - Total Generation", "TOTAL_YIELD", "source_key", "kWh"),

    (62, 'solar', 'plant', "Plant Generation (Inverters)", "TOTAL_YIELD", "plant_slug", "kWh"),
    (63, 'solar', 'plant', "Plant Generation (Energy Meters)", "Wh_RECEIVED", "plant_slug", "kWh"),

]

# name, aggregations, aggregation_key, post_aggregations, post_aggregation_key
aggregation_functions = [
 (1, u'Values Sum', u'{"sum_value": doublesum("%s")}', u'sum_value', u'', u'',
  'sum_value', 'stream_value'),
 (2, u'Maximum Value', u'"max_value": doublemax("%s")}', u'max_value', u'', u'',
  'max_value', 'stream_value'),
 (3, u'Minimum Value', u'{"min_value": doublemin("%s")}', u'min_value', u'', u'',
  'min_value', 'stream_value'),
 (4, u'First Value of the period',
  u'{"first_value": doublefirst("%s")}', u'first_value', u'', u'',
  'first_value','stream_value'),
 (5, u'Last Value of the period',
  u'{"last_value": doublelast("%s")}',
  u'last_value',
  u'',
  u'',
  'last_value',
  'stream_value'),
 (6, u'(Last-First) Value of the period',
  u'{"first_value": doublefirst("%s"), "last_value": doublelast("%s")}',
  u'first_value, last_value',
  u"{'last_minus_first': (HyperUniqueCardinality('last_value') - HyperUniqueCardinality('first_value'))}",
  u'last_minus_first',
  'last_minus_first',
  'stream_value'),
 (7, u'Count',
  u'{"count_value": count("%s")}',
  u'count_value',
  u'',
  u'',
  'count_value',
  'stream_value'),
 (8, u'Average Value',
  u'{"avg_sum_value": doublesum("%s"), "avg_count_value": count("%s")}',
  u'avg_sum_value, avg_count_value',
  u'{"avg_value": (Field("avg_count_value") / Field("avg_sum_value"))}',
  u'avg_value',
  'avg_value',
  'stream_value'),
]


pandas_functions = [
    (1, 'Add', '+'),
    (2, 'Subtract', '-'),
    (3, 'Multiplication', '*'),
    (4, 'Division', '/')
]
# category, name, description, query_options, instantaneous_aggregation,
# daily_aggregation, monthly_aggregation
system_analysis = [
    # Energy Export
    ("Energy Export", "Plant Generation", "Plant Generation", [(47, 1, 1, 1, 'column'),]),
    ("Energy Export", "Plant Generation Vs Forecasted", "Plant Generation Vs Forecasted", [(47, 1, 1, 1, 'column'),
                                                                                           (48, 1, 1, 1, 'spline')]),
    ("Energy Export", "Plant Generation Vs PVSyst", "Plant Generation Vs PVSyst", [(47, 1, 1, 1, 'column'),
                                                                                   (49, 1, 1, 1, 'spline')]),

    # Performance Indicators
    ("Performance Indicators", "Performance Ratio (PR)", "Performance Ratio (PR)", [(54, 8, 8, 8, 'column')]),
    ("Performance Indicators", "Specific Yield Vs. CUF", "Specific Yield Vs. CUF", [(56, 8, 8, 8, 'column'),
                                                                                    (58, 8, 8, 8, 'spline')]),
    ("Performance Indicators", "Generation Vs. Insolation", "Generation Vs. Insolation", [(47, 1, 1, 1, 'column'),
                                                                                          (60, 1, 1, 1, 'spline')]),
    ("Performance Indicators", "PR vs. Insolation vs. Avg. Module Temp.",
     "PR vs. Insolation vs. Avg. Module Temp.", [(47, 8, 8, 8, 'column'), (60, 1, 1, 1, 'spline'), (37, 8, 8, 8, 'spline'),
                                                 (38, 8, 8, 8, 'spline'), (39, 8, 8, 8, 'spline'), (40, 8, 8, 8, 'spline')]),
    ("Performance Indicators", "Plant Availability", "Plant Availability", [(1, 8, 8, 8, 'column')]),
    ("Performance Indicators", "Grid Availability", "Grid Availability", [(3, 8, 8, 8, 'column')]),
    ("Performance Indicators", "PR (Operating Vs. Expected)", "PR (Operating Vs. Expected)", [(47, 8, 8, 8, 'column'),
                                                                                              (61, 8, 8, 8, 'spline')]),

    ("Performance Indicators", "(Meter - Inverter) Generation", "(Meter - Inverter) Generation", [(62, 1, 1, 1, 'column', [(52, 6, 6, 6, 'column')]),
                                                                                                  (63, 1, 1, 1, 'spline', [(50, 6, 6, 6, 'column')])], '62_slice/63_slice'),
    # Inverters
    ("Inverters", "Inverters Index Values", "Index Values", [(52, 5, 5, 5, 'spline')]),
    ("Inverters", "Inverters Generation (Total)", "Generation (Total)", [(52, 6, 6, 6, 'spline')]),
    ("Inverters", "Inverters Generation (Daily)", "Generation (Daily)", [(53, 6, 6, 6, 'spline')]),
    ("Inverters", "AC Power", "AC Power", [(10, 8, 8, 8, 'spline')]),
    ("Inverters", "Inverters Performance Ratio (PR)", "PR", [(55, 8, 8, 8, 'spline')]),
    ("Inverters", "Inverters Specific Yield Vs. CUF", "Specific Yield Vs. CUF", [(57, 8, 8, 8, 'column'),
                                                                       (59, 8, 8, 8, 'spline')]),
    ("Inverters", "Inverters Availability", "Availability", [(2, 8, 8, 8, 'spline')]),
    ("Inverters", "Operating Time Index", "Operating Time Index", [(8, 6, 6, 6, 'spline')]),
    ("Inverters", "Operating Hours (Daily)", "Operating Hours (Daily)", [(9, 6, 6, 6, 'spline')]),
    ("Inverters", "Operational Status", "Operational Status", [(15, 8, 8, 8, 'spline')]),
    ("Inverters", "MPPT Power", "MPPT Power", [(27, 8, 8, 8, 'spline'),
                                               (30, 8, 8, 8, 'spline'),
                                               (33, 8, 8, 8, 'spline'),
                                               (36, 8, 8, 8, 'spline')]),
    ("Inverters", "MPPT Current", "MPPT Current", [(26, 8, 8, 8, 'spline'),
                                               (29, 8, 8, 8, 'spline'),
                                               (32, 8, 8, 8, 'spline'),
                                               (35, 8, 8, 8, 'spline')]),
    ("Inverters", "MPPT Voltage", "MPPT Voltage", [(25, 8, 8, 8, 'spline'),
                                               (28, 8, 8, 8, 'spline'),
                                               (31, 8, 8, 8, 'spline'),
                                               (34, 8, 8, 8, 'spline')]),
    # ("Inverters", "Inverters Strings", "Inverters Operational Status", []),
    ("Inverters", "DC Power", "DC Power", [(11, 8, 8, 8, 'spline')]),
    ("Inverters", "Phase-wise AC Power", "Inverters Phase-wise AC Power", [(12, 8, 8, 8, 'spline'),
                                                                           (13, 8, 8, 8, 'spline'),
                                                                           (14, 8, 8, 8, 'spline')]),
    ("Inverters", "AC Voltage", "AC Voltage", [(16, 8, 8, 8, 'spline'),
                                               (17, 8, 8, 8, 'spline'),
                                               (18, 8, 8, 8, 'spline')]),
    ("Inverters", "AC Current", "AC Current", [(19, 8, 8, 8, 'spline'),
                                               (20, 8, 8, 8, 'spline'),
                                               (21, 8, 8, 8, 'spline')]),
    # ("Inverters", "Frequency", "Frequency", []),

    # Weather Parameters
    ("Weather Parameters", "Irradiance", "Irradiance", [(4, 8, 8, 8, 'spline'),
                                                        (5, 8, 8, 8, 'spline'),
                                                        (6, 8, 8, 8, 'spline'),
                                                        (7, 8, 8, 8, 'spline')]),
    ("Weather Parameters", "Ambient Temperature", "Ambient Temperature", [(41, 8, 8, 8, 'spline'),
                                                                          (42, 8, 8, 8, 'spline'),
                                                                          (43, 8, 8, 8, 'spline'),
                                                                          (44, 8, 8, 8, 'spline')]),
    ("Weather Parameters", "Module Temperature", "Module Temperature", [(37, 8, 8, 8, 'spline'),
                                                                        (38, 8, 8, 8, 'spline'),
                                                                        (39, 8, 8, 8, 'spline'),
                                                                        (40, 8, 8, 8, 'spline')]),
    ("Weather Parameters", "Windspeed", "Windspeed", [(45, 8, 8, 8, 'spline')]),

    # Meters
    ("Meters", "Index Values", "Index Values", [(50, 5, 5, 5, 'column')]),
    ("Meters", "Generation (Imported)", "Meter Generation (Imported)", [(50, 6, 6, 6, 'column')]),
    ("Meters", "Generation (Exported)", "Meter Generation (Exported)", [(51, 6, 6, 6, 'column')]),
]

from .models import QueryOption, AggregationFunction, DataAnalysis, DataSlice, CssTemplate
from dashboards.models import Dashboard

# def setup_pandas_functions():
#     PandasFunctions.objects.all().delete()
#     for func in pandas_functions:
#         pandas_func = PandasFunctions.objects.create(func_id=func[0],
#                                                      name=func[1],
#                                                      operation=func[2])
#         pandas_func.save()

def setup_query_options():
    QueryOption.objects.all().delete()
    for query in query_options:
        query_opt = QueryOption.objects.create(query_id=query[0],
                                               dashboard=Dashboard.objects.get(slug=query[1]),
                                               data_family=query[2].upper(),
                                               display_name=query[3],
                                               filter_stream_name=query[4],
                                               dimension=query[5],
                                               data_unit=query[6])



def setup_agg_functions():
    AggregationFunction.objects.all().delete()
    for af in aggregation_functions:
        agg_func = AggregationFunction.objects.create(function_id=af[0],
                                                      name=af[1],
                                                      aggregations=af[2],
                                                      aggregation_key=af[3],
                                                      post_aggregations=af[4],
                                                      post_aggregation_key=af[5],
                                                      data_key=af[6],
                                                      default_column_name=af[7])



def get_query_details(id):
    for entry in query_options:
        if entry[0] == id:
            return entry

def get_func_details(id):
    for entry in aggregation_functions:
        if entry[0] == id:
            return entry


from django.contrib.auth.models import User

# ("Performance Indicators", "(Meter - Inverter) Generation", "(Meter - Inverter) Generation",
# [(62, 1, 1, 1, 'column', [(52, 6, 6, 6, 'column')]),
# (63, 1, 1, 1, 'spline', [(50, 6, 6, 6, 'column')])], '62_slice/63_slice'),

def setup_analysis():
    user = User.objects.get(email="admin@dataglen.com")
    DataAnalysis.objects.filter(system_defined=True, created_by=user).delete()
    for analysis in system_analysis:
        analysis_obj = DataAnalysis.objects.create(category=analysis[0],
                                                   name=analysis[1],
                                                   description=analysis[2],
                                                   created_by=user,
                                                   system_defined=True,
                                                   admin_view=False,
                                                   operation_text=None if len(analysis) == 4 else analysis[4])

        for slice in analysis[3]:
            query_details = QueryOption.objects.get(query_id=slice[0])
            css = CssTemplate.objects.create(viz_type=slice[4])
            slice_obj = DataSlice.objects.create(analysis=analysis_obj,
                                                 name=query_details.display_name,
                                                 description=query_details.display_name,
                                                 query_options=query_details,
                                                 css_options=css,
                                                 instantaneous_aggregation=AggregationFunction.objects.get(function_id=slice[1]),
                                                 daily_aggregation=AggregationFunction.objects.get(function_id=slice[2]),
                                                 monthly_aggregation=AggregationFunction.objects.get(function_id=slice[3]),
                                                 parent_slice=None)
            slice_obj.save()
            if len(slice) == 6:
                child_slice = slice[5][0]
                child_query_details = QueryOption.objects.get(query_id=child_slice[0])
                css_child = CssTemplate.objects.create(viz_type=child_slice[4])
                child_slice_obj = DataSlice.objects.create(analysis=analysis_obj,
                                                           name=query_details.display_name,
                                                           description=query_details.display_name,
                                                           query_options=child_query_details,
                                                           css_options=css_child,
                                                           instantaneous_aggregation=AggregationFunction.objects.get(
                                                                 function_id=child_slice[1]),
                                                           daily_aggregation=AggregationFunction.objects.get(
                                                                 function_id=child_slice[2]),
                                                           monthly_aggregation=AggregationFunction.objects.get(
                                                                 function_id=child_slice[3]),
                                                           parent_slice=slice_obj)
                child_slice_obj.save()


from django.db import transaction


def setup_analysis_module():
    with transaction.atomic():
        setup_query_options()
        setup_agg_functions()
        setup_analysis()


def create_analysis_dict():
    """
    get all created analysis as backup
    :return:
    """
    system_analysis_2 = []
    for analysis in DataAnalysis.objects.all():
        #analysis dic1
        analysis_dict = {}
        analysis_dict['category'] = analysis.category
        analysis_dict['name'] = analysis.name
        analysis_dict['description'] = analysis.description
        analysis_dict['system_defined'] = analysis.system_defined
        analysis_dict['admin_view'] = analysis.admin_view
        analysis_dict['dg_client'] = analysis.dg_client
        analysis_dict['created_at'] = analysis.created_at
        analysis_dict['updated_at'] = analysis.updated_at
        analysis_dict['created_by'] = analysis.created_by
        analysis_dict['enable_admin_view'] = analysis.enable_admin_view
        analysis_dict['enable_client_view'] = analysis.enable_client_view
        analysis_dict['operation_text'] = analysis.operation_text
        #slice dict
        analysis_dict['slices1'] = {}
        for slice in analysis.slices.all():
            slice_dict = {}
            slice_dict['name'] = slice.name
            slice_dict['description'] = slice.description
            #query options
            query_options = {}
            query_options['query_id'] = slice.query_options.query_id
            query_options['dashboard'] = slice.query_options.dashboard
            query_options['data_family'] = slice.query_options.data_family
            query_options['display_name'] = slice.query_options.display_name
            query_options['filter_stream_name'] = slice.query_options.filter_stream_name
            query_options['dimension'] = slice.query_options.dimension
            query_options['data_unit'] = slice.query_options.data_unit
            slice_dict['query_options'] = query_options
            #css options
            slice_dict['css_options'] = slice.css_options.viz_type
            slice_dict['daily_aggregation'] = {'function_id': slice.daily_aggregation.function_id,
                                               'name': slice.daily_aggregation.name,
                                               'aggregation_key': slice.daily_aggregation.aggregation_key,
                                               'aggregations': slice.daily_aggregation.aggregations,
                                               'post_aggregation_key': slice.daily_aggregation.post_aggregation_key,
                                               'post_aggregations': slice.daily_aggregation.post_aggregations,
                                               'data_key': slice.daily_aggregation.data_key,
                                               'default_column_name': slice.daily_aggregation.default_column_name}
            slice_dict['instantaneous_aggregation'] = {'function_id': slice.daily_aggregation.function_id,
                                                       'name': slice.instantaneous_aggregation.name,
                                                       'aggregation_key': slice.instantaneous_aggregation.aggregation_key,
                                                       'aggregations': slice.instantaneous_aggregation.aggregations,
                                                       'post_aggregation_key': slice.instantaneous_aggregation.post_aggregation_key,
                                                       'post_aggregations': slice.instantaneous_aggregation.post_aggregations,
                                                       'data_key': slice.instantaneous_aggregation.data_key,
                                                       'default_column_name': slice.instantaneous_aggregation.default_column_name}
            slice_dict['monthly_aggregation'] = {'function_id': slice.daily_aggregation.function_id,
                                                 'name': slice.monthly_aggregation.name,
                                                 'aggregation_key': slice.monthly_aggregation.aggregation_key,
                                                 'aggregations': slice.monthly_aggregation.aggregations,
                                                 'post_aggregation_key': slice.monthly_aggregation.post_aggregation_key,
                                                 'post_aggregations': slice.monthly_aggregation.post_aggregations,
                                                 'data_key': slice.monthly_aggregation.data_key,
                                                 'default_column_name': slice.monthly_aggregation.default_column_name}
            slice_dict['instantaneous_minutes'] = slice.instantaneous_minutes
            if slice.parent_slice:
                if slice.parent_slice_id in analysis_dict['slices1']:
                    analysis_dict['slices1'][slice.parent_slice_id]['child'] = []
                    analysis_dict['slices1'][slice.parent_slice_id]['child'].append(slice_dict)
                else:
                    analysis_dict['slices1'][slice.parent_slice_id] = {}
                    analysis_dict['slices1'][slice.parent_slice_id]['child'] = []
                    analysis_dict['slices1'][slice.parent_slice_id]['child'].append(slice_dict)
            else:
                analysis_dict['slices1'][slice.id] = slice_dict

        slices_values = analysis_dict.pop('slices1')
        analysis_dict['slices'] = {}
        analysis_dict['slices'] = slices_values.values()
        system_analysis_2.append(analysis_dict)
    return system_analysis_2

