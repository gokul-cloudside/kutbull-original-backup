
from django.db import models
from django.utils.crypto import get_random_string
from django.db.models import F
from datetime import datetime
# Create your models here.


class License(models.Model):
    # license key that DataGlen will generate
    license_key = models.CharField(unique=True, null=False, max_length=255,
                                   blank=False, primary_key=True)

    # allowed installations for this key
    installations_limit = models.IntegerField(null=False, blank=False, default=1)

    # customer name
    customer_name = models.CharField(null=False, max_length=255, blank=False)

    # this function will create a new license key
    @staticmethod
    def create_signature(self, no_of_installations, customer_name):
        try:
            # get the key
            lic_key = get_random_string(length=32)
            # create a new License object
            new_sig = License.objects.create(license_Key=lic_key,
                                             InstallLimit=no_of_installations,
                                             customer_name=customer_name)
            return new_sig.license_key
        except Exception as exc:
            return None

    def check_availability(self):
        existing_installations = self.installations.filter(active_installation=True).count()
        if existing_installations >= self.installations_limit:
            return False
        else:
            return True

    def add_installation(self, installation_key, customer_name, installation_name, ip_address):
        try:
            new_installation = Installation.objects.create(license=self,
                                                           installation_key=installation_key,
                                                           customer_name=customer_name,
                                                           installation_name=installation_name,
                                                           ip_address=ip_address,
                                                           active_installation=True)
            return new_installation.active_installation

        except Exception as exc:
            return False

    def delete_installation(self, installation_key):
        try:
            existing_installation = Installation.objects.get(license=self,
                                                             installation_key=installation_key,
                                                             active_installation=True)
            existing_installation.delete()
            return True
        except Exception as exc:
            return False

    def validate_installation(self, installation_key):
        try:
            existing_installation = Installation.objects.get(license=self,
                                                             installation_key=installation_key,
                                                             active_installation=True)
            existing_installation.updated_ts = datetime.now()
            existing_installation.save()
            return existing_installation.active_installation

        except Exception as exc:
            return False


    def __str__(self):
        return "_".join([str(self.customer_name), str(self.license_key)])


class Installation(models.Model):
    license = models.ForeignKey(License, related_name="installations",
                                related_query_name="installations")
    # the secret of each installation
    installation_key = models.CharField(null=False, max_length=255, blank=False, unique=True)

    # installation site name
    customer_name = models.CharField(null=False, max_length=255, blank=False)

    # plant name
    installation_name = models.CharField(null=False, max_length=255, blank=False)

    # ip address
    ip_address = models.CharField(null=True, max_length=255)

    # install date time
    install_ts = models.DateTimeField(null=False, blank=False, default=datetime.now())
    # last updated time
    updated_ts = models.DateTimeField(null=True, blank=True)

    # active installation status
    active_installation = models.BooleanField(null=False, blank=False, default=False)

    def __str__(self):
        return "_".join([str(self.license), str(self.installation_key)])

