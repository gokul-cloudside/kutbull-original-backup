from django.db import models
from dashboards.models import Dashboard
from dashboards.models import DataglenClient
from django.contrib.auth.models import User
from solarrms.models import SolarPlant

charts_types = (
    ("line", "line"),
    ("column", "column"),
    ("spline", "spline"),
    ("area", "area"),
    ("event", "event"),
    ("boxplot", "boxplot"),
    ("histogram", "histogram"),
    ("scatter", "scatter"),
    ("heatmap", "heatmap"),
    ("geoheatmap", "geoheatmap"),
)


class CssTemplate(models.Model):
    css = models.TextField()
    viz_type = models.CharField(choices=charts_types, max_length=50)

    def __unicode__(self):
        return "%s %s %s" % (self.id, self.css, self.viz_type)


# TODO : Update as required by Prabhu/Lavanya
data_categories = (
    ("INVERTER", "Inverter"),
    ("METER", "Energy Meters"),
    ("PLANT", "Plants"),
    ("PLANTMETA", "Weather Parameters"),
    ("REVENUE", "Revenue")
)

dimensions_categories = (
    ("plant_slug", "plant_slug"),
    ("source_key", "source_key"),
    ("stream_name", "stream_name"),
)

data_units = (
    ("kWh/m2", "kWh/m2"),
    ("kW", "kW"),
    ("kWh", "kWh"),
    ("C", "C"),
    ("kW/m2", "kW/m2"),
    ("A", "A"),
    ("V", "V"),
    ("Hz", "Hz"),
    ("%", "%"),
    ("s", "s"),
    ("km/hr", "km/hr"),
    ("kWh/kWp", "kWh/kWp"),
    ("INR", "INR"),
    ("kg", "kg"),
    (" ", " "),
)


class QueryOption(models.Model):
    query_id = models.IntegerField(blank=False, null=False, unique=True, db_index=True)
    # enabled for which dashboard - solar to start with
    dashboard = models.ForeignKey(Dashboard, related_name="analysis_queries",
                                  related_query_name="analysis_queries")
    # While creating a new analysis, data_family and display_name will form an option
    data_family = models.CharField(max_length=100, choices=data_categories, blank=False, null=False)
    display_name = models.CharField(max_length=200, blank=False, null=False)

    # column model_name for several algorithms
    filter_column_name = models.CharField(max_length=200, blank=True, null=True, default=None)

    # for the selected option, this will be a part of the filter
    filter_stream_name = models.CharField(max_length=200, blank=False, null=False)

    # for the selected option, this will be a part of the dimension (if applicable)
    dimension = models.CharField(max_length=200, choices=dimensions_categories,
                                 blank=True, null=True, default=None)

    # unit of the returned data
    data_unit = models.CharField(max_length=200, choices=data_units,
                                 blank=True, null=True, default=None)

    # child query
    parent_query = models.ForeignKey("QueryOption", related_query_name="child_query",
                                     related_name="child_query", null=True, blank=True)

    # which type of query it is ENERGY, PR, CUF etc to filter data using having clause
    query_type = models.CharField(max_length=200, blank=True, null=True, default="ENERGY")

    def __unicode__(self):
        return "%s_%s_%s_%s" %(self.dashboard.__unicode__(), self.display_name,
                               self.filter_stream_name, self.dimension)

    class Meta:
        unique_together=(("dashboard", "data_family",
                          "filter_stream_name", "dimension", "data_unit"))

    # solar, plant, plant availability, None
    # solar, inverter, inverter availability, source_key
    # solar, inverter, Generation, TOTAL_YIELD, source_key
    # solar, inverter, Active Power, ACTIVE_POWER, source_key
    # solar, plant, Generation, TOTAL_YIELD, None


analysis_categories = (
    ("Energy Export", "Energy Export"),
    ("Performance Indicators", "Performance Indicators"),
    ("Inverters", "Inverters"),
    ("Meters", "Meters"),
    ("Revenue", "Revenue"),
    ("Weather Parameters", "Weather Parameters"),
    ("Solar Custom", "Custom")
)

# class PandasFunctions(models.Model):
#     # name of the function
#     func_id = models.IntegerField(blank=False, null=False)
#     name = models.CharField(max_length=100, blank=False, null=False)
#     operation = models.CharField(max_length=100, blank=False, null=False)
#
#     def __unicode__(self):
#         return "_".join([self.name, str(self.operation)])
#


