from django import forms

class JPlug_Upload_Form(forms.Form):
    macaddress = forms.CharField(label='macaddress', max_length=20)
    datapoint = forms.CharField(label='datapoint', max_length=2000)




