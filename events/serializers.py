from rest_framework import serializers


class ErrorByTimeValues(serializers.Serializer):
    insertion_time = serializers.DateTimeField(help_text="Time at which the event was logged")
    event_name = serializers.CharField(help_text="Type of the event that occurred")
    event_time = serializers.DateTimeField(help_text="Time at which event occurred actually")
    event_code = serializers.CharField(help_text="Actual event code")
    source_name = serializers.CharField(help_text="The name of the source")
    source_key = serializers.CharField(help_text="The key value of the source")


class PlantErrorByTimeValues(serializers.Serializer):
	plant_slug = serializers.CharField(help_text="The slug value of plant")
	plant_name = serializers.CharField(help_text="The name of plant")
	total_inverters = serializers.IntegerField(help_text="Total no of inverters associated with this plant")
	no_of_inverters_affected = serializers.IntegerField(help_text="Number of inverters on which event occurred")
	events = ErrorByTimeValues(many=True, help_text="The list of events for different inverters")