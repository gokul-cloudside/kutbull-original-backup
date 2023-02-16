from solarrms.models import SolarPlant, IndependentInverter
from rest_framework import serializers
from .settings import AGGREGATOR_CHOICES
from helpdesk.models import Ticket, FollowUp, TicketChange, TicketAssociation




class PlantSerializer(serializers.ModelSerializer):
    total_inverters = serializers.IntegerField(help_text="Total Independent Inverters at the plant",
                                               required=False, read_only=True)
    connected_inverters = serializers.IntegerField(help_text="Total Connected Inverters at the plant",
                                                   required=False, read_only=True)
    disconnected_inverters = serializers.IntegerField(help_text="Total Disconnected Inverters at the plant",
                                                      required=False, read_only=True)
    current_power = serializers.FloatField(help_text="The most recent power value reported in the last 10 minutes",
                                   required=False, read_only=True)
    today_generation = serializers.FloatField(help_text="Energy generated at the plant today",
                                               required=False, read_only=True)
    timezone = serializers.CharField(help_text="Time zone of the plant",
                                               required=False, read_only=True)

    class Meta:
        model = SolarPlant
        fields = ('name',
                  'slug',
                  'capacity',
                  'location',
                  'latitude',
                  'longitude',
                  'total_inverters',
                  'connected_inverters',
                  'disconnected_inverters',
                  'current_power',
                  'today_generation',
                  'timezone',
                  'id'
                  )


class InverterSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndependentInverter
        fields = ('name',
                  'sourceKey',
                  'manufacturer',
                  'dataReportingInterval',
                  'sourceMacAddress',
                  'isActive',
                  'isMonitored',
                  'timeoutInterval',
                  'dataTimezone',
                  'orientation',
                  'total_capacity',
                  'actual_capacity'
                 )


class InverterStreamDataValues(serializers.Serializer):
    name = serializers.CharField(help_text="Stream name")
    values = serializers.ListField(child=serializers.CharField(),
                                   help_text="Stream values at the given timestamps")
    timestamps = serializers.ListField(child=serializers.DateTimeField(),
                                       help_text="The timestamps at which data was reported")

class InverterDataValues(serializers.Serializer):
    sourceKey = serializers.CharField(help_text="The key value of the inverter")
    streams = InverterStreamDataValues(many=True)
    

class EnergyDataQuery(serializers.Serializer):
    startTime = serializers.DateTimeField(help_text="Start time of the energy data lookup")
    endTime = serializers.DateTimeField(help_text="End time of the energy data lookup")
    aggregator = serializers.ChoiceField(choices=AGGREGATOR_CHOICES)


class EnergyDataValues(serializers.Serializer):
    energy = serializers.CharField(help_text="Energy value")
    pvsyst_generation = serializers.CharField(help_text="PVSyst Energy Value", required=False)
    predicted_energy = serializers.CharField(help_text="Predicted Energy Value", required=False)
    lower_bound = serializers.CharField(help_text="Lower bound", required=False)
    upper_bound = serializers.CharField(help_text="Upper bound", required=False)
    timestamp = serializers.DateTimeField(help_text="Timestamp")

class PowerDataValues(serializers.Serializer):
    power = serializers.FloatField(help_text="Power value")
    timestamp = serializers.DateTimeField(help_text="Timestamp")


class PerformanceRatioValues(serializers.Serializer):
    performance_ratio = serializers.FloatField(help_text="Performance Ratio Values")
    pvsyst_pr = serializers.FloatField(help_text="Expected PR value", required=False)
    timestamp = serializers.DateTimeField(help_text="Timestamp")

class SpecificYieldValues(serializers.Serializer):
    specific_yield = serializers.FloatField(help_text="Specific Yield Values")
    pvsyst_specific_yield = serializers.FloatField(help_text="Expected specific yield value", required=False)
    timestamp = serializers.DateTimeField(help_text="Timestamp")

class CUFValueSerializer(serializers.Serializer):
    cuf = serializers.FloatField(help_text="CUF Values")
    timestamp = serializers.DateTimeField(help_text="Timestamp")

