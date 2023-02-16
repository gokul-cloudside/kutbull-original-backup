from dataglen.models import Sensor
from .models import ErrorField
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist


class ErrorStreamSerializer(serializers.ModelSerializer):
    source = serializers.ReadOnlyField(source='source.sourceKey', help_text="Key of the source this stream belongs to")
    streamPositionInCSV = serializers.IntegerField(required=False,
                                                   help_text="Applicable only if source dataFormat is CSV, should be unique")

    class Meta:
        model = ErrorField
        fields = ('name',
                  'source',
                  'streamDataType',
                  'streamDataUnit',
                  'streamDateTimeFormat',
                  'streamPositionInCSV',
                  'multiplicationFactor',
                  'isActive',
                  'type')


class StreamDataValues(serializers.Serializer):
    name = serializers.CharField(help_text="Stream name")
    count = serializers.IntegerField(help_text="Data Count")
    startTime = serializers.DateTimeField(help_text="The first timestamp of the returned data", required=False)
    endTime = serializers.DateTimeField(help_text="The last timestamp of the returned data", required=False)
    values = serializers.ListField(child=serializers.CharField(),
                                   help_text="Stream values at the given timestamps")
    timestamps = serializers.ListField(child=serializers.DateTimeField(),
                                       help_text="The timestamps at which data was reported")

class ErrorDataValues(serializers.Serializer):
    sourceKey = serializers.CharField(help_text="The key value of the source")
    streams = StreamDataValues(many=True, help_text="The value of the mentioned error streams")

class ErrorStreamDataValuesLatest(serializers.Serializer):
    name = serializers.CharField(help_text="Stream name")
    value = serializers.CharField(help_text="Stream values at the given timestamps")
    timestamp = serializers.DateTimeField(help_text="The timestamps at which data was reported")

class ErrorSourceDataValuesLatest(serializers.Serializer):
    sourceKey = serializers.CharField(help_text="The key value of the source")
    streams = ErrorStreamDataValuesLatest(many=True, help_text="The value of the mentioned streams")