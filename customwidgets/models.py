from django.db import models
from django.contrib.auth.models import User

class FilePath(models.Model):
    name = models.CharField(max_length=1000, blank=False)
    filepath = models.CharField(max_length=1000, blank=False)
    default_x = models.IntegerField(default=0, blank=False)
    default_y = models.IntegerField(default=0, blank=False)
    def __unicode__(self):
        return self.name

class UserConfiguration(models.Model):
    user = models.OneToOneField(User, related_query_name="configuration",
                                related_name="configuration")
    configure = models.BooleanField(default=False, blank=False)

    def __unicode__(self):
        return self.user.__unicode__()

class WidgetInstance(models.Model):
    configuration = models.ForeignKey(UserConfiguration,
                                      related_name="widgets",
                                      related_query_name="widgets")
    x = models.IntegerField(blank=False, default=0)
    y = models.IntegerField(blank=False, default=0)
    width = models.IntegerField(blank=False, default=0)
    height = models.IntegerField(blank=False, default=0)
    name = models.CharField(max_length=1000, blank=False)

    def __unicode__(self):
        return self.configuration.user.__unicode__()
