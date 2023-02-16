from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import python_2_unicode_compatible
from organizations.models import Organization
from solarrms.models import SolarPlant
from dashboards.models import DataglenClient, DataglenGroup
from django.core.exceptions import ValidationError
from django.contrib.auth.models import ContentType, User
from dgusers.models import UserRole
from django.contrib.contenttypes import fields
import logging
from django.db import transaction
from datetime import timedelta, time

logger = logging.getLogger('eventsframework.views')
logger.setLevel(logging.DEBUG)


# isoweekday
WEEKDAYS = [
    (1, _("Monday")),
    (2, _("Tuesday")),
    (3, _("Wednesday")),
    (4, _("Thursday")),
    (5, _("Friday")),
    (6, _("Saturday")),
    (7, _("Sunday")),
]


class TimeStampedModelMixin(models.Model):
    """
    Abstract Mixin model to add timestamp
    """
    # Timestamp
    created = models.DateTimeField(u"Date created", auto_now_add=True, db_index=True)
    updated = models.DateTimeField(
        u"Date updated", auto_now=True, db_index=True)

    class Meta:
        abstract = True


# => States
class BaseState(TimeStampedModelMixin):
    name = models.CharField(max_length=30, editable=False)
    display_name = models.CharField(max_length=30)
    description = models.CharField(max_length=150, null=True, blank=True)

    def __unicode__(self):
        return self.name

    class Meta:
        abstract = True


# we are keeping this model as an independent model, there will not be any linking with dataglenclient
# from solar or other dashboards
class Company(DataglenGroup):
    """
    Default model for company premises, which can be
    replaced using OPENINGHOURS_PREMISES_MODEL.
    """

    class Meta:
        verbose_name = _('Company')
        verbose_name_plural = _('Companies')

    # already covered in Organization
    # name = models.CharField(_('Name'), max_length=100)
    # slug = models.SlugField(_('Slug'), unique=True)
    logo = models.URLField(null=True, blank=True)

    # company details
    registered_name = models.CharField(max_length=100, null=False, blank=False)
    registered_office_address = models.TextField(blank=False, null=False)
    cin_number = models.CharField(max_length=100, null=True, blank=True)
    email = models.CharField(max_length=100, null=False, blank=False)
    tel_number = models.CharField(max_length=100, null=False, blank=False)
    website_address = models.CharField(max_length=100, null=False, blank=False)

    # tax details
    tax_details_primary = models.CharField(max_length=100, null=True, blank=True)
    tax_details_secondary = models.CharField(max_length=100, null=True, blank=True)

    #
    # add_new_solar_company("test", "test", "test", "test", "test", "test", "test", "test", "test", "test", "test", "test", "test")
    @staticmethod
    def add_new_solar_company(name,registered_name,registered_office_address,cin_number,email,\
                              tel_number,website_address,tax_details_primary,tax_details_secondary,
                              admin_first_name, admin_last_name, admin_email,
                              admin_phone_number, dgclient_user):

        # get the owner
        if not dgclient_user.role.enable_preference_edit:
            return ("Not Authorized")

        try:
            with transaction.atomic():
                # create a new Company
                newCompany = Company.objects.create(registered_name=registered_name,
                                                    registered_office_address=registered_office_address,
                                                    name=name,
                                                    cin_number=cin_number,
                                                    email= email,
                                                    tel_number=tel_number,
                                                    website_address=website_address,
                                                    tax_details_primary=tax_details_primary,
                                                    tax_details_secondary=tax_details_secondary,
                                                    groupClient=dgclient_user.role.dg_client)

                # assign a new owner for the new company - same as the dg_client
                newAdminUser = User.objects.create(username=admin_email, first_name=admin_first_name,
                                                   last_name=admin_last_name, email=admin_email)
                # assign role for the new user as OM_VENDOR_ADMIN
                UserRole.objects.create(user=newAdminUser, phone_number=admin_phone_number,
                                        role="OM_VENDOR_ADMIN",
                                        dg_client=dgclient_user.role.dg_client)
                newCompany.add_user(newAdminUser)
                #set password for new user
                newAdminUser.set_password(str(admin_email))
                newAdminUser.save()
                logger.info("New company created")
                return newCompany
        except Exception as exc:
            logger.debug(",".join(["Error creating a new company", str(exc)]))
            return False

    def add_site_technician(self, username, first_name, last_name, email,
                            phone_number):
        try:
            with transaction.atomic():
                # add a user
                user = User.objects.create(username = username, first_name=first_name, last_name=last_name, email=email)
                # user = ?
                # ur = add user role OM_VENDOR_FT
                UserRole.objects.create(user = user, phone_number= phone_number, role="OM_VENDOR_FT", dg_client=self.groupClient)
                # self.add_user(user, False)
                self.add_user(user)
                return True
        except Exception as exc:
            logger.debug(",".join(["Error adding a new site technician", str(exc)]))
            return False

    @staticmethod
    def disable_site_technician(user):
        try:
            with transaction.atomic():
                # find user role ur =
                user.role.account_suspended = True
                user.role.save()
                # mark suspended =
                return True
        except Exception as exc:
            logger.debug(",".join(["Error disabling a site technician", str(exc)]))
            return False

    def delete_site_technician(self, user):
        try:
            with transaction.atomic():
                self.remove_user(user)
                # delete user role
                user.role.delete()
                # delete user instance
                user.delete()
                return True
        except Exception as exc:
            logger.debug(",".join(["Error deleting a site technician", str(exc)]))
            return False

    def get_all_contracts(self):
        # returns all contracts - should only be returning for an admin
        return self.contracts.all()

    def get_all_accessible_plants(self, user):
        # based on the role - get the details from contracts
        # returns all plants based on user's profile
        pass

    def get_all_service_requests(self, user):
        # returns a list of service requests, based on a user's profile
        pass

    def __str__(self):
        return self.name


