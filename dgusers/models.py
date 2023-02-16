from django.db import models
from django.contrib.auth.models import User
from dashboards.models import DataglenClient
from helpdesk.models import EVENT_TYPE, EVENT_TYPE_TO_FEATURE_MAPPING
from solarrms.models import SolarPlant
from features.models import RoleAccess
import logging
from django.utils import timezone
from datetime import timedelta
from features.models import SOLAR_USER_ROLE
from django.db import transaction
from django.contrib.auth.models import User

logger = logging.getLogger('helpdesk.models')
logger.setLevel(logging.DEBUG)


class UserRole(models.Model):
    user = models.OneToOneField(User, related_name="role", related_query_name="role")
    role = models.CharField(max_length=100, null=False, blank=False, choices=SOLAR_USER_ROLE)
    dg_client = models.ForeignKey(DataglenClient, null=True, blank=True, related_name="dg_client", related_query_name="dg_client")

    # if this parameter is checked, send AGGREGATED report and sms
    daily_report = models.BooleanField(default=False, null=False, blank=False)
    enable_alerts = models.BooleanField(default=False)
    account_suspended = models.BooleanField(default=False)
    # for user or plant preference edit page
    enable_preference_edit = models.BooleanField(default=False)

    gateway_alerts_notifications = models.BooleanField(default=False, null=False, blank=False)
    inverters_alerts_notifications = models.BooleanField(default=False, null=False, blank=False)
    other_alerts = models.BooleanField(default=False, null=False, blank=False)

    sms = models.BooleanField(default=False, null=False, blank=False, help_text="Is SMS alerts enabled for this user.")
    phone_number = models.CharField(blank=True, null=True, max_length=15, help_text="Phone number on which sms alerts should be sent.")
    viewOnly = models.BooleanField(blank=False, null=False, default=False, help_text="If downloadable link should be enabled or not.")

    @staticmethod
    def sort_alerts(alerts):
        predefined_order = ['GATEWAY_POWER_OFF'.replace("_", " ").title(),
                            'GATEWAY_DISCONNECTED'.replace("_", " ").title(),
                            'INVERTERS_DISCONNECTED'.replace("_", " ").title(),
                            'INVERTERS_ALARMS'.replace("_", " ").title(),
                            'PANEL_CLEANING'.replace("_", " ").title(),
                            'AJBS_DISCONNECTED'.replace("_", " ").title(),
                            'AJB_STRING_CURRENT_ZERO_ALARM'.replace("_", " ").title(),
                            'INVERTERS_UNDERPERFORMING'.replace("_", " ").title(),
                            'MPPT_UNDERPERFORMING'.replace("_", " ").title(),
                            'AJB_UNDERPERFORMING'.replace("_", " ").title()]
        new_order = sorted(alerts, key=lambda i:predefined_order.index(i['event_type']))
        return new_order

    def __unicode__(self):
        return "_".join([self.user.username, str(self.role), str(self.dg_client.name)])

    # setup alerts preferences for this user, if they have not been set already
    def save(self, *args, **kwargs):
        super(UserRole, self).save(*args, **kwargs)
        logger.debug("save() UserRole" + str(self.id))
        if self.id:
            logger.debug("inside self.id " + str(len(self.alerts_preferences.all())))
            if len(self.alerts_preferences.all()) == 0:
                AlertsCategory.setup_alerts_preferences(self)
            if len(self.alerts_preferences_plants.all()) == 0:
                instance = UserRolePlantsAlertsPreferences.objects.create(user_role=self)
                instance.save()
        return

    # get the alerts the user has permissions to
    def list_accessible_alerts(self, serizalize=True):
        accessible_features = RoleAccess.objects.get(role=self.role,
                                                     dg_client=self.dg_client)

        alert_categories = self.alerts_preferences.filter(event_type__in=["GATEWAY_POWER_OFF", "GATEWAY_DISCONNECTED",
                                                                          "INVERTERS_DISCONNECTED", "INVERTERS_ALARMS",
                                                                          "PANEL_CLEANING", "INVERTERS_UNDERPERFORMING"])
        alerts = []
        for alert in alert_categories:
            try:
                len(accessible_features.features.filter(
                    name=EVENT_TYPE_TO_FEATURE_MAPPING[alert.event_type])) > 0
                if serizalize:
                    info = alert.serialize()
                    if info:
                        alerts.append(info)
                else:
                    alerts.append(alert)
            except:
                continue


        return UserRole.sort_alerts(alerts)

    # for a given plant and event type, get the list of
    # users with alerts who should be sent an alert
    @staticmethod
    def users_list_for_notifications(plant_slug, event_type, closing_alert=False):
        emails = []
        phone_numbers = []

        try:
            plant = SolarPlant.objects.get(slug=plant_slug)
        except:
            return [], []

        try:
            for org_user in plant.organization_users.all():
                try:
                    user_role = org_user.user.role
                    accessible_features = RoleAccess.objects.get(role=org_user.user.role.role,
                                                                 dg_client=plant.groupClient)

                    alert_category = user_role.alerts_preferences.get(event_type=event_type)

                    if alert_category.enabled is True and len(accessible_features.features.filter(
                                            name=EVENT_TYPE_TO_FEATURE_MAPPING[event_type])) > 0:
                        selected_user = org_user.user

                        # send_email
                        if alert_category.send_email(closing_alert) is True:
                            if selected_user.email not in emails:
                                emails.append((selected_user.email, alert_category.id))

                        # send sms
                        if alert_category.send_sms(closing_alert) is True:
                            if user_role.phone_number is not None \
                                    and 10 <= len(user_role.phone_number) <= 13 \
                                    and user_role.phone_number not in phone_numbers:
                                phone_numbers.append((user_role.phone_number, alert_category.id))
                except:
                    continue

            # logger.debug(",".join(["users_list_for_notifications", plant_slug, str(event_type),
            #                             str(emails), str(phone_numbers)]))
            return emails, phone_numbers

        except Exception as exc:
            logger.debug("users_list_for_notifications exception: " + str(exc))
            return [], []


