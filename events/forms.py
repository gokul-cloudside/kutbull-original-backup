from .models import UserEventAlertsPreferences
from django import forms
from django.db import IntegrityError
from organizations.utils import create_organization
from django.http import HttpResponseServerError, HttpResponseBadRequest
from .models import Events


class AlertPreferencesForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(AlertPreferencesForm, self).__init__(*args, **kwargs)

        self.fields['alert_active'].label = "Active"
        self.fields['alert_active'].widget = forms.CheckboxInput(attrs={'placeholder': 'Notifications will be sent only if this alert is active',
                                                                        'required': 'true'})
        self.fields['alert_active'].required = True

        self.fields['email_id'].label = "Email Address"
        self.fields['email_id'].widget = forms.TextInput(attrs={'placeholder': 'Email address to which the alert '
                                                                               'emails will be sent',
                                                                'required': 'true'})
        self.fields['email_id'].required = True

        #self.fields['phone_no'].label = "Phone Number"
        #self.fields['phone_no'].widget = forms.TextInput(attrs={'placeholder': 'SMS messages will be sent to this '
        #                                                                       'number', 'required': 'true'})
        #self.fields['phone_no'].required = True

        self.fields['alert_interval'].label = "Time Interval (minutes)"
        self.fields['alert_interval'].widget = forms.TextInput(attrs={'placeholder': 'Time interval between two '
                                                                                     'notifications of this event',
                                                                      'required': 'true'})
        self.fields['alert_interval'].required = True

    class Meta:
        model = UserEventAlertsPreferences
        fields = ['alert_active', 'email_id', 'alert_interval']


class EventChoiceForm(AlertPreferencesForm):
    def __init__(self, *args, **kwargs):
        super(EventChoiceForm, self).__init__(*args, **kwargs)
        
    event_names = Events.objects.all().order_by('event_name')
    Event = forms.ModelChoiceField(event_names)

    class Meta(AlertPreferencesForm.Meta):
        fields = ['Event'] + AlertPreferencesForm.Meta.fields
