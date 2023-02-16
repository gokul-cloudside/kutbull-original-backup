from django.conf.urls import url
from django.views.generic import TemplateView

urlpatterns = [
	url(r'^home/$', TemplateView.as_view(template_name="website/index.html"), name="home"),
    url(r'^customers/$', TemplateView.as_view(template_name="website/customers.html"), name="customers"),
    url(r'^team/$', TemplateView.as_view(template_name="website/team.html"), name="team"),
    url(r'^faq/$', TemplateView.as_view(template_name="website/faq.html"), name="faq"),
    url(r'^life_at_dataglen/$', TemplateView.as_view(template_name="website/lifeatdataglen.html"), name="life_at_dataglen"),
    url(r'^gmap-demo/$', TemplateView.as_view(template_name="website/gmap-demo.html"), name="gmapdemo"),
]
