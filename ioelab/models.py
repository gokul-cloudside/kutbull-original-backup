# Create your models here.
from django.db import models
from dashboards.models import DataglenGroup
from dataglen.models import Sensor, Field
from django.contrib.auth.models import User

class ValidUID(models.Model):
    UID = models.CharField(max_length=12,blank=False,primary_key=True, help_text="Valid UID of IoELab Kits provided by vendors")
    def __unicode__(self):
        return self.UID


class Invite(models.Model):
    source = models.ForeignKey(Sensor,
                                related_name = "invite",
                                related_query_name="invite",
                                to_field='sourceKey',
                                help_text="IoELab invite for the source")
                                # commented for disabling UID validation for the time-being
    '''
    UID = models.ForeignKey(ValidUID,
                            related_name = "invite",
                            related_query_name="invite",
                            to_field='UID',
                            help_text="IoELab invite for the specific UID")
    '''
    UID = models.CharField(max_length=12,blank=False, help_text="Valid UID of IoELab Kits provided by vendors")
    invitee =  models.ForeignKey(User, related_name = "ioeinvites_sent",blank=True, related_query_name="ioeinvites_sent", help_text="invitee name")
    emailid = models.EmailField(max_length=100, blank=False, help_text="email-id for the invitation to be sent")
    status = models.PositiveSmallIntegerField(null=False,
                                 blank=False,default=0,
                                 help_text="status of the invitation: 0-Invitation sent, 1-Invitation accepted, 2-Invitation expired, 3-Device validated, ownership changed, 4-De-registration executed")
    inviteTime =models.DateTimeField(auto_now_add=True)
    default_load = models.BooleanField(default=False, blank=True)

    def __unicode__(self):
        return str(self.id)
    
    class Meta:
        unique_together = (("UID", "emailid","status"),)

#After testing put a unique condition on 'UID', 'status'



