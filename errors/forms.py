from django import forms
from dataglen.models import Sensor
from .models import ErrorField
from captcha.fields import ReCaptchaField
from django.core.exceptions import ObjectDoesNotExist, ValidationError

class ErrorFieldForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ErrorFieldForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget = forms.TextInput(attrs={'placeholder': 'Name of the Error DataStream', 'required': 'true'})
        self.fields['streamDataType'].required = True
        self.fields['streamDateTimeFormat'].label = "Date/Time fields format."
        self.fields['streamDateTimeFormat'].required = False

        # TODO check the availability of position field for a CSV format sensor
        # will be displayed only if the sensor data format is CSV.
        self.fields['streamPositionInCSV'].widget = forms.TextInput(attrs={'placeholder': 'Position of the stream'})
        self.fields['streamPositionInCSV'].required = False

        self.fields['streamDataUnit'].widget = forms.TextInput(attrs={'placeholder': 'Data unit (Optional)'})

    class Meta:
        model = ErrorField
        exclude = ['source', ]