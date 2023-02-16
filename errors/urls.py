from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from errors import views 
from django.core.urlresolvers import reverse_lazy

urlpatterns = patterns('',
                       url(r'error_streams/create/(?P<source_key>[\w]+)/$', views.ErrorStreamCreateView.as_view(),
                           name="error-stream-create"),)

urlpatterns = format_suffix_patterns(urlpatterns)