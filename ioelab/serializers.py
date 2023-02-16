from ioelab.models import ValidUID, Invite
from rest_framework import serializers
from dataglen.models import Sensor

class ValidUIDSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValidUID
        fields = ('UID')

class InviteSerializer(serializers.ModelSerializer):
    #invitee = serializers.ReadOnlyField(source='user.id')
    inviteTime = serializers.ReadOnlyField()
    source = serializers.SlugRelatedField(
                                          #many=True,
                                          slug_field='sourceKey',
                                          queryset=Sensor.objects.all())
    class Meta:
        model = Invite
        fields = ('source','UID','emailid','status','inviteTime','default_load')

