from django.conf.urls import patterns, url

from dataglen import ui_views, charts_views
from rest_framework.urlpatterns import format_suffix_patterns

from action import views 
from django.core.urlresolvers import reverse_lazy
from dashboards.views import OrganizationEmployeeCreate, DataglenGroupCreate, GroupMemberCreate, \
    DataglenGroupUpdate

urlpatterns = patterns('',
                       url(r'action_streams/create/(?P<source_key>[\w]+)/$', views.ActionStreamCreateView.as_view(),
                           name="action-stream-create"),)

urlpatterns = format_suffix_patterns(urlpatterns)