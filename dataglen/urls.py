from django.conf.urls import patterns, url

from dataglen import ui_views, charts_views
from rest_framework.urlpatterns import format_suffix_patterns
from django.views.generic import TemplateView

from dataglen import views
from django.core.urlresolvers import reverse_lazy
from dashboards.views import OrganizationEmployeeCreate, DataglenGroupCreate, GroupMemberCreate, \
    DataglenGroupUpdate

urlpatterns = patterns('',
                       url(r'dashboard/', views.DashboardData.as_view(), name='dashboard'),
                       url(r'policy/$', TemplateView.as_view(template_name="dataglen/pp.html"), name="privacy_policy"),

                       url(r'sources/', views.SourceListView.as_view(), name='source-list'),
                       url(r'source/(?P<source_key>[\w]+)/$', views.SourceData.as_view(), name="source-detail"),
                       url(r'source/(?P<source_key>[\w]+)/delete/$', views.SourceDeleteView.as_view(),
                           name="source-delete"),
                       url(r'source/(?P<source_key>[\w]+)/nebula/$', views.NebulaView.as_view(),
                           name="nebula-view"),
                       url(r'create/source/', views.SourceCreateView.as_view(), name="source-create"),
                       url(r'source/(?P<source_key>[\w]+)/(?P<stream_name>[\w]+)/$', views.StreamDeleteView.as_view(),
                           name="stream-delete"),
                       url(r'source/(?P<source_key>[\w]+)/update/(?P<stream_id>[\w]+)/$',
                           views.StreamUpdateView.as_view(),
                           name="stream-update"),
                       url(r'template/(?P<source_key>[\w]+)/$', views.ApplyTemplate.as_view(), name="apply_template"),
                       url(r'update/(?P<source_key>[\w]+)/$', views.SourceUpdateView.as_view(), name="source-update"),
                       url(r'monitoring/', views.MonitoringStatus.as_view(), name='monitoring_status'),
                       url(r'discarded/$', views.DiscardedRecordsStatsForSources.as_view(),
                           name="discarded-stats"),
                       url(r'discarded/(?P<source_key>[\w]+)/$', views.DiscardedRecordsForSource.as_view(),
                           name="discarded-source"),
                       url(r'data/$', views.SourcesList.as_view(), name="view-data"),
                       url(r'streams/create/(?P<source_key>[\w]+)/$', views.StreamCreateView.as_view(),
                           name="stream-create"),
                       url(r'profile', views.UserProfile.as_view(), name='user-profile'),

                       url(r'employees', OrganizationEmployeeCreate.as_view(template_name="dataglen/add_employee.html",
                                                                            success_url=reverse_lazy("dataglen:employee-add")),
                           name='employee-add'),
                       url(r'members', GroupMemberCreate.as_view(template_name="dataglen/add_member.html",
                                                                 success_url=reverse_lazy("dataglen:member-add")),
                           name='member-add'),
                       url(r'groups', DataglenGroupCreate.as_view(template_name="dataglen/add_group.html",
                                                                  success_url=reverse_lazy("dataglen:group-add")),
                           name='group-add'),
                       url(r'group/(?P<slug>[a-z0-9-_]+)/$', DataglenGroupUpdate.as_view(template_name="dataglen/update_group.html",
                                                                  success_url=reverse_lazy("dataglen:group-add")),
                           name='group-sensor-update'),

                       #url(r'upload/(?P<source_key>[\w]+)/$', ui_views.upload, name="upload_data"),
                       # TODO remove this function later. use the data retrieval api directly.
                       url(r'scatter_plot/', charts_views.scatter_data, name="scatter_data"),
                       url(r'get_heat_map_week_data/(?P<identifier>[\w]+)/$', views.HeatMapData.as_view(),
                           name='get_heat_map_week_data'),)

urlpatterns = format_suffix_patterns(urlpatterns)