class InverterErrors(serializers.Serializer):
    error_code = serializers.CharField(required=False)
    timestamp = serializers.DateTimeField(required=False)

class InverterLatestStatus(serializers.Serializer):
    status = serializers.CharField(required=False)
    timestamp = serializers.DateTimeField(required=False)

class InverterStatus(serializers.Serializer):
    name = serializers.CharField(required=False)
    generation = serializers.CharField(required=False)
    power = serializers.FloatField(required=False)
    connected = serializers.CharField(required=False)
    key = serializers.CharField(required=False)
    orientation = serializers.CharField(required=False)
    capacity = serializers.CharField(required=False)
    solar_group = serializers.CharField(required=False)
    inside_temperature = serializers.CharField(required=False)
    total_yield = serializers.CharField(required=False)
    total_ajbs = serializers.IntegerField(required=False)
    disconnected_ajbs = serializers.IntegerField(required=False)
    last_three_errors = InverterErrors(required=False, many=True)
    last_inverter_status = InverterLatestStatus(required=False, many=True)
    last_timestamp = serializers.CharField(required=False)

class InverterStatusAJB(serializers.Serializer):
    name = serializers.CharField(required=False)
    generation = serializers.FloatField(required=False)
    power = serializers.FloatField(required=False)
    connected = serializers.CharField(required=False)
    key = serializers.CharField(required=False)
    orientation = serializers.CharField(required=False)
    capacity = serializers.FloatField(required=False)
    solar_group = serializers.CharField(required=False)
    inside_temperature = serializers.FloatField(required=False)
    total_yield = serializers.FloatField(required=False)
    total_ajbs = serializers.IntegerField(required=False)
    disconnected_ajbs = serializers.IntegerField(required=False)
    # total_dc_generation_ajbs = serializers.FloatField(required=False, allow_null=True)
    # total_dc_generation_inverter = serializers.FloatField(required=False, allow_null=True)
    # total_ac_generation_inverter = serializers.FloatField(required=False, allow_null=True)
    # dc_losses_percent = serializers.FloatField(required=False, allow_null=True)
    # conversion_loss_percent = serializers.FloatField(required=False, allow_null=True)
    total_ajb_power = serializers.FloatField(required=False)
    inverter_dc_power = serializers.FloatField(required=False)
    inverter_ac_power = serializers.FloatField(required=False)
    last_three_errors = InverterErrors(required=False, many=True)
    last_inverter_status = InverterLatestStatus(required=False, many=True)

class AJB_SPD_Status(serializers.Serializer):
    spd_status = serializers.CharField(required=False)
    timestamp = serializers.DateTimeField(required=False)

class AJB_DC_Isolator_Status(serializers.Serializer):
    dc_isolator_status = serializers.CharField(required=False)
    timestamp = serializers.DateTimeField(required=False)

class AJBStatus(serializers.Serializer):
    name = serializers.CharField(required=False)
    power = serializers.FloatField(required=False)
    current = serializers.FloatField(required=False)
    voltage = serializers.FloatField(required=False)
    connected = serializers.CharField(required=False)
    key = serializers.CharField(required=False)
    inverter_name = serializers.CharField(required=False)
    solar_group = serializers.CharField(required=False)
    last_spd_status = AJB_SPD_Status(required=False, many=True)
    last_dc_isolator_status = AJB_DC_Isolator_Status(required=False, many=True)


class PlantStatusSummary(serializers.Serializer):
    irradiation = serializers.FloatField(help_text="Irradiation value", required=False)
    ambient_temperature = serializers.FloatField(help_text="Ambient Temperature", required=False)
    module_temperature = serializers.FloatField(required=False)
    windspeed = serializers.FloatField(required=False)
    current_power = serializers.FloatField(required=False)
    plant_generation_today = serializers.CharField(required=False)
    performance_ratio = serializers.FloatField(required=False)
    cuf = serializers.FloatField(required=False)
    pvsyst_generation = serializers.CharField(required=False)
    pvsyst_pr = serializers.FloatField(required=False)
    pvsyst_tilt_angle = serializers.FloatField(required=False)
    inverters = InverterStatus(many=True, required=False)
    unacknowledged_tickets = serializers.IntegerField(required=False)
    open_tickets = serializers.IntegerField(required=False)
    closed_tickets = serializers.IntegerField(required=False)
    total_group_number = serializers.IntegerField(required=False)
    solar_groups = serializers.ListField(required=False)
    plant_capacity = serializers.CharField(required=False)
    plant_name = serializers.CharField(required=False)
    plant_location = serializers.CharField(required=False)
    plant_total_energy = serializers.CharField(required=False)
    plant_co2 = serializers.CharField(required=False)