class UserRolePlantsAlertsPreferences(models.Model):
    user_role = models.ForeignKey(UserRole, related_name="alerts_preferences_plants",
                                            related_query_name="alerts_preferences_plants")
    alerts_enabled = models.ManyToManyField(SolarPlant,
                                            related_name="alerts_users_preferences",
                                            related_query_name="alerts_users_preferences")

    def get_preferences(self):
        allowed_plants = []
        enabled = 0
        total = 0
        for group in self.user_role.user.organizations_organizationuser.all():
            try:
                if hasattr(group.organization.dataglengroup, 'solarplant'):
                    if self.alerts_enabled.filter(slug=group.organization.dataglengroup.solarplant.slug).first():
                        allowed_plants.append({"name": group.organization.dataglengroup.solarplant.name,
                                               "slug": group.organization.dataglengroup.solarplant.slug,
                                               "enabled": True})
                        enabled += 1
                    else:
                        allowed_plants.append({"name": group.organization.dataglengroup.solarplant.name,
                                               "slug": group.organization.dataglengroup.solarplant.slug,
                                               "enabled": False})
                total += 1
            except Exception as exc:
                logger.debug("error getting alerts preferences: " + str(exc))
                continue

        return allowed_plants, enabled, total

    def set_preferences(self, slugs):
        for group in self.user_role.user.organizations_organizationuser.all():
            try:
                if hasattr(group.organization.dataglengroup, 'solarplant'):
                    if group.organization.dataglengroup.solarplant.slug in slugs:
                        if self.alerts_enabled.filter(slug=group.organization.dataglengroup.solarplant.slug).first():
                            continue
                        else:
                            self.alerts_enabled.add(group.organization.dataglengroup.solarplant)

                    else:
                        if self.alerts_enabled.filter(slug=group.organization.dataglengroup.solarplant.slug).first():
                            self.alerts_enabled.remove(group.organization.dataglengroup.solarplant)
                    self.save()
            except Exception as exc:
                logger.debug("error saving alerts preferences: " + str(exc))
                continue
        return True

