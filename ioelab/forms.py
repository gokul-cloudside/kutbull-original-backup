from django import forms
from ioelab.models import ValidUID

class ValidateUIDForm(forms.Form):
    UID = forms.CharField(max_length=12, help_text="Validate UID of IoELab Kit provided on the display")

    def __init__(self, *args, **kwargs):
        super(ValidateUIDForm, self).__init__(*args, **kwargs)
        self.fields['UID'].required = True
        self.fields['UID'].label = "UID of pending device"
        self.fields['UID'].widget = forms.TextInput(attrs={'required': 'true'})

    '''
    class Meta:
        model = ValidateUIDForm
        fields = ['UID']
    '''