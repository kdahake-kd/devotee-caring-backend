from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Sum
from .models import DailyActivity, Week, MonthlyActivity
from .serializers import DailyActivitySerializer, WeekSerializer, MonthlyActivitySerializer
from authentication.models import User





DAY_SPECIFIC_FIELDS = {
    "Monday": [],
    "Tuesday": [],
    "Wednesday": [],
    "Thursday": ["thursday_morning_chanting_session_attendance"],
    "Friday": ["friday_morning_chanting_session_attendance"],
    "Saturday": [],
    "Sunday": ["sunday_offline_program_attendance", "sunday_temple_chanting_session_attendance"]
}

# ✅ Always editable fields (everyday)
BASE_FIELDS = ["daily_hearing", "daily_reading", "daily_chanting", "sport_session_attendance"]

class DailyActivityViewSet(viewsets.ModelViewSet):
    queryset = DailyActivity.objects.all()
    serializer_class = DailyActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DailyActivity.objects.filter(user=self.request.user).order_by('date')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # 🟢 API 1 — Fetch all week data (Mon–Sun)
    #
    @action(detail=False, methods=['GET'], url_path='week-data')
    def get_week_data(self, request):
        """
        Return all days of current week with editable fields for each day.
        """
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())  # Monday
        end_of_week = start_of_week + timedelta(days=6)

        week_obj, _ = Week.objects.get_or_create(
            start_date=start_of_week,
            end_date=end_of_week,
            month=start_of_week.month,
            year=start_of_week.year,
            created_by=request.user,
            defaults={"name": f"Week of {start_of_week}"}
        )

        # Fetch user’s existing daily activities
        activities = DailyActivity.objects.filter(
            user=request.user,
            date__range=[start_of_week, end_of_week]
        )

        week_data = []
        for i in range(7):
            current_date = start_of_week + timedelta(days=i)
            activity = next((a for a in activities if a.date == current_date), None)
            day_name = current_date.strftime("%A")

            # Define editable fields dynamically based on weekday
            editable_fields = ["daily_hearing", "daily_reading", "daily_chanting","sport_session_attendance"]

            if day_name == "Thursday":
                editable_fields.append("thursday_morning_chanting_session_attendance")
            elif day_name == "Sunday":
                editable_fields.extend([
                    "sunday_offline_program_attendance",
                    "sunday_temple_chanting_session_attendance",
                    "weekly_discussion_session",
                    "weekly_sloka_audio_posted",
                    "weekly_seva"
                ])

            # Only make editable if date <= today
            is_editable = current_date <= today

            week_data.append({
                "date": str(current_date),
                "day": day_name,
                "is_editable": is_editable,
                "editable_fields": editable_fields if is_editable else [],
                "activity": DailyActivitySerializer(activity).data if activity else None
            })

        return Response({
            "week_name": week_obj.name,
            "start_date": str(start_of_week),
            "end_date": str(end_of_week),
            "days": week_data
        }, status=status.HTTP_200_OK)

    # 🟡 API 2 — Add or Edit a specific day
    @action(detail=False, methods=['POST'], url_path='add-or-edit-day')
    def add_or_edit_day(self, request):
        """
        Add or edit activity for a specific date (only if <= today and >= week_start).
        """
        user = request.user
        date_str = request.data.get("date")

        if not date_str:
            return Response({"error": "Date is required."}, status=400)

        try:
            activity_date = date.fromisoformat(date_str)
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        today = date.today()
        if activity_date > today:
            return Response({"error": "Cannot add future data."}, status=400)

        # Compute week start/end
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        if activity_date < start_of_week:
            return Response({"error": "Cannot edit previous week’s data."}, status=400)

        # Get week object
        week_obj, _ = Week.objects.get_or_create(
            start_date=start_of_week,
            end_date=end_of_week,
            month=start_of_week.month,
            year=start_of_week.year,
            created_by=user,
            defaults={"name": f"Week of {start_of_week}"}
        )
        # ✅ Determine which fields are editable for this date
        weekday_name = activity_date.strftime("%A")
        allowed_fields = BASE_FIELDS + DAY_SPECIFIC_FIELDS.get(weekday_name, [])
        
        # Add Sunday weekly fields if it's Sunday
        if weekday_name == "Sunday":
            allowed_fields.extend(["weekly_discussion_session", "weekly_sloka_audio_posted", "weekly_seva"])

        # Filter only allowed fields from request data
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

        # Update or create activity
        activity, created = DailyActivity.objects.update_or_create(
            user=user,
            date=activity_date,
            defaults={**update_data, "week": week_obj}
        )

        serializer = self.get_serializer(activity)
        return Response({
            "message": f"{weekday_name} data {'created' if created else 'updated'} successfully.",
            "editable_fields": allowed_fields,
            "data": serializer.data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    # 🔴 API 3 — Delete specific day data
    @action(detail=True, methods=['DELETE'], url_path='delete-day')
    def delete_day(self, request, pk=None):
        try:
            activity = self.get_queryset().get(pk=pk)
            today = date.today()

            # Only delete if this day <= today and >= week start
            week_start = today - timedelta(days=today.weekday())
            if not (week_start <= activity.date <= today):
                return Response({"error": "Cannot delete this date’s data."}, status=400)

            activity.delete()
            return Response({"message": "Deleted successfully."}, status=204)
        except DailyActivity.DoesNotExist:
            return Response({"error": "Not found."}, status=404)

    # 🔵 API 4 — Filter data by week, month, or year
    @action(detail=False, methods=['GET'], url_path='filter')
    def filter_activities(self, request):
        """
        Filter activities by week, month, or year.
        Query params: week_id, month, year
        """
        user = request.user
        week_id = request.query_params.get('week_id')
        month = request.query_params.get('month')
        year = request.query_params.get('year')

        # Start with user's activities
        queryset = DailyActivity.objects.filter(user=user).order_by('-date')

        # Filter by week_id if provided
        if week_id:
            try:
                week_obj = Week.objects.get(id=week_id, created_by=user)
                queryset = queryset.filter(week=week_obj)
            except Week.DoesNotExist:
                return Response({"error": "Week not found."}, status=404)

        # Filter by month if provided
        if month:
            try:
                month = int(month)
                if month < 1 or month > 12:
                    return Response({"error": "Invalid month. Must be 1-12."}, status=400)
                queryset = queryset.filter(date__month=month)
            except ValueError:
                return Response({"error": "Invalid month format."}, status=400)

        # Filter by year if provided
        if year:
            try:
                year = int(year)
                queryset = queryset.filter(date__year=year)
            except ValueError:
                return Response({"error": "Invalid year format."}, status=400)

        # Get current week for editable check
        today = date.today()
        current_week_start = today - timedelta(days=today.weekday())
        current_week_end = current_week_start + timedelta(days=6)

        # Group by week for better organization
        weeks_data = {}
        for activity in queryset:
            week_id = activity.week.id
            if week_id not in weeks_data:
                is_current_week = current_week_start <= activity.week.start_date <= current_week_end
                weeks_data[week_id] = {
                    "week_id": week_id,
                    "week_name": activity.week.name,
                    "start_date": str(activity.week.start_date),
                    "end_date": str(activity.week.end_date),
                    "month": activity.week.month,
                    "year": activity.week.year,
                    "is_current_week": is_current_week,
                    "activities": []
                }
            # Serialize each activity individually
            activity_serializer = DailyActivitySerializer(activity)
            weeks_data[week_id]["activities"].append(activity_serializer.data)

        return Response({
            "total_count": queryset.count(),
            "weeks": list(weeks_data.values())
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['GET'], url_path='chanting-round-count')
    def get_chanting_round_count(self, request):
        """
        Get the total number of chanting rounds 
        """
        user = request.user
        queryset = DailyActivity.objects.filter(user=user)
        total_chanting_rounds = queryset.aggregate(total=Sum('daily_chanting'))['total'] or 0
        return Response({
            "total_chanting_rounds": total_chanting_rounds
        }, status=status.HTTP_200_OK)
    
class MonthlyActivityViewSet(viewsets.ModelViewSet):
    queryset = MonthlyActivity.objects.all()
    serializer_class = MonthlyActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MonthlyActivity.objects.filter(user=self.request.user).order_by('-year', '-month')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # 🟢 API 1 — Get current month's activity
    @action(detail=False, methods=['GET'], url_path='current-month')
    def get_current_month(self, request):
        """
        Get or create monthly activity for current month.
        """
        today = date.today()
        current_month = today.month
        current_year = today.year

        monthly_activity, created = MonthlyActivity.objects.get_or_create(
            user=request.user,
            month=current_month,
            year=current_year,
            defaults={}
        )

        # Get all weeks for this month
        weeks = Week.objects.filter(
            created_by=request.user,
            month=current_month,
            year=current_year
        )
        monthly_activity.weeks.set(weeks)

        serializer = self.get_serializer(monthly_activity)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 🟡 API 2 — Get monthly activity by month and year
    @action(detail=False, methods=['GET'], url_path='get-month')
    def get_month_activity(self, request):
        """
        Get monthly activity for specific month and year.
        Query params: month (1-12), year
        """
        month = request.query_params.get('month')
        year = request.query_params.get('year')

        if not month or not year:
            return Response({"error": "Month and year are required."}, status=400)

        try:
            month = int(month)
            year = int(year)
            if month < 1 or month > 12:
                return Response({"error": "Invalid month. Must be 1-12."}, status=400)
        except ValueError:
            return Response({"error": "Invalid month or year format."}, status=400)

        try:
            monthly_activity = MonthlyActivity.objects.get(
                user=request.user,
                month=month,
                year=year
            )
            serializer = self.get_serializer(monthly_activity)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except MonthlyActivity.DoesNotExist:
            return Response({"error": "Monthly activity not found for this month/year."}, status=404)

    # 🟢 API 3 — Add or update monthly activity
    @action(detail=False, methods=['POST'], url_path='add-or-edit')
    def add_or_edit_monthly(self, request):
        """
        Add or update monthly activity.
        Required: month, year
        Optional: one_to_one_meeting_conducted_with_counselor, monthly_morning_program,
                  monthly_book_completed, book_name, book_discussion_attended, week_ids (list)
        """
        month = request.data.get('month')
        year = request.data.get('year')

        if not month or not year:
            return Response({"error": "Month and year are required."}, status=400)

        try:
            month = int(month)
            year = int(year)
            if month < 1 or month > 12:
                return Response({"error": "Invalid month. Must be 1-12."}, status=400)
        except ValueError:
            return Response({"error": "Invalid month or year format."}, status=400)

        # Get or create monthly activity
        monthly_activity, created = MonthlyActivity.objects.get_or_create(
            user=request.user,
            month=month,
            year=year,
            defaults={}
        )

        # Update fields
        update_fields = [
            'one_to_one_meeting_conducted_with_counselor',
            'monthly_morning_program',
            'monthly_book_completed',
            'book_name',
            'book_discussion_attended'
        ]

        for field in update_fields:
            if field in request.data:
                setattr(monthly_activity, field, request.data[field])

        monthly_activity.save()

        # Update weeks - use provided week_ids or auto-assign weeks for this month
        if 'week_ids' in request.data and request.data['week_ids']:
            week_ids = request.data['week_ids']
            if isinstance(week_ids, list) and len(week_ids) > 0:
                weeks = Week.objects.filter(
                    id__in=week_ids,
                    created_by=request.user
                )
                monthly_activity.weeks.set(weeks)
            else:
                # Auto-assign weeks for this month if week_ids is empty or invalid
                weeks = Week.objects.filter(
                    created_by=request.user,
                    month=month,
                    year=year
                )
                monthly_activity.weeks.set(weeks)
        else:
            # Auto-assign weeks for this month if not provided
            weeks = Week.objects.filter(
                created_by=request.user,
                month=month,
                year=year
            )
            monthly_activity.weeks.set(weeks)

        # Serialize and return response
        serializer = self.get_serializer(monthly_activity)
        return Response({
            "message": f"Monthly activity {'created' if created else 'updated'} successfully.",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    # 🔵 API 4 — Filter monthly activities
    @action(detail=False, methods=['GET'], url_path='filter')
    def filter_monthly_activities(self, request):
        """
        Filter monthly activities by year or month.
        Query params: year, month (optional)
        """
        user = request.user
        queryset = MonthlyActivity.objects.filter(user=user).order_by('-year', '-month')

        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if year:
            try:
                year = int(year)
                queryset = queryset.filter(year=year)
            except ValueError:
                return Response({"error": "Invalid year format."}, status=400)

        if month:
            try:
                month = int(month)
                if month < 1 or month > 12:
                    return Response({"error": "Invalid month. Must be 1-12."}, status=400)
                queryset = queryset.filter(month=month)
            except ValueError:
                return Response({"error": "Invalid month format."}, status=400)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "total_count": queryset.count(),
            "activities": serializer.data
        }, status=status.HTTP_200_OK)


# QR Code Quick Entry Views (Public - No Authentication Required)

@api_view(['GET'])
@permission_classes([AllowAny])
def validate_qr_token(request, token):
    """
    Validate QR token and return today's editable fields and existing data
    No authentication required - uses token instead
    """
    if not token:
        return Response({"error": "Token is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(qr_token=token, is_active=True)
    except User.DoesNotExist:
        return Response({
            "error": "Invalid or expired QR token. Please generate a new QR code from your profile."
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check if token is too old (optional - 1 year expiration)
    if user.qr_token_created_at:
        days_old = (timezone.now() - user.qr_token_created_at).days
        if days_old > 365:
            return Response({
                "error": "QR token has expired. Please generate a new QR code from your profile."
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get today's date
    today = date.today()
    weekday_name = today.strftime("%A")
    
    # Determine editable fields for today
    allowed_fields = BASE_FIELDS + DAY_SPECIFIC_FIELDS.get(weekday_name, [])
    
    # Add Sunday weekly fields if it's Sunday
    if weekday_name == "Sunday":
        allowed_fields.extend(["weekly_discussion_session", "weekly_sloka_audio_posted", "weekly_seva"])
    
    # Get existing activity for today if any
    existing_activity = None
    try:
        activity = DailyActivity.objects.get(user=user, date=today)
        serializer = DailyActivitySerializer(activity)
        existing_activity = serializer.data
    except DailyActivity.DoesNotExist:
        pass
    
    # Build field definitions for frontend
    field_definitions = {}
    
    # Base fields
    if "daily_hearing" in allowed_fields:
        field_definitions["daily_hearing"] = {
            "label": "Daily Hearing",
            "type": "select",
            "options": [
                {"value": "Completed", "label": "Completed"},
                {"value": "Not Completed", "label": "Not Completed"}
            ],
            "value": existing_activity.get("daily_hearing", "Not Completed") if existing_activity else "Not Completed"
        }
    
    if "daily_reading" in allowed_fields:
        field_definitions["daily_reading"] = {
            "label": "Daily Reading",
            "type": "select",
            "options": [
                {"value": "Completed", "label": "Completed"},
                {"value": "Not Completed", "label": "Not Completed"}
            ],
            "value": existing_activity.get("daily_reading", "Not Completed") if existing_activity else "Not Completed"
        }
    
    if "daily_chanting" in allowed_fields:
        field_definitions["daily_chanting"] = {
            "label": "Daily Chanting (Rounds)",
            "type": "number",
            "min": 0,
            "value": existing_activity.get("daily_chanting", 0) if existing_activity else 0
        }
    
    if "sport_session_attendance" in allowed_fields:
        field_definitions["sport_session_attendance"] = {
            "label": "Sport Session Attendance",
            "type": "select",
            "options": [
                {"value": "Attended", "label": "Attended"},
                {"value": "Not Attended", "label": "Not Attended"},
                {"value": "No Session Today", "label": "No Session Today"}
            ],
            "value": existing_activity.get("sport_session_attendance", "Not Attended") if existing_activity else "Not Attended"
        }
    
    # Thursday specific
    if "thursday_morning_chanting_session_attendance" in allowed_fields:
        field_definitions["thursday_morning_chanting_session_attendance"] = {
            "label": "Thursday Morning Chanting Session",
            "type": "select",
            "options": [
                {"value": "Attended", "label": "Attended"},
                {"value": "Not Attended", "label": "Not Attended"}
            ],
            "value": existing_activity.get("thursday_morning_chanting_session_attendance", "Not Attended") if existing_activity else "Not Attended"
        }
    
    # Friday specific
    if "friday_morning_chanting_session_attendance" in allowed_fields:
        field_definitions["friday_morning_chanting_session_attendance"] = {
            "label": "Friday Morning Chanting Session",
            "type": "select",
            "options": [
                {"value": "Attended", "label": "Attended"},
                {"value": "Not Attended", "label": "Not Attended"}
            ],
            "value": existing_activity.get("friday_morning_chanting_session_attendance", "Not Attended") if existing_activity else "Not Attended"
        }
    
    # Sunday specific
    if "sunday_offline_program_attendance" in allowed_fields:
        field_definitions["sunday_offline_program_attendance"] = {
            "label": "Sunday Offline Program Attendance",
            "type": "select",
            "options": [
                {"value": "Attended", "label": "Attended"},
                {"value": "Not Attended", "label": "Not Attended"}
            ],
            "value": existing_activity.get("sunday_offline_program_attendance", "Not Attended") if existing_activity else "Not Attended"
        }
    
    if "sunday_temple_chanting_session_attendance" in allowed_fields:
        field_definitions["sunday_temple_chanting_session_attendance"] = {
            "label": "Sunday Temple Chanting Session",
            "type": "select",
            "options": [
                {"value": "Attended", "label": "Attended"},
                {"value": "Not Attended", "label": "Not Attended"}
            ],
            "value": existing_activity.get("sunday_temple_chanting_session_attendance", "Not Attended") if existing_activity else "Not Attended"
        }
    
    if "weekly_discussion_session" in allowed_fields:
        field_definitions["weekly_discussion_session"] = {
            "label": "Weekly Discussion Session",
            "type": "select",
            "options": [
                {"value": "Online", "label": "Online"},
                {"value": "Offline", "label": "Offline"},
                {"value": "Not Attended", "label": "Not Attended"}
            ],
            "value": existing_activity.get("weekly_discussion_session", "Not Attended") if existing_activity else "Not Attended"
        }
    
    if "weekly_sloka_audio_posted" in allowed_fields:
        field_definitions["weekly_sloka_audio_posted"] = {
            "label": "Weekly Sloka Audio Posted",
            "type": "select",
            "options": [
                {"value": "Yes", "label": "Yes"},
                {"value": "No", "label": "No"}
            ],
            "value": existing_activity.get("weekly_sloka_audio_posted", "No") if existing_activity else "No"
        }
    
    if "weekly_seva" in allowed_fields:
        field_definitions["weekly_seva"] = {
            "label": "Weekly Seva",
            "type": "select",
            "options": [
                {"value": "Yes", "label": "Yes"},
                {"value": "No", "label": "No"}
            ],
            "value": existing_activity.get("weekly_seva", "No") if existing_activity else "No"
        }
    
    return Response({
        "valid": True,
        "user_name": f"{user.first_name} {user.last_name}",
        "today": today.isoformat(),
        "day_name": weekday_name,
        "editable_fields": allowed_fields,
        "field_definitions": field_definitions,
        "has_existing_data": existing_activity is not None
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def submit_quick_entry(request, token):
    """
    Submit today's activities via QR token (no authentication required)
    
    """
    if not token:
        return Response({"error": "Token is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(qr_token=token, is_active=True)
    except User.DoesNotExist:
        return Response({
            "error": "Invalid or expired QR token. Please generate a new QR code from your profile."
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check token expiration
    if user.qr_token_created_at:
        days_old = (timezone.now() - user.qr_token_created_at).days
        if days_old > 365:
            return Response({
                "error": "QR token has expired. Please generate a new QR code from your profile."
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get today's date
    today = date.today()
    weekday_name = today.strftime("%A")
    
    # Determine editable fields for today
    allowed_fields = BASE_FIELDS + DAY_SPECIFIC_FIELDS.get(weekday_name, [])
    
    # Add Sunday weekly fields if it's Sunday
    if weekday_name == "Sunday":
        allowed_fields.extend(["weekly_discussion_session", "weekly_sloka_audio_posted", "weekly_seva"])
    
    # Validate that only allowed fields are being submitted
    submitted_fields = set(request.data.keys())
    invalid_fields = submitted_fields - set(allowed_fields + ['date'])  # date is allowed for validation
    
    if invalid_fields:
        return Response({
            "error": f"Invalid fields submitted: {', '.join(invalid_fields)}. Only today's fields are allowed."
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Compute week start/end
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Get or create week object
    week_obj, _ = Week.objects.get_or_create(
        start_date=start_of_week,
        end_date=end_of_week,
        month=start_of_week.month,
        year=start_of_week.year,
        created_by=user,
        defaults={"name": f"Week of {start_of_week}"}
    )
    
    # Filter only allowed fields from request data
    update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
    
    # Validate data types
    if 'daily_chanting' in update_data:
        try:
            update_data['daily_chanting'] = int(update_data['daily_chanting'])
            if update_data['daily_chanting'] < 0:
                return Response({"error": "Daily chanting rounds cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({"error": "Daily chanting must be a valid number."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Update or create activity
    activity, created = DailyActivity.objects.update_or_create(
        user=user,
        date=today,
        defaults={**update_data, "week": week_obj}
    )
    
    serializer = DailyActivitySerializer(activity)
    return Response({
        "message": f"Today's ({weekday_name}) activities {'saved' if created else 'updated'} successfully!",
        "data": serializer.data,
        "day_name": weekday_name
    }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)




