from django.db import models
from features.models import Feature
import abc
from django.utils import timezone
from importlib import import_module
from django.core.exceptions import ImproperlyConfigured
from dgusers.models import UserRole
from features.models import RoleAccess

import logging

logger = logging.getLogger('widgets.models')
logger.setLevel(logging.DEBUG)


# Create your models here.
# scope - portfolio/group/source
# time period - day/range
class Widget(models.Model):
    name = models.CharField(max_length=50, blank=False, null=False)

    # global list of features this widget has access to
    features = models.ManyToManyField(Feature, null=False, blank=False,
                                      related_name="widgets")

    packaging_function_path = models.CharField(max_length=100, blank=True, null=True,
                                               help_text="A function that packages the raw data")
    widget_id = models.IntegerField(blank=False, null=False)

    # default implementation of the get data function
    def __getdata__(self, user, *args, **kwargs):
        t0 = timezone.now()
        try:
            dg_user = UserRole.objects.get(user=user)
        except UserRole.DoesNotExist:
            raise ImproperlyConfigured("This user has no role defined")

        role_access = RoleAccess.objects.get(dg_client=dg_user.dg_client,
                                             role=dg_user.role)
        #logger.debug(";".join([str(self.widget_id),"Role access time: ", str(timezone.now() - t0)]))
        data = {}
        for feature in self.features.all():
            try:
                assert(feature in role_access.features.all())
        # for feature in role_access.features.all():
        #     try:
        #         assert(feature in self.features.all())
                t1 = timezone.now()
                if self.widget_id == 1 and feature.name == "LOGO" and user.email == "ndemo@dataglen.com":
                    data[feature.name] = {'client_logo': 'https://nise.res.in/wp-content/uploads/2017/05/logo-NISE.jpg'}
                elif self.widget_id == 1 and feature.name == "LOGO" and user.email in ["thematic.expo2020@gmail.com",
                                                                                       "opportunity.expo2020@gmail.com",
                                                                                       "sustainability.expo2020@gmail.com",
                                                                                       "mobility.expo2020@gmail.com"]:
                    data[feature.name] = {'client_logo': 'http://www.empereal.com/images/logo/logo.jpg'}
                elif self.widget_id == 1 and feature.name == "LOGO" and user.email == "dataglen@cleanmax.com":
                    data[feature.name] = {'client_logo': 'http://dataglen.com/static/website/images/dataglen_LOGO_transparent0.png'}

                elif self.widget_id == 1 and feature.name == "LOGO" and user.email == "dataglen@firstsolar.com":
                    data[feature.name] = {'client_logo': 'http://dataglen.com/static/website/images/dataglen_LOGO_transparent0.png'}

                elif self.widget_id == 1 and feature.name == "LOGO" and user.email == "mux@playsolar.in":
                    data[feature.name] = {'client_logo': 'http://www.playsolar.in/images/logo.png'}
                elif self.widget_id == 1 and feature.name == "LOGO" and user.email == "cdemo@dataglen.com":
                    data[feature.name] = {'client_logo': 'http://asia.conergy.com/wp-content/themes/conergy-child/images/conergy_logo.png'}
                elif self.widget_id == 1 and feature.name == "LOGO" and user.email == "ansdemo@dataglen.com":
                    data[feature.name] = {'client_logo': 'https://www.ausnetservices.com.au/-/media/Images/AusNet/Common/logo_ausnet.ashx'}
                elif self.widget_id == 1 and feature.name == "LOGO" and user.email == "webdyn@dataglen.com":
                    data[feature.name] = {'client_logo': 'https://www.webdyn.com/wp-content/uploads/2018/05/logo_webdyn_couleurs_72dpi.png'}
                elif self.widget_id == 1 and feature.name == "LOGO" and user.email == "wdemo@dataglen.com":
                    data[feature.name] = {
                        'client_logo': 'https://www.webdyn.com/wp-content/uploads/2018/05/logo_webdyn_couleurs_72dpi.png'}
                else:
                    data[feature.name] = feature.get_data(*args, **kwargs)
                # logger.debug(";".join([";", str(self.widget_id), str(self.name), str(feature), str(timezone.now() - t1)]))
            except Exception as exc:
                # logger.debug(str(exc))
                continue
        #logger.debug(";".join([";", str(self.widget_id), "Total time: ", str(timezone.now() - t0)]))

        return data

    # default implementation of the packaging function
    def __datapackaging__(self, *args, **kwargs):
        if self.packaging_function_path:
            module_path, function_name = self.packaging_function_path.rsplit('.', 1)
            module = import_module(module_path)
            func = getattr(module, function_name)
            # run the function
            try:
                return func(*args, **kwargs)
            except:
                #logger.exception('Failed to complete cronjob at %s', job)
                return None

    def __unicode__(self):
        return self.name

# power vs irradiation --> plant (which plant?) and inverter (which inverter?) (y1-y2 chart) : component1
# stacked bar chart for generation and losses --> plant (stacked bar) : component2
# gateway powered off number --> plant (only content) : component3
