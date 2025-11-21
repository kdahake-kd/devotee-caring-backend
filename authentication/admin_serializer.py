from rest_framework import serializers
from .models import User
from devotee.models import DailyActivity, MonthlyActivity
from devotee.serializers import DailyActivitySerializer, MonthlyActivitySerializer

class AdminDailyActivitySerializer(serializers.ModelSerializer):
    """Admin serializer for daily activities - shows all fields"""
    user = serializers.ReadOnlyField(source='user.username')
    week_name = serializers.ReadOnlyField(source='week.name')
    day_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DailyActivity
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'user', 'week']
    
    def get_day_name(self, obj):
        """Get the day name from the date"""
        return obj.date.strftime("%A")

class DevoteeListSerializer(serializers.ModelSerializer):
    """Serializer for listing devotees with basic info"""
    full_name = serializers.SerializerMethodField()
    total_daily_activities = serializers.SerializerMethodField()
    total_monthly_activities = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'full_name',
            'email', 'is_active', 'is_user_verified', 'created_at',
            'total_daily_activities', 'total_monthly_activities'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    
    def get_total_daily_activities(self, obj):
        return DailyActivity.objects.filter(user=obj).count()
    
    def get_total_monthly_activities(self, obj):
        return MonthlyActivity.objects.filter(user=obj).count()

class DevoteeDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed devotee information"""
    full_name = serializers.SerializerMethodField()
    daily_activities = serializers.SerializerMethodField()
    monthly_activities = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'full_name',
            'email', 'is_active', 'is_user_verified', 'created_at', 'updated_at',
            'daily_activities', 'monthly_activities'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    
    def get_daily_activities(self, obj):
        try:
            activities = DailyActivity.objects.filter(user=obj).order_by('-date')[:50]
            if activities.exists():
                return AdminDailyActivitySerializer(activities, many=True).data
            return []
        except Exception as e:
            # Return empty list if there's any error
            return []
    
    def get_monthly_activities(self, obj):
        try:
            activities = MonthlyActivity.objects.filter(user=obj).order_by('-year', '-month')
            if activities.exists():
                return MonthlyActivitySerializer(activities, many=True).data
            return []
        except Exception as e:
            # Return empty list if there's any error
            return []