class PlantClientSummary(serializers.Serializer):
    total_energy = serializers.CharField()
    energy_today = serializers.CharField()
    total_capacity = serializers.CharField(required=False)
    total_co2 = serializers.CharField()
    plants = PlantStatusSummary(many=True)

class TicketPatchSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ticket
        fields = (
            'id',
            'title',
            'queue',
            'created',
            'modified',
            'submitter_email',
            'assigned_to',
            'status',
            'description',
            'resolution',
            'priority',
            'due_date',
            'last_escalation'

        )

class AssociationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketAssociation
        fields = (
            'id',
            'identifier',
            'identifier_name',
            'active',
            'created',
            'comment1',
            'comment2',
            'comment3',
            'comment4',
            'title',
            'description'
        )
    id = serializers.IntegerField(required=True)
    comment1 = serializers.CharField(required=False)
    comment2 = serializers.CharField(required=False)
    comment3 = serializers.CharField(required=False)
    comment4 = serializers.CharField(required=False)
    title = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)

class TicketSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="id of the ticket")
    title = serializers.CharField(help_text="title of the serializer", required=False)
    queue = serializers.CharField(help_text="Queue to which the ticket is associated to")
    modified = serializers.DateTimeField(help_text="last time at which the ticket was modified", required=False)
    created = serializers.DateTimeField(help_text="time at which the ticket was created", required=False)
    submitter_email = serializers.CharField(help_text="email id of the submitter of ticket", required=False)
    assigned_to = serializers.CharField(help_text="user to which the ticket is assigned to", required=False)
    status = serializers.CharField(help_text="current status of the ticket")
    description = serializers.CharField(help_text="description of the ticket", required=False)
    resolution = serializers.CharField(help_text="resolution of the ticket", required=False)
    priority = serializers.CharField(help_text="Priority of the ticket")
    due_date = serializers.CharField(help_text="Due date of the ticket", required=False)
    last_escalation = serializers.DateTimeField(help_text="last esclation date", required=False)
    total_associations = serializers.IntegerField(help_text="Total associations of the ticket", required=False)
    active_associations = serializers.IntegerField(help_text="Total active associations of the ticket", required=False)
    ticket_type = serializers.CharField(help_text="ticket type", required=True)
    active_associations = serializers.IntegerField(help_text="total active associations for the ticket", required=False)
    association_details = AssociationsSerializer(required=False, many=True)

class FollowUpSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    date = serializers.CharField(required=False)
    title = serializers.CharField(required=False)
    comment = serializers.CharField(required=False)
    public = serializers.BooleanField(required=False)
    user = serializers.CharField(required=False)
    new_status = serializers.CharField(required=False)

class TicketChangeSerializer(serializers.ModelSerializer):

    class Meta:
        model = TicketChange
        fields = (
            'followup',
            'field',
            'old_value',
            'new_value'
        )

class FollowUpTicketChangeSerializer(serializers.Serializer):
    followups = FollowUpSerializer(many=True)
    ticket_changes = TicketChangeSerializer(many=True)

class TicketAssociationsSerializer(serializers.Serializer):
    ticket = TicketSerializer(many=False)
    associations = AssociationsSerializer(many=True)


