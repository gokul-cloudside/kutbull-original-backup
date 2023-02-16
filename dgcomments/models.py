# Create your models here.

from django.db import models
from django_comments.models import Comment
from django.utils.translation import ugettext_lazy as _

class DgComment(Comment):
    image_base_64 = models.TextField(null=True, blank=True)

    class Meta:
         verbose_name = _('dg comment')
         verbose_name_plural = _('dg comments')

    def __unicode__(self):
        return "%s by %s" % (self.comment, self.user_email)

