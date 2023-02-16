from rest_framework import serializers
from features.models import SOLAR_USER_ROLE

class UserCreateValues(serializers.Serializer):
    first_name = serializers.CharField(help_text="First name of the user")
    last_name = serializers.CharField(help_text="Last name of the user")
    email = serializers.EmailField(help_text="Valid email id of the user")
    password = serializers.CharField(help_text="Password of the user")
    confirm_password = serializers.CharField(help_text="Re-type password")
    user_role = serializers.ChoiceField(choices=SOLAR_USER_ROLE, help_text="Role of the user")

class IndividualUserViewValues(serializers.Serializer):
    user_id = serializers.CharField(help_text="User id of user")
    user_name = serializers.CharField(help_text="User name of user")
    email = serializers.EmailField(help_text="Valid email id of the user")
    first_name = serializers.CharField(help_text="First name of the user")
    last_name = serializers.CharField(help_text="Last name of the user")
    role = serializers.CharField(help_text="Role of the user")

class UserViewValues(serializers.Serializer):
    users = IndividualUserViewValues(required=False, many=True)

class OrganizationUserCreateValues(serializers.Serializer):
    email = serializers.EmailField(help_text="email address of the user")
    plant_slug = serializers.CharField(help_text="plant slug")