class EnergyLossValues(serializers.Serializer):
    dc_energy_calculated_from_ajbs = serializers.CharField(help_text="DC Energy calculated from AJB's")
    dc_energy_calculated_from_inverters = serializers.CharField(help_text="DC Energy calculated from Inverters")
    ac_energy_calculated_from_inverters = serializers.CharField(help_text="AC Energy calculated from Inverters")
    ac_energy_calculated_from_energy_meters = serializers.CharField(help_text="AC Energy calculated from Energy meters")
    dc_energy_loss = serializers.CharField(help_text="DC Energy Loss")
    conversion_loss = serializers.CharField(help_text="Conversion Loss")
    ac_energy_loss = serializers.CharField(help_text="AC Energy Loss")
    timestamp = serializers.DateTimeField(help_text="Timestamp")

class V1_PastGenerations(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    pvsyst_generation = serializers.CharField(required=False)
    energy = serializers.CharField()

class V1_PastPR(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    pr = serializers.FloatField()

class V1_PastSpecificYield(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    specific_yield = serializers.FloatField()

class V1_PastCUF(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    cuf = serializers.FloatField()

class V1_PastUnAvailability(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    unavailability = serializers.CharField()

class V1_Past_DC_Loss(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    dc_energy_loss = serializers.CharField()

class V1_Past_Conversion_Loss(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    conversion_loss = serializers.CharField()

class V1_Past_AC_Loss(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    ac_energy_loss = serializers.CharField()

class V1_Past_Months_Generation(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    energy = serializers.CharField()

class V1_Past_KWH_Per_Meter_Square(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    kwh_value = serializers.CharField()

class V1_Current_Inverter_Error(serializers.Serializer):
    plant_name = serializers.CharField(required=False)
    affected_inverters_number = serializers.IntegerField(required=False)
    ticket_url = serializers.CharField(required=False)

class V1_Current_Cleaning(serializers.Serializer):
    plant_name = serializers.CharField(required=False)
    inverters_required_cleaning_numbers = serializers.IntegerField(required=False)
    ticket_url = serializers.CharField(required=False)

class V1_Current_SMB_Anomaly_Error(serializers.Serializer):
    plant_name = serializers.CharField(required=False)
    low_anomaly_affected_ajbs_number = serializers.IntegerField(required=False)
    low_anomaly_ticket_url = serializers.CharField(required=False)
    high_anomaly_affected_ajbs_number = serializers.IntegerField(required=False)
    high_anomaly_ticket_url = serializers.CharField(required=False)

class V1_Inverter_Static_Details(serializers.Serializer):
    numbers = serializers.IntegerField(required=False)
    make = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    model = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    capacity = serializers.CharField(required=False, allow_null=True, allow_blank=True)

class V1_Panel_static_Details(serializers.Serializer):
    numbers = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    make = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    model = serializers.CharField(required=False,allow_null=True, allow_blank=True)
    capacity = serializers.CharField(required=False,allow_null=True, allow_blank=True)

class V1_PlantStatusSummary(serializers.Serializer):
    plant_name = serializers.CharField(required=False)
    plant_slug = serializers.CharField(required=False)
    plant_logo = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    plant_location = serializers.CharField(required=False)
    plant_capacity = serializers.CharField(required=False)
    latitude = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)
    performance_ratio = serializers.FloatField(required=False)
    specific_yield = serializers.FloatField(required=False)
    cuf = serializers.FloatField(required=False)
    grid_unavailability = serializers.CharField(required=False)
    equipment_unavailability = serializers.CharField(required=False)
    unacknowledged_tickets = serializers.IntegerField(required=False)
    open_tickets = serializers.IntegerField(required=False)
    closed_tickets = serializers.IntegerField(required=False)
    plant_generation_today = serializers.CharField(required=False)
    prediction_deviation = serializers.CharField(required=False)
    today_predicted_energy_value_till_time = serializers.CharField(required=False)
    total_today_predicted_energy_value = serializers.CharField(required=False)
    plant_total_energy = serializers.CharField(required=False)
    plant_co2 = serializers.CharField(required=False)
    current_power = serializers.FloatField(required=False)
    irradiation = serializers.FloatField(required=False)
    connected_inverters = serializers.IntegerField(required=False)
    disconnected_inverters = serializers.IntegerField(required=False)
    invalid_inverters = serializers.IntegerField(required=False)
    connected_smbs = serializers.IntegerField(required=False)
    disconnected_smbs = serializers.IntegerField(required=False)
    invalid_smbs = serializers.IntegerField(required=False)
    string_errors_smbs = serializers.IntegerField(required=False)
    network_up = serializers.CharField(required=False)
    module_temperature = serializers.FloatField(required=False)
    ambient_temperature = serializers.FloatField(required=False)
    windspeed = serializers.FloatField(required=False)
    dc_loss = serializers.CharField(required=False)
    conversion_loss = serializers.CharField(required=False)
    ac_loss = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    pvsyst_generation = serializers.CharField(required=False)
    pvsyst_pr = serializers.FloatField(required=False)
    pvsyst_tilt_angle = serializers.FloatField(required=False)
    updated_at = serializers.DateTimeField(required=False)
    past_generations = V1_PastGenerations(many=True, required=False)
    past_pr = V1_PastPR(many=True, required=False)
    past_specific_yield = V1_PastSpecificYield(many=True, required=False)
    past_cuf = V1_PastCUF(many=True, required=False)
    past_grid_unavailability = V1_PastUnAvailability(many=True, required=False)
    past_equipment_unavailability = V1_PastUnAvailability(many=True, required=False)
    past_dc_loss = V1_Past_DC_Loss(many=True, required=False)
    past_conversion_loss = V1_Past_Conversion_Loss(many=True, required=False)
    past_ac_loss = V1_Past_AC_Loss(many=True, required=False)
    inverters = InverterStatus(many=True, required=False)
    total_group_number = serializers.IntegerField(required=False)
    solar_groups = serializers.ListField(required=False)
    power_irradiation = serializers.ListField(required=False)
    residual = serializers.DictField(required=False)
    plant_current_inverter_error_details = V1_Current_Inverter_Error(many=True, required=False)
    plant_string_anomaly_details = V1_Current_SMB_Anomaly_Error(many=True, required=False)
    plant_inverter_cleaning_details = V1_Current_Cleaning(many=True, required=False)
    total_inverter_error_numbers = serializers.IntegerField(required=False)
    total_low_anomaly_smb_numbers = serializers.IntegerField(required=False)
    total_high_anomaly_smb_numbers = serializers.IntegerField(required=False)
    total_inverter_cleaning_numbers = serializers.IntegerField(required=False)
    past_kwh_per_meter_square = V1_Past_KWH_Per_Meter_Square(many=True, required=False)
    past_monthly_generation = V1_Past_Months_Generation(many=True, required=False)
    inverter_details = V1_Inverter_Static_Details(required=False)
    panel_details = V1_Panel_static_Details(required=False)
    max_power = serializers.FloatField(required=False)
    gateways_disconnected = serializers.IntegerField(required=False)
    gateways_powered_off = serializers.IntegerField(required=False)
    gateways_disconnected_list = serializers.ListField(required=False)
    gateways_powered_off_list = serializers.ListField(required=False)
    gateways_disconnected_ticket = serializers.CharField(required=False)
    gateways_powered_off_ticket = serializers.CharField(required=False)

class V1_PlantClientSummary(serializers.Serializer):
    client_name = serializers.CharField(required=False)
    client_slug = serializers.CharField(required=False)
    client_logo = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    total_capacity = serializers.CharField(required=False)
    total_capacity_past_month = serializers.CharField(required=False)
    total_energy = serializers.CharField(required=False)
    energy_today = serializers.CharField(required=False)
    prediction_deviation = serializers.CharField(required=False)
    today_predicted_energy_value_till_time = serializers.CharField(required=False)
    total_today_predicted_energy_value = serializers.CharField(required=False)
    total_co2 = serializers.CharField(required=False)
    grid_unavailability = serializers.CharField(required=False)
    equipment_unavailability = serializers.CharField(required=False)
    total_pr = serializers.FloatField(required=False)
    total_specific_yield = serializers.FloatField(required=False)
    total_cuf = serializers.FloatField(required=False)
    total_active_power = serializers.FloatField(required=False)
    total_irradiation = serializers.FloatField(required=False)
    total_unacknowledged_tickets = serializers.IntegerField(required=False)
    total_open_tickets = serializers.IntegerField(required=False)
    total_closed_tickets = serializers.IntegerField(required=False)
    total_connected_plants = serializers.IntegerField(required=False)
    total_disconnected_plants = serializers.IntegerField(required=False)
    total_unmonitored_plants = serializers.IntegerField(required=False)
    total_connected_inverters = serializers.IntegerField(required=False)
    total_disconnected_inverters = serializers.IntegerField(required=False)
    total_invalid_inverters = serializers.IntegerField(required=False)
    total_connected_smbs = serializers.IntegerField(required=False)
    total_disconnected_smbs = serializers.IntegerField(required=False)
    total_invalid_smbs = serializers.IntegerField(required=False)
    string_errors_smbs = serializers.IntegerField(required=False)
    client_dc_loss = serializers.CharField(required=False)
    client_conversion_loss = serializers.CharField(required=False)
    client_ac_loss = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    updated_at = serializers.DateTimeField(required=False)
    client_past_generations = V1_PastGenerations(many=True, required=False)
    client_past_pr = V1_PastPR(many=True, required=False)
    client_past_specific_yield = V1_PastSpecificYield(many=True, required=False)
    client_past_cuf = V1_PastCUF(many=True, required=False)
    client_past_grid_unavailability = V1_PastUnAvailability(many=True, required=False)
    client_past_equipment_unavailability = V1_PastUnAvailability(many=True, required=False)
    client_past_dc_loss = V1_Past_DC_Loss(many=True, required=False)
    client_past_conversion_loss = V1_Past_Conversion_Loss(many=True, required=False)
    client_past_ac_loss = V1_Past_AC_Loss(many=True, required=False)
    client_current_inverter_error_details = V1_Current_Inverter_Error(many=True, required=False)
    client_string_anomaly_details = V1_Current_SMB_Anomaly_Error(many=True, required=False)
    client_inverter_cleaning_details = V1_Current_Cleaning(many=True, required=False)
    total_inverter_error_numbers = serializers.IntegerField(required=False)
    total_low_anomaly_smb_numbers = serializers.IntegerField(required=False)
    total_high_anomaly_smb_numbers = serializers.IntegerField(required=False)
    total_inverter_cleaning_numbers = serializers.IntegerField(required=False)
    gateways_disconnected = serializers.IntegerField(required=False)
    gateways_powered_off = serializers.IntegerField(required=False)
    gateways_disconnected_list = serializers.ListField(required=False)
    gateways_powered_off_list = serializers.ListField(required=False)
    plants = V1_PlantStatusSummary(many=True)

class Inverter_DC_SLD(serializers.Serializer):
    name = serializers.CharField(required=False)
    value = serializers.CharField(required=False)

class V1_InverterLiveStatus(serializers.Serializer):
    inverters = InverterStatus(many=True, required=False)
    total_group_number = serializers.IntegerField(required=False)
    solar_groups = serializers.ListField(required=False)
    dc_sld = Inverter_DC_SLD(required=False, many=True)

class V1_AJBLiveStatus(serializers.Serializer):
    ajbs = AJBStatus(many=True, required=False)
    inverter_details = InverterStatusAJB(many=True, required=False)
    total_group_number = serializers.IntegerField(required=False)
    solar_groups = serializers.ListField(required=False)


class V1_MobileClientSummary(serializers.Serializer):
    client_name = serializers.CharField(required=False)
    client_logo = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    total_capacity = serializers.CharField(required=False)
    total_capacity_past_month = serializers.CharField(required=False)
    energy_today = serializers.CharField(required=False)
    total_energy = serializers.CharField(required=False)
    total_active_power = serializers.FloatField(required=False)
    prediction_deviation = serializers.CharField(required=False)
    total_co2 = serializers.CharField(required=False)
    total_connected_plants = serializers.IntegerField(required=False)
    total_disconnected_plants = serializers.IntegerField(required=False)
    total_unmonitored_plants = serializers.IntegerField(required=False)
    total_diesel = serializers.CharField(required=False)
    energy_current_month = serializers.CharField(required=False)
    know_more = serializers.BooleanField(required=False)
