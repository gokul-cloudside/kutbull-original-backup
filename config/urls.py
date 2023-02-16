from django.conf.urls import patterns, url

from dataglen import ui_views, charts_views
from rest_framework.urlpatterns import format_suffix_patterns

from config import views 
from django.core.urlresolvers import reverse_lazy
from dashboards.views import OrganizationEmployeeCreate, DataglenGroupCreate, GroupMemberCreate, \
    DataglenGroupUpdate

urlpatterns = patterns('',
                       url(r'config_streams/create/(?P<source_key>[\w]+)/$', views.ConfigStreamCreateView.as_view(),
                           name="config-stream-create"),)

urlpatterns = format_suffix_patterns(urlpatterns)