from django.db import models
from random import randint
from kutbill.settings import SMS_KEY, SMS_SENDER, SMS_URL
import requests, json, logging
logger = logging.getLogger('helpdesk.models')
logger.setLevel(logging.DEBUG)
from django.utils import timezone
from datetime import timedelta

OTP_VALIDATION = 15


# Create your models here.
class OTP(models.Model):
    otp = models.IntegerField(null=False, blank=False)
    generated_at = models.DateTimeField(null=False, blank=False)
    validated = models.BooleanField(default=False, null=False, blank=False)

    @staticmethod
    def generate_otp():
        return randint(100000, 999999)

    @staticmethod
    def send_sms(sms_body, to_number):
        try:
            params = {}
            params['method'] = 'sms'
            params['api_key'] = SMS_KEY
            params['to'] = to_number
            params['sender'] = SMS_SENDER
            params['message'] = sms_body
            params['format'] = 'json'
            params['custom'] = 1.2
            params['flash'] = 0
            url = SMS_URL
            response = requests.post(url, data=params, verify=False)
            resp_dict = json.loads(response.content)
            # print str(resp_dict["status"])
            if str(resp_dict["status"]) == 'OK':
                return True
        except Exception as exception:
            logger.debug("error sending an OTP: " + str(exception))
            return False

    @staticmethod
    def send_otp(to_number):
        otp = OTP.generate_otp()
        sms_body = "Your One Time Password (OTP) for registering your number on DataGlen's portal is : " + str(otp) + ". This OTP is valid for 15 minutes."
        if OTP.send_sms(sms_body, to_number):
            new_otp_instance = OTP.objects.create(otp=otp, generated_at=timezone.now())
            new_otp_instance.save()
            return int(new_otp_instance.id)
        else:
            return -1

    @staticmethod
    def validate_otp(otp_id, otp_number):
        try:
            otp_instance = OTP.objects.get(id=otp_id)
            if otp_instance.otp == otp_number \
                    and timezone.now() - otp_instance.generated_at <= timedelta(minutes=OTP_VALIDATION) \
                    and otp_instance.validated is False:
                otp_instance.validated = True
                otp_instance.save()
                return 1
            else:
                return 0
        except Exception as exc:
            logger.debug("Error validating an OTP" + str(exc))
            return -1

    def __unicode__(self):
        return str(self.generated_at) + "_" + str(self.otp) + "_" + str(self.validated)
