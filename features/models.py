from django.db import models
import abc
from django.contrib.auth.models import User
from dashboards.models import DataglenClient, Dashboard
from importlib import import_module
from solarrms.models import SolarPlant

import logging

logger = logging.getLogger('widgets.models')
logger.setLevel(logging.DEBUG)

SOLAR_USER_ROLE = [('CEO', 'CEO'),
                   ('O&M_MANAGER', 'O&M_MANAGER'),
                   ('SITE_ENGINEER', 'SITE_ENGINEER'),
                   ('CLIENT_CEO', 'CLIENT_CEO'),
                   ('CLIENT_O&M_MANAGER', 'CLIENT_O&M_MANAGER'),
                   ('CLIENT_SITE_ENGINEER', 'CLIENT_SITE_ENGINEER')]

class FeatureCategory(models.Model):
    name = models.CharField(max_length=50, blank=False, null=False)
    enabled = models.BooleanField(default=True, blank=False, null=False)

    def __unicode__(self):
        return self.name


class Feature(models.Model):
    feature_category = models.ForeignKey(FeatureCategory, related_name="features",
                                         related_query_name="feature")
    name = models.CharField(max_length=50, blank=False, null=False)
    enabled = models.BooleanField(default=True, blank=False, null=False)
    function_path = models.CharField(max_length=100, blank=False, null=False, help_text="A function that returns "
                                                                                        "data for this feature")
    data_key_name = models.CharField(max_length=100, blank=False, null=False)
    include_table = models.BooleanField(default=False, null=False, blank=False, help_text="whether this feature should be included in the plants table or not")

    def get_data(self, *args, **kwargs):
        module_path, function_name = self.function_path.rsplit('.', 1)
        module = import_module(module_path)
        func = getattr(module, function_name)
        # run the function
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            #logger.exception('Failed to get data for a feature %s: %s', self.name, str(exc)
            logger.debug(str(exc))
            return None

    def __unicode__(self):
        return self.name + "_" + self.feature_category.__unicode__()


class SubscriptionPlan(models.Model):
    dashboard = models.ForeignKey(Dashboard,
                                  related_name="subscription_plans")
    name = models.CharField(blank=False, null=False, max_length=50)
    features = models.ManyToManyField(Feature,
                                      related_name="subscriptions")


    def __unicode__(self):
        return self.name


class DGClientSubscription(models.Model):
    subscription_plan = models.ForeignKey(SubscriptionPlan,
                                          related_name="clients")
    dg_client = models.ForeignKey(DataglenClient,
                                  related_name="subscription")

    def __unicode__(self):
        return self.dg_client.__unicode__() + "_" + self.subscription_plan.__unicode__()


class RoleAccess(models.Model):
    dg_client = models.ForeignKey(DataglenClient,
                                  related_name="access_definitions")
    role = models.CharField(max_length=100, null=False, blank=False, choices=SOLAR_USER_ROLE)
    features = models.ManyToManyField(Feature,
                                      related_name="access")

    def __unicode__(self):
        return self.dg_client.__unicode__() + "_" + self.role


CONFIG_SCOPE = (('portfolio', 'PORTFOLIO'), ('plant', 'PLANT'))


class UserTableWidgetsConfig(models.Model):
    user = models.ForeignKey(User)
    feature_columns = models.ManyToManyField(Feature, related_name='feature_columns',
                                           through='FeatureOrder')
    config_scope = models.CharField(choices=CONFIG_SCOPE, max_length=20, null=False, blank=False)

    class Meta:
        unique_together = (("user", "config_scope"),)

    def __unicode__(self):
        return "%s_%s" % (self.user, self.config_scope)

    def get_all_featues_for_user(self):
        accessible_features = RoleAccess.objects.get(role=self.user.role.role,
                                                     dg_client=self.user.role.dg_client)
        return accessible_features.features.all()

    def all_columns(self):
        all_features = self.get_all_featues_for_user()
        return set(all_features.values_list('name', flat=True))


class FeatureOrder(models.Model):
    order_number = models.PositiveIntegerField()
    is_fixed = models.BooleanField(default=False)
    user_table_widgets = models.ForeignKey(UserTableWidgetsConfig, on_delete=models.CASCADE)
    features = models.ForeignKey(Feature)


class UserSolarPlantWidgetsConfig(models.Model):
    user = models.ForeignKey(User)
    plants = models.ManyToManyField(SolarPlant, related_name='plants')
    config_name = models.CharField(max_length=100, null=False, blank=False)

    def __unicode__(self):
        return "%s_%s" % (self.user, self.config_name)

    class Meta:
        unique_together = (("user", "config_name"), )

