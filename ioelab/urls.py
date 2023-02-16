from django.conf.urls import patterns, url, include
from ioelab import views
from ioelab.views import InviteViewSet
from rest_framework.urlpatterns import format_suffix_patterns
from django.core.urlresolvers import reverse_lazy
from rest_framework_nested import routers


'''
urlpatterns = patterns('',
                       url(r'^invite$', views.InviteList.as_view()),
                       url(r'^invite(?P<pk>[0-9]+)/$', views.InviteDetail.as_view()),)

urlpatterns = format_suffix_patterns(urlpatterns)
'''



router = routers.SimpleRouter()
router.register(r'invite', InviteViewSet, base_name="invite")

urlpatterns = patterns('',
    #url(r'docs/', views.docs, name='docs'),
    url(r'^ValidateUID/', views.ValidateUIDView.as_view(), name='validate-UID'),
    url(r'^', include(router.urls)),

)