DEFAULT_THRESHOLD = {
    'INVERTERS_UNDERPERFORMING' : 15,
    'MPPT_UNDERPERFORMING' : 15,
    'AJB_UNDERPERFORMING' : 15
}

class AlertsCategory(models.Model):
    user_role = models.ForeignKey(UserRole, related_name="alerts_preferences", related_query_name="alerts_preferences")
    event_type = models.CharField(choices=EVENT_TYPE, max_length=50, null=False, blank=False)
    enabled = models.BooleanField(default=False, blank=False, null=False)
    threshold_applicable = models.BooleanField(default=False, blank=False, null=False)
    threshold_value = models.FloatField(default=10, blank=False, null=False)
    email_notifications = models.BooleanField(default=False, blank=False, null=False)
    sms_notifications = models.BooleanField(default=False, blank=False, null=False)
    email_aggregation_minutes = models.IntegerField(default=120, blank=False, null=False)
    sms_aggregation_minutes = models.IntegerField(default=120, blank=False, null=False)
    emails_count = models.IntegerField(default=0, blank=False, null=False)
    sms_count = models.IntegerField(default=0, blank=False, null=False)
    last_email = models.DateTimeField(blank=True, null=True)
    last_sms = models.DateTimeField(blank=True, null=True)
    alert_on_close = models.BooleanField(blank=False, null=False, default=True)

    class Meta:
        unique_together = (("user_role", "event_type"),)

    def __unicode__(self):
        return "_".join([self.user_role.user.username, str(self.event_type)])

    def serialize(self):
        try:
            data = {"event_type": str(self.event_type).replace("_", " ").title(),
                    "enabled": self.enabled,
                    "email_notifications": self.email_notifications,
                    "sms_notifications": self.sms_notifications,
                    "email_aggregation_minutes": int(self.email_aggregation_minutes),
                    "sms_aggregation_minutes": int(self.sms_aggregation_minutes),
                    "emails_count": int(self.emails_count),
                    "sms_count": int(self.sms_count),
                    "alert_on_close": self.alert_on_close}
            if self.threshold_applicable:
                data["threshold_value"] = self.threshold_value
            return data
        except Exception as exc:
            logger.debug(str(exc))
            return {}

    @staticmethod
    def setup_alerts_preferences(user_role):
        for event_type in EVENT_TYPE:
            try:
                with transaction.atomic():
                    if event_type[0] in DEFAULT_THRESHOLD.keys():
                        AlertsCategory.objects.create(user_role=user_role, event_type=event_type[0],
                                                      threshold_applicable = True,
                                                      threshold_value=DEFAULT_THRESHOLD[event_type[0]])
                    else:
                        AlertsCategory.objects.create(user_role=user_role, event_type=event_type[0])

            except Exception as exc:
                logger.debug(str(exc))
                continue

    def send_email(self, closing_alert=False):
        if closing_alert is True and self.alert_on_close is False:
            return False

        if self.last_email is None:
            return True
        try:
            if self.email_notifications and \
               timezone.now() - self.last_email > timedelta(minutes=self.email_aggregation_minutes):
                return True
            else:
                return False
        except:
            return False

    def send_sms(self, closing_alert=False):
        if closing_alert is True and self.alert_on_close is False:
            return False

        if self.last_sms is None:
            return True
        try:
            if self.sms_notifications and \
               timezone.now() - self.last_sms > timedelta(minutes=self.sms_aggregation_minutes):
                return True
            else:
                return False
        except:
            return False


    @staticmethod
    def update_email_time(id, current_time=None):
        if current_time is None:
            current_time = timezone.now()
        try:
            alert_category = AlertsCategory.objects.get(id=id)
            alert_category.last_email = current_time
            alert_category.emails_count += 1
            alert_category.save()
            return True
        except:
            return False


    @staticmethod
    def update_sms_time(id, current_time=None):
        if current_time is None:
            current_time = timezone.now()
        try:
            alert_category = AlertsCategory.objects.get(id=id)
            alert_category.last_sms = current_time
            alert_category.sms_count += 1
            alert_category.save()
            return True
        except:
            return False