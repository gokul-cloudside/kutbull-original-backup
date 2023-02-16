from action.models import ActionField
from rest_framework import serializers
from dataglen.models import Sensor

'''
class ActionConfigStatusBySourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValidUID
        fields = ('UID')
'''

class ActionFieldSerializer(serializers.ModelSerializer):
    source = serializers.ReadOnlyField(source='source.sourceKey', help_text="Key of the source this ActionField belongs to")
    streamPositionInCSV = serializers.IntegerField(required=False,
                                                   help_text="Applicable only if source dataFormat is CSV, should be unique")

    class Meta:
        model = ActionField
        fields = ('name',
                  'source',
                  'streamDataType',
                  'streamDataUnit',
                  'streamDateTimeFormat',
                  'streamPositionInCSV',
                  'type',)

class StreamActionValues(serializers.Serializer):
    name = serializers.CharField(help_text="Stream name")
    value = serializers.CharField(help_text="Stream values at the given timestamps")


class SourceActionValues(serializers.Serializer):
    sourceKey = serializers.CharField(help_text="The key value of the source")
    #insertionTime = serializers.ListField(child=serializers.DateTimeField(),
    #                               help_text="The timestamps at which action was reported")

    insertionTime = serializers.DateTimeField(
                                   help_text="The timestamps at which action was reported")
    streams = StreamActionValues(many=True)


class AcknowledgmentActionValues(serializers.Serializer):
    acknowledgement = serializers.IntegerField(required=True, help_text="Acknowledgement status: 1-Success, 2-Error executing action on individual field, 3-Error parsing the JSON input received.")
    insertionTime = serializers.CharField(help_text="The insertionTime string received on the GET call.", required = True)
    comments = serializers.CharField(help_text="If the status=2, comments include comma separated list of erroneous fields and if status=3, comments include error code returned by the source.", required = False,  allow_blank=True, allow_null= True)

