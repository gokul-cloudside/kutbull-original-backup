from . import views

from django.conf.urls import patterns, url


urlpatterns = patterns('',
                       url(r'error/', views.ErrorView.as_view(), name='500_error_view'),
                       url(r'redirect/', views.EntryPointPostLogin.as_view(), name='post_successful_login'),
                       url(r'dglogin/', views.DataGlenLoginView.as_view(), name='dataglen_login'),)
