from django.conf.urls import patterns, url

from datasink import views

urlpatterns = patterns('',
                       url(r'^$', views.index, name='index'))
