from dataglen.models import Sensor, Field
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist


class SensorSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.id')
    sourceKey = serializers.ReadOnlyField()


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
        fields = ('user',
                  'name',
                  'UID',
                  'sourceKey',
                  'dataFormat',
                  'dataReportingInterval',
                  'textMessageWithHTTP200',
                  'textMessageWithError',
                  'isActive',
                  'isMonitored',
                  'csvDataKeyName',
                  'timeoutInterval',
                  'dataTimezone')


class FieldSerializer(serializers.ModelSerializer):
    sensor = serializers.ReadOnlyField(source='sensor.sourceKey')
    streamPositionInCSV = serializers.IntegerField(allow_null=True)

    class Meta:
        model = Field
        fields = ('name',
                  'source',
                  'streamDataType',
                  'streamDataUnit',
                  'streamPositionInCSV')


class DataSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()

