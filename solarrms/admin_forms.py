from django import forms
from solarrms.models import SolarPlant
from django.contrib.admin import widgets


class AddInverterForm(forms.Form):

    solar_plant = forms.ChoiceField()
    solar_group = forms.ChoiceField()
    total_capacity = forms.CharField()
    actual_capacity = forms.CharField()
    manufacturer = forms.CharField()
    model = forms.CharField()
    total_number_inverters = forms.IntegerField()


class AddMeterForm(forms.Form):

    solar_plant = forms.ChoiceField()
    solar_group = forms.ChoiceField()
    manufacturer = forms.CharField()
    model = forms.CharField()
    energy_calculation = forms.BooleanField(initial=False)
    total_number_meter = forms.IntegerField()


class MultiplicationFactorForm(forms.Form):

    solar_plant = forms.ChoiceField()
    solar_group = forms.MultipleChoiceField()
    source_key = forms.MultipleChoiceField()
    source_streams = forms.MultipleChoiceField(widget=widgets.FilteredSelectMultiple("Streams", is_stacked=False))
    multiplication_factor = forms.CharField()
    stream_data_type = forms.ChoiceField(choices=[["", "--------------"],
                                                  ["TIMESTAMP", "TIMESTAMP"],
                                                  ["FLOAT", "FLOAT"],
                                                  ["STRING", "STRING"]], initial="")
    change_display_name = forms.CharField()

class AddAJBForm(forms.Form):

    solar_plant = forms.ChoiceField()
    solar_group = forms.ChoiceField()
    inverters = forms.ChoiceField()
    manufacturer = forms.CharField()
    display_name = forms.CharField()
    total_number_abjs = forms.IntegerField()


class AddClientAndPlantForm(forms.Form):

    email_as_user_name = forms.EmailField()
    password = forms.CharField()
    first_name = forms.CharField()
    last_name = forms.CharField()

    client_name = forms.CharField()
    is_active = forms.BooleanField(initial=True)
    client_slug = forms.CharField()
    client_website = forms.CharField()
    dashboard = forms.ChoiceField(choices=[["1","SOLAR"]])
    can_create_groups = forms.BooleanField(initial=True)


class AddSolarFieldFrom(forms.Form):

    solar_plant = forms.ChoiceField()
    solar_group = forms.MultipleChoiceField()
    source_key = forms.MultipleChoiceField()
    stream_name = forms.CharField()
    stream_display_name = forms.CharField()
    multiplication_factor = forms.CharField(initial=1)


class AddPayloadErrorCheckFrom(forms.Form):

    solar_plant = forms.ChoiceField()
    solar_group = forms.ChoiceField()
    source_key = forms.ChoiceField()
    source_key_string = forms.CharField()
    data_write_payload = forms.CharField(widget=forms.Textarea)


class ResetPassword(forms.Form):

    email = forms.CharField()
    new_password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