state_options = [(0, 'Open', 'A new service request has been opened'),
                 (1, 'First Response', 'This request has been acknowledged by the vendor'),
                 (2, 'Field Technician Assigned', 'A field technician has been assigned for this request') ,
                 (3, 'Repaired', 'This request has been repaired and can be reviewed') ,
                 (4, 'Closed', "This request has been closed after an inspection")]


class MaintenanceContract(models.Model):
    name = models.CharField(max_length=50, blank=False, null=False)
    company = models.ForeignKey(Company, related_name="contracts")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    phone_number = models.CharField(max_length=15)
    fax_number = models.CharField(max_length=15)
    email = models.CharField(max_length=50)
    comments = models.TextField(blank=True, null=True)
    plants = models.ManyToManyField(SolarPlant, related_name="contracts", blank=True)

    def clean(self):
        # there cannot be two slas for the same state
        # there cannot be a state for which there is no sla
        pass

    def create_new_service_request(self, priority, plant):
        try:
            with transaction.atomic():
                # check that this plant should exist in contract plants
                assert(plant in self.plants)

                # create a new Event
                # TODO to be done by Lavanya - please add necessary fields
                event = Event.objects.create()

                # create a new service request
                service_request = ServiceRequest.objects.create(contract=self,
                                                                plant=plant,
                                                                priority=priority,
                                                                event=event,
                                                                sla_met=False)
                service_request.save()

                # create the first state of this service request
                # get the initial state of this contract
                contract_initial_state = self.contract_states.all().order_by('order')[0]
                # create a new service state based on these properties
                service_request_initial_state = ServiceRequestState.objects.create(name=contract_initial_state.name,
                                                                                   displayName=contract_initial_state.displayName,
                                                                                   description=contract_initial_state.description,
                                                                                   service_request=service_request,
                                                                                   active=True,
                                                                                   order=contract_initial_state.order)
                service_request_initial_state.save()
                return True
        except Exception as exc:
            logger.debug(",".join(["Error creating a new service request", str(exc)]))
            return False

    def save(self, *args, **kwargs):
        # create the initial ContractStates of this contract
        try:
            with transaction.atomic():
                new_contract = False
                if self.pk is None:
                    new_contract = True
                # call the super first to save the instance since we are saving m2m instances
                super(MaintenanceContract, self).save(*args, **kwargs)

                logger.debug(",".join(["New Contract", str(new_contract)]))

                # if it is the first execution
                if new_contract and self.contract_states.all().count() == 0:
                    logger.debug(",".join(["Adding new ContractState", str(new_contract)]))
                    # create new ContractStates
                    for state in state_options:
                        cs = ContractState.objects.create(contract=self,
                                                          name=state[1],
                                                          display_name=state[1],
                                                          description=state[2],
                                                          order=state[0])
                        cs.save()

                # create new SLAs
                if new_contract and self.slas.all().count() == 0:
                    logger.debug(",".join(["New SLAs", str(new_contract)]))
                    max_state_order = self.contract_states.all().order_by('-order')[0].order
                    for state_order in range(max_state_order):
                        from_state = self.contract_states.get(order=state_order)
                        to_state = self.contract_states.get(order=state_order + 1)
                        for priority in priority_categories:
                            sla = SLA.objects.create(contract=self,
                                                     priority=priority,
                                                     from_state=from_state,
                                                     to_state=to_state,
                                                     time=timedelta(hours=1),
                                                     consider_closed_hours=False,
                                                     consider_closed_days=False)
                            sla.save()

                # create opening hours
                if new_contract:
                    logger.debug(",".join(["Opening Hours", str(new_contract)]))
                    for weekday in WEEKDAYS:
                        weekday = weekday[0]
                        from_hour = time(hour=9)
                        to_hour = time(hour=19)
                        if weekday is 7:
                            from_hour = time(hour=0)
                            to_hour = time(hour=0)
                        opening_hours = OpeningHours.objects.create(contract=self,
                                                                    weekday=weekday,
                                                                    from_hour=from_hour,
                                                                    to_hour=to_hour)
                        opening_hours.save()

                logger.info("New contract created")
            return True
        except Exception as exc:
            logger.debug(",".join(["Error creating a new Contract ", str(exc)]))
            return False

    def __unicode__(self):
        return self.name


