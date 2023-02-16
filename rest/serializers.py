from dataglen.models import Sensor, Field
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist


class SourceSerializer(serializers.ModelSerializer):
    sourceKey = serializers.ReadOnlyField(help_text="Unique sensor key, a read only field")


    def validate_UID(self, UID):
        #raise serializers.ValidationError('inside validate_UID')
        if UID and UID != '':
            try:
                Sensor.objects.get(UID=UID)
            except ObjectDoesNotExist:
                return UID
            raise serializers.ValidationError('UID already exists')
        else:
            return UID


    class Meta:
        model = Sensor
        fields = ('name',
                  'sourceKey',
                  'UID',
                  'dataFormat',
                  'dataReportingInterval',
                  'sourceMacAddress',
                  'textMessageWithHTTP200',
                  'textMessageWithError',
                  'isActive',
                  'isMonitored',
                  'actuationEnabled',
                  'csvDataKeyName',
                  'timeoutInterval',
                  'dataTimezone',
                  'manager_email',
                  'manager_name',
                  'manager_phone')



class StreamSerializer(serializers.ModelSerializer):
    source = serializers.ReadOnlyField(source='source.sourceKey', help_text="Key of the source this stream belongs to")
    streamPositionInCSV = serializers.IntegerField(required=False,
                                                   help_text="Applicable only if source dataFormat is CSV, should be unique")

    class Meta:
        model = Field
        fields = ('name',
                  'source',
                  'streamDataType',
                  'streamDataUnit',
                  'streamDateTimeFormat',
                  'streamPositionInCSV',
                  'multiplicationFactor')


class StreamDataValues(serializers.Serializer):
    name = serializers.CharField(help_text="Stream name")
    count = serializers.IntegerField(help_text="Data Count")
    startTime = serializers.DateTimeField(help_text="The first timestamp of the returned data", required=False)
    endTime = serializers.DateTimeField(help_text="The last timestamp of the returned data", required=False)
    values = serializers.ListField(child=serializers.CharField(),
                                   help_text="Stream values at the given timestamps")
    timestamps = serializers.ListField(child=serializers.DateTimeField(),
                                       help_text="The timestamps at which data was reported")


class StreamDataValuesLatest(serializers.Serializer):
    name = serializers.CharField(help_text="Stream name")
    #count = serializers.IntegerField(help_text="Data Count")
    #startTime = serializers.DateTimeField(help_text="The first timestamp of the returned data", required=False)
    #endTime = serializers.DateTimeField(help_text="The last timestamp of the returned data", required=False)
    value = serializers.CharField(help_text="Stream values at the given timestamps")
    timestamp = serializers.DateTimeField(help_text="The timestamps at which data was reported")


class SourceDataValues(serializers.Serializer):
    sourceKey = serializers.CharField(help_text="The key value of the source")
    streams = StreamDataValues(many=True, help_text="The value of the mentioned streams")


class SourceDataValuesLatest(serializers.Serializer):
    sourceKey = serializers.CharField(help_text="The key value of the source")
    streams = StreamDataValuesLatest(many=True, help_text="The value of the mentioned streams")
