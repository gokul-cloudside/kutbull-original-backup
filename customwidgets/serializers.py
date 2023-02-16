from .models import WidgetInstance, UserConfiguration, FilePath
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.fields import CurrentUserDefault
import logging

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)


class WidgetInstanceSerializer(serializers.ModelSerializer):
    filepath = serializers.SerializerMethodField('get_filename', read_only=True)
    id = serializers.IntegerField(read_only=False)
    # filepath = serializers.CharField(allow_blank=False,
    #                                  read_only=True,
    #                                  max_length=500)
    class Meta:
        model = WidgetInstance
        fields = ('id', 'x', 'y', 'name', 'width', 'height', 'filepath')
        
    def get_filename(self, wi):
        return FilePath.objects.get(name=wi.name).filepath

class ConfigurationSerializer(serializers.ModelSerializer):
    widgets = WidgetInstanceSerializer(many=True)

    class Meta:
        model = UserConfiguration
        fields = ('id', 'configure', 'widgets',)
        read_only_fields = ('configure', 'id')

    def update(self, instance, validated_data):
        widgets_data = validated_data['widgets']
        for widget in widgets_data:
            try:
                old_widget = instance.widgets.all().get(id=widget["id"])
                old_widget.x = widget.get('x', old_widget.x)
                old_widget.y = widget.get('y', old_widget.y)
                old_widget.width = widget.get('width', old_widget.width)
                old_widget.height = widget.get('height', old_widget.height)
                old_widget.save()
            except WidgetInstance.DoesNotExist:
                continue
        return instance