event_categories = ("PREDICTIVE_EVENT", "PREVENTIVE_EVENT", "CORRECTIVE_EVENT")
priority_categories = ('LOW', 'MEDIUM', 'HIGH', 'PREVENTIVE')


# this will be linked either to a ticket or to a O&MTask
class Event(models.Model):
    event_category = models.CharField(choices=zip(event_categories, event_categories),
                                      max_length=50, blank=False, null=False)
    priority_category = models.CharField(choices=zip(priority_categories, priority_categories),
                                         max_length=50, blank=False, null=False)
    content_type = models.ForeignKey(ContentType, related_name="content_type")
    object_id = models.PositiveIntegerField(blank=False, null=False)
    content_object = fields.GenericForeignKey('content_type', 'object_id')
    name = models.CharField(max_length=50, blank=False, null=False)

    def __unicode__(self):
        return "%s_%s_%s" %(self.name, self.event_category, self.priority_category)


class ContractState(BaseState):
    contract = models.ForeignKey(MaintenanceContract, related_name="contract_states")
    color = models.CharField(default='008ac6', max_length=10, null=True, blank=True)
    order = models.IntegerField(blank=False, null=False)

    def next_state(self):
        try:
            with transaction.atomic():
                next_state = self.contract.contract_states.get(order=self.order+1)
                return next_state
        except Exception as exc:
            logger.debug(",".join(["Error getting the next state", str(exc)]))
            return False

    class Meta:
        unique_together = (('order', 'contract'),)


class ServiceRequest(models.Model):
    contract = models.ForeignKey(MaintenanceContract, related_name="service_requests")
    plant = models.ForeignKey(SolarPlant, related_name="service_requests")
    priority = models.CharField(choices=zip(priority_categories, priority_categories),
                                max_length=100, null=False, blank=False)
    event = models.OneToOneField(Event, related_name="service_request")
    sla_met = models.BooleanField(default=True, blank=False, null=False)
    closed_at = models.DateTimeField(
        u"Closing time", db_index=True, blank=True, null=True)
    summary = models.TextField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)

    def get_current_state(self):
        # returns the latest state
        pass

    # return the name of next state with remaining time on SLA Sunil
    def get_next_state(self):
        # get next state name and SLA time remaining
        pass

    def move_to_next_state(self):
        # create next state object
        pass

    def close_service_request(self):
        # close the existing
        pass


class ServiceRequestState(BaseState):
    service_request = models.ForeignKey(ServiceRequest, related_name="service_states")
    active = models.BooleanField(default=True)
    order = models.IntegerField(blank=False, null=False)
    closed_at = models.DateTimeField(
        u"Closing time", db_index=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        # the name of this servicerequeststate should be present in
        # contractstates of the contract of the service_request obj
        pass

    class Meta:
        unique_together = (('order', 'service_request'),)


class SLA(TimeStampedModelMixin):
    contract = models.ForeignKey(MaintenanceContract, related_name="slas")
    priority = models.CharField(choices=zip(priority_categories, priority_categories),
                                max_length=50, blank=False)
    from_state = models.ForeignKey(ContractState, related_name="from_slas")
    to_state = models.ForeignKey(ContractState, related_name="next_slas")
    # it is a datetime.timedelta object
    time = models.DurationField(blank=False, null=False, default=timedelta(hours=1))
    consider_closed_hours = models.BooleanField(default=False)
    consider_closed_days = models.BooleanField(default=False)

    def __unicode__(self):
        return ",".join([self.from_state.name, self.to_state.name])


class OpeningHours(models.Model):
    """
    Store opening times of company premises,
    defined on a daily basis (per day) using one or more
    start and end times of opening slots.
    """

    class Meta:
        verbose_name = _('Opening Hours')  # plurale tantum
        verbose_name_plural = _('Opening Hours')
        ordering = ['weekday', 'from_hour']

    contract = models.ForeignKey(MaintenanceContract, verbose_name=_('MaintenanceContract'))
    weekday = models.IntegerField(_('Weekday'), choices=WEEKDAYS)
    from_hour = models.TimeField(_('Opening'), default=time(hour=9), blank=False, null=False)
    to_hour = models.TimeField(_('Closing'), default=time(hour=19), blank=False, null=False)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return _("%(contract)s %(weekday)s (%(from_hour)s - %(to_hour)s)") % {
            'contract': self.contract.name,
            'weekday': self.weekday,
            'from_hour': self.from_hour,
            'to_hour': self.to_hour
        }


class ClosingRules(models.Model):
    """
    Used to overrule the OpeningHours. This will "close" the store due to
    public holiday, annual closing or private party, etc.
    """

    class Meta:
        verbose_name = _('Closing Rule')
        verbose_name_plural = _('Closing Rules')
        ordering = ['start']

    contract = models.ForeignKey(MaintenanceContract, verbose_name=_('MaintenanceContract'))
    start = models.DateTimeField(_('Start'))
    end = models.DateTimeField(_('End'))
    reason = models.TextField(_('Reason'), null=True, blank=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return _("%(contract)s is closed from %(start)s to %(end)s\
        due to %(reason)s") % {
            'contract': self.contract.name,
            'start': str(self.start),
            'end': str(self.end),
            'reason': self.reason
        }



