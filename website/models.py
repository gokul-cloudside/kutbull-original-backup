from django.db import models

class BetaRequest(models.Model):
    name = models.CharField(max_length=100, blank=False)
    email = models.EmailField(blank=False)
    phone = models.CharField(max_length=20, blank=False)
    requirements = models.TextField(max_length=100, blank=False, default=None)
    processed = models.BooleanField(default=False, blank=True)
    comments = models.TextField(default=None, blank=True, null=True)