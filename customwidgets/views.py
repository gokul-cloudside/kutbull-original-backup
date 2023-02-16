import logging
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework import authentication, permissions
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from .models import UserConfiguration
from .serializers import ConfigurationSerializer

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)


# Create your views here.
class WidgetsViewSet(viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication,
                              authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        configuration = UserConfiguration.objects.get(user=request.user)
        serializer = ConfigurationSerializer(configuration, many=False)
        response = Response(data=serializer.data, status=status.HTTP_200_OK)
        return response

    def partial_update(self, request, pk=None):
        if int(self.request.user.configuration.id) != int(pk):
            raise PermissionDenied
        instance = UserConfiguration.objects.get(id=pk)
        serializer = ConfigurationSerializer(instance,
                                             data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.update(serializer.instance, serializer.validated_data)
            response = Response(status=status.HTTP_200_OK)
            return response
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
