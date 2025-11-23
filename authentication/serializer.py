from rest_framework import serializers
from .models import User
from django.contrib.auth import authenticate


class UserRegistrationSerializer(serializers.ModelSerializer):
    confirm_password=serializers.CharField(write_only=True)
    class Meta:
        model=User
        fields=['username', 'first_name', 'last_name', 'email', 'password', 'confirm_password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate_username(self,value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("User with this mobile Number is already Registered")
        return value
    def validate_email(self,value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this Email is already Registered")
        return value
    def validate(self,attrs):
        if attrs.get('password')!=attrs.get('confirm_password'):
            raise serializers.ValidationError("Password do not match")
        return attrs


class UserLoginSerializer(serializers.Serializer):
    username=serializers.CharField(max_length=12)
    password=serializers.CharField(write_only=True)

    def validate(self,data):
        username=data.get('username')
        password=data.get('password')

        user=authenticate(username=username,password=password)
        if not user:
            raise serializers.ValidationError("Invalid username or Password")
        if not user.is_active:
            raise serializers.ValidationError("user account is disabled")
        if user.is_staff or user.is_superuser:
            raise serializers.ValidationError("Admin users are not allowed to login here.")

        data['user']=user
        return data

class ChangePasswordSerializer(serializers.Serializer):
    old_password=serializers.CharField(write_only=True)
    new_password=serializers.CharField(write_only=True)
    confirm_new_password=serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError({"confirm_new_password": "Passwords do not match."})
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile update"""
    profile_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'profile_image', 'profile_image_url', 'date_of_birth', 'initiation_date']
        extra_kwargs = {
            'email': {'required': False},
            'profile_image': {'required': False, 'write_only': True},
            'date_of_birth': {'required': False},
            'initiation_date': {'required': False},
        }
    
    def get_profile_image_url(self, obj):
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None
    
    def validate_email(self, value):
        user = self.context['request'].user
        if value and User.objects.filter(email=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("User with this Email is already Registered")
        return value