# Create your models here.
class DataAnalysis(models.Model):
    # category of the analysis
    category = models.CharField(choices=analysis_categories, max_length=100)
    # name of the analysis
    name = models.CharField(max_length=50, blank=False, null=False, unique=True)
    # a longer description
    description = models.CharField(max_length=500, blank=True, null=True)
    # system or user defined
    system_defined = models.BooleanField(default=True)
    # present to admin users of the org - has to be false for a system defined model
    admin_view = models.BooleanField(default=False)
    # dg client who created the analysis - cannot be null if system_defined is False
    dg_client = models.ForeignKey(DataglenClient, null=True, blank=True, related_name="data_analysis",
                                  related_query_name="data_analysis")
    # creation timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    # updated at
    updated_at = models.DateTimeField(auto_now=True)
    # created by
    created_by = models.ForeignKey(User, related_name="data_analysis",
                                   related_query_name="data_analysis")
    # enabled admin view (dgclient's admins)
    enable_admin_view = models.BooleanField(default=False)
    # enable customer view (client roles)
    enable_client_view = models.BooleanField(default=False)

    # final operation on slices TODO : Write validation function for this
    operation_text = models.CharField(max_length=5000, blank=True, null=True)
    # initialization granularity

    # TODO: for later usage additional users who have access to this analysis
    # users = models.ManyToManyField(User)
    # tags
    # plants
    # roles
    is_active = models.BooleanField(default=True)

    # analysis unit
    analysis_unit = models.CharField(max_length=200, choices=data_units, blank=True, null=True, default=None)

    def save(self, *args, **kwargs):
        # if it's a system defined model, the admin_view cannot be set to true
        if self.system_defined is True and self.admin_view is True:
            raise ValueError("It is a system defined module, the admin_view cannot be set to True")
        # if it's a system defined model, the dg_client cannot take a value
        elif self.system_defined is True and self.dg_client is not None:
            raise ValueError("It is a system defined module, dg_client has to be null")
        # if it's not a system defined model, the cannot be null
        elif self.system_defined is False and self.dg_client is None:
            raise ValueError("It is a user defined module, dg_client cannot to be null")
        super(DataAnalysis, self).save(*args, **kwargs)

    def __unicode__(self):
        return "_".join([self.category, self.name])


class HavingClause(models.Model):
    clause_id = models.IntegerField(blank=False, null=False, unique=True, db_index=True)
    # name of this clause
    name = models.CharField(max_length=100, blank=False, null=False, unique=True)
    # the selected having text
    having_clause = models.TextField(blank=True, null=True)
    # the output key(s)
    having_clause_key = models.CharField(blank=True, null=True, max_length=100)

    def __unicode__(self):
        return "_".join([self.name, str(self.having_clause),
                         str(self.having_clause_key)])


class AggregationFunction(models.Model):
    function_id = models.IntegerField(blank=False, null=False, unique=True, db_index=True)
    # name of this Function that the users will see - common across all dashboards
    name = models.CharField(max_length=100, blank=False, null=False)
    # the selected aggregation text
    aggregations = models.TextField(blank=True, null=True)
    # the output key(s) - "sum", "count" etc. that will be returned by pydruid [controlled by us]
    aggregation_key = models.CharField(blank=True, null=True, max_length=100)

    # the selected post aggregation text
    post_aggregations = models.TextField(blank=True, null=True)
    # the output key(s) - "sum", "count" etc. that will be returned by pydruid [controlled by us]
    post_aggregation_key = models.CharField(blank=True, null=True, max_length=100)
    # data key
    data_key = models.CharField(blank=False, null=False, max_length=100)
    # default column name to be queries
    default_column_name = models.CharField(blank=False, null=False, max_length=100)

    def __unicode__(self):
        return "_".join([self.name, str(self.aggregation_key),
                         str(self.post_aggregation_key)])

    class Meta:
        unique_together=(("name"), )


