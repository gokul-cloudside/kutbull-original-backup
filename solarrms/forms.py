from .models import IndependentInverter, SolarPlant, Feeder, AJB, Inverter
from django import forms
from django.db import IntegrityError
from organizations.utils import create_organization
from django.http import HttpResponseServerError, HttpResponseBadRequest


class SolarPlantAddForm(forms.ModelForm):
    def __init__(self, request, dataglenclient, sensors, *args, **kwargs):
        self.request = request
        self.dataglenclient = dataglenclient
        super(SolarPlantAddForm, self).__init__(*args, **kwargs)
        self.fields['is_active'].label = 'If the customer is active yet'
        self.fields['name'].label = 'The name cannot be changed later.'
        self.fields['groupSensors'].label = 'Add inverters/devices that belong to this customer.'
        self.fields['groupSensors'].queryset = sensors
        self.fields['capacity'].label = 'The capacity of the plant (in KW)'
        self.fields['location'].label = 'Location (eg. Kurnoor, Andhra Pradesh)'
        self.fields['latitude'].label = 'Exact Latitude Coordinates (Optional)'
        self.fields['longitude'].label = 'Exact Longitude Coordinates (Optional)'

    class Meta:
        model = SolarPlant
        fields = ['name', 'is_active', 'groupSensors', 'capacity', 'location', 'latitude', 'longitude']

    def save(self, **kwargs):
        try:
            org_kwargs = {'org_model': SolarPlant}
            org_defaults = {'groupClient': self.dataglenclient,
                            'capacity': self.cleaned_data['capacity'],
                            'location': self.cleaned_data['location'],
                            'latitude': self.cleaned_data['latitude'],
                            'longitude': self.cleaned_data['longitude']}
            solar_plant = create_organization(user=self.request.user, name=self.cleaned_data['name'],
                                              is_active=self.cleaned_data['is_active'],
                                              org_defaults=org_defaults, **org_kwargs)
            # since there's a dataglen_group instance now, we can save many to many relations as well
            for sensor in self.cleaned_data['groupSensors']:
                solar_plant.groupSensors.add(sensor)
            solar_plant.save()
            return solar_plant
        except IntegrityError:
            return HttpResponseBadRequest("The name should be unique.")
        except:
            return HttpResponseServerError("Internal error. Please contact us at contact@dataglen.com")


class IndependentInverterForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(IndependentInverterForm, self).__init__(*args, **kwargs)

        self.fields['name'].widget = forms.TextInput(attrs={'placeholder': 'Inverter Name', 'required': 'true'})

        self.fields['dataReportingInterval'].label = "Data Reporting Interval"
        self.fields['dataReportingInterval'].widget = forms.TextInput(attrs={'placeholder': 'In Seconds.', 'required': 'true'})
        self.fields['dataReportingInterval'].required = False

        self.fields['sourceMacAddress'].required = False
        self.fields['sourceMacAddress'].label = "Source Identifier (e.g. MAC)"
        self.fields['sourceMacAddress'].widget = forms.TextInput(attrs={'placeholder': 'Inverter hardware identifier. Optional.'})

        self.fields['timeoutInterval'].label = "Monitoring timeout interval (in seconds)"
        self.fields['dataTimezone'].label = "Data Timezone"

    class Meta:
        model = IndependentInverter
        fields = ['name', 'manufacturer', 'dataReportingInterval', 'sourceMacAddress', 'isActive',
                  'isMonitored', 'timeoutInterval', 'dataTimezone']


class FeederForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FeederForm, self).__init__(*args, **kwargs)
        
        self.fields['name'].widget = forms.TextInput(attrs={'placeholder': 'Feeder Name', 'required': 'true'})
        
        self.fields['dataReportingInterval'].label = "Data Reporting Interval"
        self.fields['dataReportingInterval'].widget = forms.TextInput(attrs={'placeholder': 'In Seconds.', 'required': 'true'})
        self.fields['dataReportingInterval'].required = False

        self.fields['sourceMacAddress'].required = False
        self.fields['sourceMacAddress'].label = "Source Identifier (e.g. MAC)"
        self.fields['sourceMacAddress'].widget = forms.TextInput(attrs={'placeholder': 'Feeder hardware identifier. Optional.'})

        self.fields['timeoutInterval'].label = "Monitoring timeout interval (in seconds)"
        self.fields['dataTimezone'].label = "Data Timezone"

    class Meta:
        model = Feeder
        fields = ['name', 'manufacturer', 'dataReportingInterval', 'sourceMacAddress', 'isActive',
                  'isMonitored', 'timeoutInterval', 'dataTimezone']


class AJBForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(AJBForm, self).__init__(*args, **kwargs)
        
        self.fields['name'].widget = forms.TextInput(attrs={'placeholder': 'AJB Name', 'required': 'true'})
        
        self.fields['dataReportingInterval'].label = "Data Reporting Interval"
        self.fields['dataReportingInterval'].widget = forms.TextInput(attrs={'placeholder': 'In Seconds.', 'required': 'true'})
        self.fields['dataReportingInterval'].required = False

        self.fields['sourceMacAddress'].required = False
        self.fields['sourceMacAddress'].label = "Source Identifier (e.g. MAC)"
        self.fields['sourceMacAddress'].widget = forms.TextInput(attrs={'placeholder': 'Feeder hardware identifier. Optional.'})

        self.fields['timeoutInterval'].label = "Monitoring timeout interval (in seconds)"
        self.fields['dataTimezone'].label = "Data Timezone"

    class Meta:
        model = AJB
        fields = ['name', 'manufacturer', 'dataReportingInterval', 'sourceMacAddress', 'isActive',
                  'isMonitored', 'timeoutInterval', 'dataTimezone']


class InverterForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(InverterForm, self).__init__(*args, **kwargs)

        self.fields['name'].widget = forms.TextInput(attrs={'placeholder': 'Inverter Name', 'required': 'true'})

        self.fields['dataReportingInterval'].label = "Data Reporting Interval"
        self.fields['dataReportingInterval'].widget = forms.TextInput(attrs={'placeholder': 'In Seconds.', 'required': 'true'})
        self.fields['dataReportingInterval'].required = False

        self.fields['sourceMacAddress'].required = False
        self.fields['sourceMacAddress'].label = "Source Identifier (e.g. MAC)"
        self.fields['sourceMacAddress'].widget = forms.TextInput(attrs={'placeholder': 'Inverter hardware identifier. Optional.'})

        self.fields['timeoutInterval'].label = "Monitoring timeout interval (in seconds)"
        self.fields['dataTimezone'].label = "Data Timezone"

    class Meta:
        model = Inverter
        fields = ['name', 'manufacturer', 'dataReportingInterval', 'sourceMacAddress', 'isActive',
                  'isMonitored', 'timeoutInterval', 'dataTimezone']


