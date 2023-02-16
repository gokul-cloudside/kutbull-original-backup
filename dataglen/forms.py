from django import forms
from dataglen.models import Sensor, Field
from captcha.fields import ReCaptchaField
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class SensorForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(SensorForm, self).__init__(*args, **kwargs)

        self.fields['name'].widget = forms.TextInput(attrs={'placeholder': 'Name of the data source', 'required': 'true',})

        self.fields['dataReportingInterval'].label = "Data Reporting Interval"
        self.fields['dataReportingInterval'].widget = forms.TextInput(attrs={'placeholder': 'In Seconds.', 'required': 'true'})
        self.fields['dataReportingInterval'].required = False

        self.fields['sourceMacAddress'].required = False
        self.fields['sourceMacAddress'].label = "Source Identifier (e.g. MAC)"
        self.fields['sourceMacAddress'].widget = forms.TextInput(attrs={'placeholder': 'MAC address of the source. Optional.'})

        self.fields['dataFormat'].label = "Data Format"

        self.fields['textMessageWithHTTP200'].label = "Response Text with HTTP 200 OK"
        self.fields['textMessageWithHTTP200'].widget = forms.TextInput(attrs={'placeholder': 'Message to be sent with a 200 OK. Optional'})
        self.fields['textMessageWithHTTP200'].required = False

        self.fields['textMessageWithError'].label = "Response Text in case of an error."
        self.fields['textMessageWithError'].widget = forms.TextInput(attrs={'placeholder': 'It should be left blank if actual error code is expected in response. '})
        self.fields['textMessageWithError'].required = False

        self.fields['csvDataKeyName'].label = "Name of the key holding CSV data"
        self.fields['csvDataKeyName'].widget = forms.TextInput(attrs={'placeholder': 'Leave it blank if there is none.'})
        self.fields['csvDataKeyName'].required = False

        self.fields['timeoutInterval'].label = "Monitoring timeout interval (in seconds)"
        self.fields['dataTimezone'].label = "Data Timezone"

    def clean_UID(self):
        UID_value = self.cleaned_data.get('UID',None)
        if UID_value and UID_value != '':
            try:
                Sensor.objects.get(UID=UID_value)
            except ObjectDoesNotExist:
                return UID_value
            raise ValidationError(('UID already exists: %(value)s'),
                                code='invalid',
                                params={'value': UID_value})

    class Meta:
        model = Sensor
        fields = ['name', 'dataReportingInterval', 'sourceMacAddress', 'dataFormat','UID',
                  'textMessageWithHTTP200', 'textMessageWithError', 'isActive', 'actuationEnabled',
                  'csvDataKeyName', 'isMonitored', 'timeoutInterval', 'dataTimezone']


class FieldForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FieldForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget = forms.TextInput(attrs={'placeholder': 'Name of the DataStream', 'required': 'true'})
        self.fields['streamDataType'].required = True

        self.fields['streamDateTimeFormat'].label = "Date/Time fields format."
        self.fields['streamDateTimeFormat'].required = False

        # TODO check the availability of position field for a CSV format sensor
        # will be displayed only if the sensor data format is CSV.
        self.fields['streamPositionInCSV'].widget = forms.TextInput(attrs={'placeholder': 'Position of the stream'})
        self.fields['streamPositionInCSV'].required = False

        self.fields['streamDataUnit'].widget = forms.TextInput(attrs={'placeholder': 'Data unit (Optional)'})

    class Meta:
        model = Field
        exclude = ['source', ]

class TemplateForm(forms.Form):
    template_id = forms.ChoiceField()
    def __init__(self, *args, **kwargs):
        super(TemplateForm, self).__init__(*args, **kwargs)
        self.fields['template_id'] = forms.ChoiceField(choices=[(template.id, template.name) for template in Sensor.objects.filter(isTemplate=True)])

class DataViewForm(forms.Form):
    sensor_name = forms.ChoiceField()
    streams = forms.CheckboxSelectMultiple()
    start_time = forms.DateTimeField(label="", input_formats=["%Y/%m/%d %H:%M"], required=True,
                                     widget=forms.TextInput(attrs={'class':'date_time_input_data', 'placeholder': 'Start Time'}))
    end_time  = forms.DateTimeField(label="", input_formats=["%Y/%m/%d %H:%M"], required=True,
                                    widget=forms.TextInput(attrs={'class':'date_time_input_data', 'placeholder': 'End Time'}))
    def __init__(self, user, *args, **kwargs):
        super(DataViewForm, self).__init__(*args, **kwargs)
        self.fields['sensor_name'] = forms.ChoiceField(label="", choices=[(sensor.id, sensor.name) for sensor in Sensor.objects.filter(user=user, isTemplate=False)])

# TODO remove this later.
class JplugUploadForm(forms.Form):
    macaddress = forms.CharField(label='macaddress', max_length=20)
    datapoint = forms.CharField(label='datapoint', max_length=2000)


class SignupForm(forms.Form):
    captcha = ReCaptchaField()
    first_name = forms.CharField(max_length=30, label='First Name')
    last_name = forms.CharField(max_length=30, label='Last Name')

    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()

