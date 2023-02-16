from django import forms

class IndexForm(forms.Form):
    premise_name = forms.CharField(label="Premise:", max_length=100, required=True)
    load_name = forms.CharField(label="Load:", max_length=100, required=True)
    start_date = forms.DateField(label='Start Date:', required=True)
    end_date = forms.DateField(label='End Date:', required=True)

class LiveForm(forms.Form):
    premise_name = forms.CharField(max_length=100, required=True)
    load_name = forms.CharField(max_length=100, required=True)
    start_time = forms.DateField(required=True)
    end_time = forms.DateField(required=True)