# one analysis will have multiple slices
class DataSlice(models.Model):
    # data source
    data_source = models.CharField(max_length=100, blank=False, null=False, default="dgc_prod_warehouse")
    # analysis name
    analysis = models.ForeignKey(DataAnalysis, related_name="slices",
                                 related_query_name="slices", null=True, blank=True, default=None)
    # name of the slice
    name = models.CharField(max_length=50, blank=True, null=True)
    # a longer description
    description = models.CharField(max_length=500, blank=True, null=True)
    # query options for the data
    query_options = models.ForeignKey(QueryOption, related_name="slices",
                                      related_query_name="slices")
    css_options = models.OneToOneField(CssTemplate, related_name="slice",
                                       related_query_name="slice")

    # fixed instantaneous granularity
    fixed_instantaneous_granularity = models.BooleanField(default=False)

    # instantaneous aggregation
    instantaneous_aggregation = models.ForeignKey(AggregationFunction,
                                                  related_name="instantaneous_slices",
                                                  related_query_name="instantaneous_slices")
    instantaneous_minutes = models.IntegerField(default=15, null=False, blank=False)

    # daily aggregation
    daily_aggregation = models.ForeignKey(AggregationFunction,
                                          related_name="daily_slices",
                                          related_query_name="daily_slices")

    # monthly aggregation
    monthly_aggregation = models.ForeignKey(AggregationFunction,
                                            related_name="monthly_slices",
                                            related_query_name="monthly_slices")

    # parent slice
    parent_slice = models.ForeignKey("DataSlice", related_query_name="child_slice",
                                     related_name="child_slice", null=True, blank=True, default=None)

    # having clauses
    having_clauses = models.ManyToManyField(HavingClause, related_name="slices",
                                            related_query_name="slices", null=True, blank=True)

    # normalized data
    normalized = models.BooleanField(default=False)

    # multiplication factor
    multiplier = models.FloatField(default=1.0)

    # which IRRADIATION to be consider like PR should be calculated with only IRRADIATION
    irradiation = models.CharField(max_length=100, blank=True, null=True, default="IRRADIATION")

    # fixed granuality origin, so if the data is not there druid query should not fail.
    granularity_origin = models.BooleanField(default=False)

    # ppa multiplier to be used or not
    ppa_multiplier = models.BooleanField(default=False)

    def __unicode__(self):
        return "_".join(["query_", self.analysis.__unicode__(), self.name])

    # def save(self, *args, **kwargs):
    #     if self.parent_slice:
    #         if len(self.parent_slice.child_slice.all()) > 0:
    #             raise ValueError("Only one child slice allowed")
    #     else:
    #         super(DataSlice, *args, **kwargs)


class AnalysisDashboard(models.Model):
    title = models.CharField(max_length=100, blank=False, null=False)
    created_by = models.ForeignKey(User, related_name="saved_dashboards",
                                   related_query_name="saved_dashboards")
    # creation timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    # updated at
    updated_at = models.DateTimeField(auto_now=True)
    editable_by_others = models.BooleanField(default=False, blank=True)
    enabled_for_admins = models.BooleanField(default=True, blank=True)
    css = models.OneToOneField(CssTemplate, related_name="dashboard",
                               related_query_name="dashboard")

    def __unicode__(self):
        return "_".join([self.title, str(self.created_by.username)])


class AnalysisConfiguration(models.Model):
    # saved analysis
    analysis = models.ForeignKey(DataAnalysis, related_name="saved_dashboards",
                                 related_query_name="saved_dashboards", null=False, blank=False)
    # dashboard
    dashboard = models.ForeignKey(AnalysisDashboard, related_name="analysis_configurations",
                                  related_query_name="analysis_configurations", null=False, blank=False)

    # plants enabled for this analysis
    plants = models.ManyToManyField(SolarPlant, related_name="saved_dashboards",
                                    related_query_name="saved_dashboards", null=False, blank=False)
    # data granularity (by default, data for the current day and this granularity will be displayed)
    granularity = models.CharField(max_length=100, default="hour", null=True)

    # for future use, not to be used as of now
    interval = models.CharField(max_length=100, default="live", null=True)

    # saved by which user
    created_by = models.ForeignKey(User, related_name="saved_dashboards_analysis",
                                   related_query_name="saved_dashboards_analysis")

    # positioning of the analysis
    col = models.IntegerField(blank=False, null=False)
    row = models.IntegerField(blank=False, null=False)
    size_x = models.IntegerField(blank=False, null=False)
    size_y = models.IntegerField(blank=False, null=False)

    css = models.OneToOneField(CssTemplate, related_name="analysis_configuration",
                               related_query_name="analysis_configuration", null=True, blank=True)

    def __unicode__(self):
        return "_".join(["saved_analysis_", self.analysis.__unicode__(), str(self.created_by.username)])









