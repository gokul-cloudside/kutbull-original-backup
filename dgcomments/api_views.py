from rest_framework.response import Response
from rest_framework import status, viewsets, authentication, permissions
from dashboards.mixins import ProfileDataInAPIs
from dgcomments.models import DgComment
from django.contrib.auth.models import ContentType
from django.utils import timezone
from django.conf import settings
from django.apps import apps
import logging
import re
logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

COMMENT_REGEX = '[^a-zA-Z0-9 \n\r\.><&]'


class V1CommentDataViewSet(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request, **kwargs):
        try:
            payload = self.request.data
            try:
                model_name = apps.get_model(app_label='%s' % payload['app_label'],
                                            model_name='%s' % payload['model_name'])
                content_object = ContentType.objects.get(app_label='%s' % payload['app_label'],
                                                         model='%s' % payload['model_name'])
                model_object_pk = model_name.objects.get(pk=payload['object_pk'])
                comment_text = payload['comment']
                image_base_64 = payload.get('image_base_64', "")
            except:
                return Response("Invalid app_label, model_name, object_pk, comment", status=status.HTTP_400_BAD_REQUEST)
            user_name = "%s %s" %(self.request.user.first_name, self.request.user.last_name)
            comment_text = re.sub(COMMENT_REGEX, '', comment_text)
            DgComment.objects.create(content_type_id=content_object.id,
                                            object_pk=model_object_pk.id,
                                            is_public=True, is_removed=False,
                                            site_id=settings.SITE_ID,
                                            submit_date=timezone.now(),
                                            user_id=self.request.user.id,
                                            user_name=user_name,
                                            user_email=self.request.user.email,
                                            comment=comment_text,
                                            image_base_64=image_base_64)
            return Response("Comment created successfully", status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("%s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request, **kwargs):
        try:
            payload = dict()
            try:
                payload['app_label'] = request.query_params["app_label"]
                payload['model_name'] = request.query_params["model_name"]
                payload['object_pk'] = request.query_params["object_pk"]
                model_name = apps.get_model(app_label='%s' % payload['app_label'],
                                            model_name='%s' % payload['model_name'])
                content_object = ContentType.objects.get(app_label='%s' % payload['app_label'],
                                                         model='%s' % payload['model_name'])
                model_object_pk = model_name.objects.get(pk=payload['object_pk'])
            except:
                return Response("Invalid app_lable or model_name or object_pk",
                                status=status.HTTP_400_BAD_REQUEST)
            all_comments = DgComment.objects.filter(content_type_id=content_object.id,
                                                           object_pk=model_object_pk.id,
                                                           is_public=True,
                                                           site_id=settings.SITE_ID).\
                values('comment', 'image_base_64', 'submit_date', 'user_email', 'user_name')
            return Response(all_comments, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("%s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    #def retrieve(self, request, object_pk=None):
    #    return Response([], status=status.HTTP_200_OK)

    #def destroy(self, request, item_id=None):
    #    return Response([], status=status.HTTP_200_OK)
