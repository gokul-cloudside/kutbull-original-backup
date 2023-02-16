from actionconfig.models import ActionConfigStatusBySource, ActionStorageByStream, Field_Action
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
        model = Field_Action
        fields = ('name',
                  'source',
                  'streamDataType',
                  'streamDataUnit',
                  'streamDateTimeFormat',
                  'streamPositionInCSV',
                  'type',)

'''
class InviteSerializer(serializers.ModelSerializer):
    #invitee = serializers.ReadOnlyField(source='user.id')
    inviteTime = serializers.ReadOnlyField()
    source = serializers.SlugRelatedField(
                                          #many=True,
                                          slug_field='sourceKey',
                                          queryset=Sensor.objects.all())
    class Meta:
        model = Invite
        fields = ('source','UID','emailid','status','inviteTime')
        '''

