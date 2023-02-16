from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from django.core.urlresolvers import reverse_lazy
from events import views


urlpatterns = patterns('',
	url(r'sources/(?P<source_key>[\w]+)/alerts/preferences/$', views.ListPreferencesView.as_view(),
                           									name="list-alert-preferences"),
    url(r'sources/(?P<source_key>[\w]+)/alerts/add/$', 
    											views.AlertPreferencesAdd.as_view(
                       					        template_name = 'events/alert_preferences.html'),
                           						name="alert-preference-add"),
    url(r'sources/(?P<source_key>[\w]+)/alerts/update/(?P<preference_id>[\w]+)/$', views.UpdatePreferences.as_view(),
                           									name="preference-update"),)

urlpatterns = format_suffix_patterns(urlpatterns)