FEATURE_CHART_TYPE= [('BAR','BAR'),('LINE','LINE')]
FEATURE_UNITS = [('Power','kW')]
REPORT_TYPES = [('DAILY','DAILY'),('MONTHLY','MONTHLY'),('YEARLY','YEARLY')]
# Custom Feature
class CustomFeature(models.Model):
    """
    Admin can create, edit and save custom features
    """
    feature_title = models.CharField(max_length=100, blank=True, null=True, help_text='')
    feature_description = models.CharField(max_length=100, blank=True, null=True, help_text='')
    feature_columns = models.CharField(max_length=100, blank=True, null=True, help_text='No of Days in case of PDF') #add choice 5days/7days
    feature_chart_type = models.CharField(max_length=100, blank=True, null=True,choices=FEATURE_CHART_TYPE, help_text='BAR/LINE') # add choice bar/ line
    feature_unit = models.CharField(max_length=100, blank=True, null=True, choices=FEATURE_UNITS, help_text='kw/cm/degree')
    feature_type = models.CharField(max_length=100, blank=True, null=True, help_text='')
    feature_order = models.SmallIntegerField(default=0, blank=False, null=False, help_text="order number in feature sequence")
    features = models.ForeignKey(Feature, blank=False, null=False,related_name="custom_feature")

# Custom Format
class CustomReportFormat(models.Model):
    name = models.CharField(max_length=100, blank=False, null=False)
    custom_features = models.ManyToManyField(CustomFeature, blank=True,null=True,related_name="custom_report")
    dg_client = models.ForeignKey(DataglenClient, null=False, blank=False, related_name="custom_report")
    role = models.CharField(max_length=100, null=False, blank=False, choices=SOLAR_USER_ROLE)
    role_default = models.BooleanField(null=False, blank=False, default=False)
    report_type = models.CharField(max_length=100, null=False, blank=False, choices=REPORT_TYPES, help_text="Daily/Monthly/Yearly")
    user = models.ManyToManyField(User, related_name="custom_report")

    def __str__(self):
        return self.name

    def update_custom_format(self, list_of_new_feature_dict):
        # First verify if we are getting valid features to add or update based on User Role.
        accessible_features_ids = RoleAccess.objects.get(role=self.role,dg_client=self.dg_client)\
                                                        .features.all().values_list('id',flat=True)
        new_feature_ids = [x['feature_id'] for x in list_of_new_feature_dict]
        if set(new_feature_ids).issubset(set(accessible_features_ids)):
            print "allowed"
            print list_of_new_feature_dict
        else:
            print "invalid features"
            return "Feature not in the scope of role"


        custom_feature_set = []
        all_current_features = self.custom_features.all()
        for current_feature in all_current_features:
            self.custom_features.remove(current_feature)
            # current_feature.feature_order = 0
            # current_feature.save()

        for new_feature in list_of_new_feature_dict:
            new_custom_feature = self.create_or_update_custom_feature(new_feature)
            if new_custom_feature:
                custom_feature_set.append(new_custom_feature)
            else:
                print "custom feature creation failed for feature ==> ", new_feature
        if custom_feature_set:
            for custom_feature in custom_feature_set:
                self.custom_features.add(custom_feature)
        self.save()
        return True

    def create_or_update_custom_feature(self, new_feature_dict):
        """
        new_feature_dict = { feature_id : { feature_title,feature_desc,cols,chart_type, etc}}
        Formats are based on role.
        If admin selects a feature format for a role it can be applied to that role only.
        If admin selects a feature format for user. we fetch the role first then show available
        features for that user role.

        :param feature:
        :return:
        """

        if 'feature_id' in new_feature_dict:
            feature_id = new_feature_dict['feature_id']
            all_existing_feature_ids = self.custom_features.all().values_list('features__id',flat=True)
            if feature_id in all_existing_feature_ids:
                custom_feature = self.custom_features.all().get(features__id=feature_id)
            else:
                print "feature id is====", feature_id
                try:
                    feature = Feature.objects.get(id=int(feature_id))
                    custom_feature = CustomFeature.objects.create(features=feature)
                except:
                    logger.debug("feature does not exist feature_id = %s" %feature_id)
                    return False
        else:
            logger.debug("feature_id not found")
            return "feature_id not found"

        attribute_vals = new_feature_dict
        if 'feature_title' in attribute_vals:
            custom_feature.feature_title = attribute_vals['feature_title']
        if 'feature_description' in attribute_vals:
            custom_feature.feature_description = attribute_vals['feature_description']
        if 'feature_columns' in attribute_vals:
            custom_feature.feature_columns = attribute_vals['feature_columns']
        if 'feature_chart_type' in attribute_vals:
            custom_feature.feature_chart_type = attribute_vals['feature_chart_type']
        if 'feature_unit' in attribute_vals:
            custom_feature.feature_unit = attribute_vals['feature_unit']
        if 'feature_type' in attribute_vals:
            custom_feature.feature_type = attribute_vals['feature_type']
        if 'feature_order' in attribute_vals:
            custom_feature.feature_order = attribute_vals['feature_order']
        custom_feature.save()
        return custom_feature

    def save(self, *args, **kwargs):

        super(CustomReportFormat, self).save(*args, **kwargs)