from django.contrib import admin
from .models import CssTemplate, QueryOption, AggregationFunction, DataAnalysis, DataSlice, HavingClause, AnalysisConfiguration, AnalysisDashboard


# register css
admin.site.register(CssTemplate)
admin.site.register(DataSlice)
# register query option - both inline and separately
admin.site.register(QueryOption)
admin.site.register(HavingClause)


class QueryOptionInline(admin.TabularInline):
    model = QueryOption
    search_fields = ['data_family', 'display_name', 'filter_stream_name', 'dimension']

# register Aggregation Function - both inline and separately
admin.site.register(AggregationFunction)
class AggregationFunctionInline(admin.TabularInline):
    model = AggregationFunction
    search_fields = ['name', 'aggregations', 'post_aggregations']


class DataSliceInline(admin.TabularInline):
    model = DataSlice
    inlines = [QueryOptionInline, AggregationFunctionInline]


class DataAnalysisAdmin(admin.ModelAdmin):
    model = DataAnalysis
    inlines = [DataSliceInline]
    search_fields = ['category', 'name']


admin.site.register(DataAnalysis, DataAnalysisAdmin)


class AnalysisConfigurationInLine(admin.TabularInline):
    model = AnalysisConfiguration


class AnalysisDashboardAdmin(admin.ModelAdmin):
    model = AnalysisDashboard
    inlines = [AnalysisConfigurationInLine]

admin.site.register(AnalysisConfiguration)
admin.site.register(AnalysisDashboard, AnalysisDashboardAdmin)


