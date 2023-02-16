from django.conf.urls import patterns, url
from dataviz import views

urlpatterns = patterns('',
		               url(r'^$', views.index, name="index"),
                       url(r'^show_data/$', views.show_data, name='show_data'),
                       url(r'^show_live_data/$', views.show_live_data, name='show_live_data'),
                       url(r'^data_status/$', views.generate_data_status, name='generate_data_status'),
                      )
