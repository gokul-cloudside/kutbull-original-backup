from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _
from django.db import models
from dashboards.models import DataglenClient, DataglenGroup
from solarrms.models import SolarPlant
from django.db.models import Q
from django.core.exceptions import ValidationError
from solarrms2.settings import currency_choices
from helpdesk.models import EVENT_TYPE


EVENT_TYPE.append(('OANDM_TASK', 'OANDM_TASK'))

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

# set the Priority values
PRIORITY_VALUES = ['LOW', 'MEDIUM', 'HIGH', 'URGENT', 'COMMUNICATION ERROR', 'INFORMATION', 'NO ALERT']
PRIORITY = zip(PRIORITY_VALUES, PRIORITY_VALUES)


# a model that stores the bill related information
# for a DataGlenClient (Ranergy, Cleanmax etc.),
# does not need to be a dataglengroup as that information is already available
class BillingEntity(models.Model):

    # company details
    dataglen_client = models.OneToOneField(DataglenClient, related_name="billing_entity")
    registered_name = models.CharField(max_length=100, null=False, blank=False)
    registered_office_address = models.TextField(blank=False, null=False)
    cin_number = models.CharField(max_length=100, null=True, blank=True)
    email = models.CharField(max_length=100, null=False, blank=False)
    tel_number = models.CharField(max_length=100, null=False, blank=False)
    website_address = models.CharField(max_length=100, null=False, blank=False)

    # tax details
    tax_details_primary = models.CharField(max_length=100, null=True, blank=True)
    tax_details_secondary = models.CharField(max_length=100, null=True, blank=True)


class BankAccount(models.Model):
    billing_entity = models.ForeignKey(BillingEntity, related_name="accounts", null=True, blank=True)
    # bank details
    account_bank = models.CharField(max_length=50, null=False, blank=False)
    beneficiary_name =  models.CharField(max_length=50, null=False, blank=False)
    account_number = models.CharField(max_length=50, null=False, blank=False)
    account_ifsc_code = models.CharField(max_length=50, null=False, blank=False)
    bank_address = models.TextField(null=False, blank=False)
    account_micr_code = models.CharField(max_length=50, null=False, blank=False)
    account_branch_code = models.CharField(max_length=50, null=False, blank=False)


# an off taker of electricity from a dataglen client, this guy will be billed for monthly consumption etc.
# relationship with dataglen clinet and logo etc. will be used from dataglengroup
class EnergyOffTaker(DataglenGroup):
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


# energy contracts
class EnergyContract(models.Model):
    # start date of the contract
    start_date = models.DateField(blank=False, null=False)
    # end date of the contract
    end_date = models.DateField(blank=False, null=False)
    # plant for which the contract is, there can be multiple
    plant = models.ForeignKey(SolarPlant, blank=False, null=False, related_name="energy_contract")
    # off taker/client
    off_taker = models.ForeignKey(EnergyOffTaker, blank=False, null=False, related_name="energy_contract")
    # ppa price
    ppa_price = models.FloatField(blank=False, null=False)
    # currency
    currency = models.CharField(choices=currency_choices,
                                blank=False, null=False, max_length=10)
    # late payment penalty
    late_payment_penalty_clause = models.TextField(null=False, blank=False)
    # early payment days
    early_payment_offset_days = models.IntegerField(blank=True, null=True)
    # early payment discount factor
    early_payment_discount_factor = models.FloatField(blank=True, null=True)
    #
    contact_name = models.CharField(max_length=50, blank=True, null=True)

    def clean(self):
        # it's a new instance
        existing_contract = EnergyContract.objects.filter(Q(start_date__gte=self.start_date,
                                                            end_date__lte=self.start_date,
                                                            plant=self.plant,
                                                            off_taker=self.off_taker) |
                                                          Q(start_date__gte=self.end_date,
                                                            end_date__lte=self.end_date,
                                                            plant=self.plant,
                                                            off_taker=self.off_taker) |
                                                          Q(start_date__gte=self.start_date,
                                                            end_date__lte=self.end_date,
                                                            plant=self.plant,
                                                            off_taker=self.off_taker) |
                                                          Q(start_date__lte=self.start_date,
                                                            end_date__gte=self.end_date,
                                                            plant=self.plant,
                                                            off_taker=self.off_taker))
        if len(existing_contract) > 0:
            raise ValidationError("There is already a contract with this "
                                  "plant and off taker that overlaps with the mentioned period")
        return


# Set priorities mappings for a client
class SolarEventsPriorityMapping(models.Model):
    # dataglen client for which these priorities are, 1 set for each client
    client = models.ForeignKey(DataglenClient, related_name="events_priorities")
    # event type - should include all the events
    event_type = models.CharField(choices=EVENT_TYPE, blank=False, null=False, max_length=100)
    # priority value
    priority = models.CharField(choices=PRIORITY, blank=False, null=False, max_length=100)
    # html color code, if that needs to be added later
    html_color_code = models.CharField(blank=True, null=True, max_length=100)

    class Meta:
        unique_together = (('client', 'event_type', 'priority'), ('client', 'event_type', 'html_color_code'))

    def __unicode__(self):
        return "_".join([str(self.client),
                         str(self.event_type),
                         str(self.priority)])
