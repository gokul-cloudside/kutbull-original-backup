from django import forms
from organizations.models import get_user_model
from django.utils.translation import ugettext_lazy as _
from organizations.forms import OrganizationUserAddForm
from .models import DataglenGroup
from organizations.utils import create_organization
from django.db import IntegrityError
from django.http import HttpResponseServerError, HttpResponseBadRequest
from .utils import filter_owned_orgs
import logging
from dataglen.models import Sensor
from utils import is_owner, is_employee, is_member
from django.http import HttpResponseBadRequest, HttpResponseServerError

logger = logging.getLogger('dataglen.views')
logger.setLevel(logging.DEBUG)


def already_member(user):
    status_owner, org = is_owner(user)
    if status_owner is True:
        return True
    status_employee, org = is_employee(user)
    if status_employee is True:
        return True
    status_member, org = is_member(user)
    if status_member is True:
        return True

    return False

class EmployeeAddForm(OrganizationUserAddForm):
    def __init__(self, request, organization, *args, **kwargs):
        super(EmployeeAddForm, self).__init__(request, organization, *args, **kwargs)
        self.fields['is_admin'].label = 'Administrator [allowed to create new customers/groups]'

    def clean(self):
        try:
            user = get_user_model().objects.get(email__iexact=self.cleaned_data['email'])
            if already_member(user) is True:
                raise forms.ValidationError(_("A user with this email address is already "
                                              "associated with a different organization."))
        except:
            pass

    def save(self, *args, **kwargs):
        return super(EmployeeAddForm, self).save(args, kwargs)


class MemberAddForm(OrganizationUserAddForm):
    selected_group = forms.ChoiceField()

    def __init__(self, request, organization, groups, *args, **kwargs):
        super(MemberAddForm, self).__init__(request, organization, *args, **kwargs)
        self.fields['is_admin'].widget = forms.HiddenInput()
        self.fields['selected_group'] = forms.ChoiceField(label="Select a group/customer this member should be added to",
                                                          choices=[(group.id, group.slug) for group in groups])

    def clean(self):
        try:
            user = get_user_model().objects.get(email__iexact=self.cleaned_data['email'])
            if already_member(user) is True:
                raise forms.ValidationError(_("A user with this email address is already "
                                              "associated with a different organization."))
        except:
            pass

    def save(self, *args, **kwargs):
        self.organization = DataglenGroup.objects.get(id=self.cleaned_data['selected_group']).organization_ptr
        return super(MemberAddForm, self).save(args, kwargs)


class DataglenGroupAddForm(forms.ModelForm):
    def __init__(self, request, dataglenclient, sensors, *args, **kwargs):
        self.request = request
        self.dataglenclient = dataglenclient
        super(DataglenGroupAddForm, self).__init__(*args, **kwargs)
        self.fields['is_active'].label = 'If the customer/group is active yet'
        self.fields['name'].label = 'Name cannot be changed later.'
        self.fields['groupSensors'].label = 'Add devices that belong to this customer.'
        self.fields['groupSensors'].queryset = sensors

    class Meta:
        model = DataglenGroup
        fields = ['name', 'is_active', 'groupSensors']

    def save(self, **kwargs):
        try:
            org_kwargs = {'org_model': DataglenGroup}
            org_defaults = {'groupClient': self.dataglenclient}
            dataglen_group = create_organization(user=self.request.user, name=self.cleaned_data['name'],
                                       is_active=self.cleaned_data['is_active'],
                                       org_defaults=org_defaults, **org_kwargs)
            # since there's a dataglen_group instance now, we can save many to many relations as well
            for sensor in self.cleaned_data['groupSensors']:
                dataglen_group.groupSensors.add(sensor)
            dataglen_group.save()
            return dataglen_group
        except IntegrityError:
            return HttpResponseBadRequest("The name should be unique.")
        except:
            return HttpResponseServerError("Internal error. Please contact us at contact@dataglen.com")
