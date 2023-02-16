from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from django.core.urlresolvers import reverse_lazy
from reports import views


urlpatterns = patterns('',
                       url(r'sources/(?P<source_key>[\w]+)/$',
                           views.GeneratePDFReportView.as_view(),
                           name="pdf-create"),)

urlpatterns = format_suffix_patterns(urlpatterns)