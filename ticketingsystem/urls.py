from django.views.generic import TemplateView
from django.conf.urls import url

urlpatterns = [
    url(r'^hd/$',
        TemplateView.as_view(template_name="tickets.html")),
]