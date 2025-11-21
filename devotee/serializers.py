from rest_framework import serializers
from .models import DailyActivity,Week,MonthlyActivity
from datetime import datetime

class WeekSerializer(serializers.ModelSerializer):
    class Meta:
        model = Week
        fields = ['id', 'name', 'start_date', 'end_date', 'month', 'year']


class DailyActivitySerializer(serializers.ModelSerializer):
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
    
    def to_representation(self, instance):
        """Filter out day-specific fields that aren't relevant for this day"""
        data = super().to_representation(instance)
        day_name = instance.date.strftime("%A")
        
        # Define which fields are relevant for each day
        day_specific_fields = {
            "Monday": [],
            "Tuesday": [],
            "Wednesday": [],
            "Thursday": ["thursday_morning_chanting_session_attendance"],
            "Friday": ["friday_morning_chanting_session_attendance"],
            "Saturday": [],
            "Sunday": [
                "sunday_offline_program_attendance",
                "sunday_temple_chanting_session_attendance",
                "weekly_discussion_session",
                "weekly_sloka_audio_posted",
                "weekly_seva"
            ]
        }
        
        # Get fields that should be shown for this day
        allowed_day_fields = day_specific_fields.get(day_name, [])
        
        # Collect all day-specific fields from all days
        all_day_specific_fields = []
        for fields_list in day_specific_fields.values():
            all_day_specific_fields.extend(fields_list)
        
        # Remove fields that aren't relevant for this day
        # Always remove irrelevant day-specific fields to avoid showing them in filtered views
        for field in all_day_specific_fields:
            if field not in allowed_day_fields and field in data:
                del data[field]
        
        return data



class MonthlyActivitySerializer(serializers.ModelSerializer):
    weeks = WeekSerializer(many=True, read_only=True)
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = MonthlyActivity
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'user']