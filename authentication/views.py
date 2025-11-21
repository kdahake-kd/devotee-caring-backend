from django.shortcuts import render
from rest_framework import status,viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny,IsAuthenticated,IsAdminUser
from rest_framework.response import Response
from .models import User
from .serializer import UserRegistrationSerializer,UserLoginSerializer,ChangePasswordSerializer
from .admin_serializer import DevoteeListSerializer, DevoteeDetailSerializer, AdminDailyActivitySerializer
from devotee.serializers import MonthlyActivitySerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import logout, authenticate
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from datetime import date, timedelta, datetime
from devotee.models import DailyActivity, MonthlyActivity, Week
from collections import defaultdict
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class UserAuthenticationViewSet(viewsets.ViewSet):
    """
        Handles:
        - POST /register-user/
        - POST /login/
        - POST /change-password/
        - POST /logout/
    """
    @action(detail=False,methods=['POST'],permission_classes=[AllowAny],url_path='register-user')
    def register_user(self,request):
        try:
            serializer=UserRegistrationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data= serializer.validated_data
            #mobile= data.get('username')

            # Check is Mobile number is verified by otp
            # if not VerifiedMobile.objects.filter(username=mobil).exists():
            #     return Response({'error':"Mobile Number is not verified "},, status=status.HTTP_400_BAD_REQUEST)

            user=User.objects.create_user(
                username=data.get('username','Guest'),
                first_name=data.get('first_name',"Guest"),
                last_name=data.get("last_name","Guest"),
                email=data.get("email","guest@gmail.com"),
                password=data.get("password","Guest@123"),
                is_active=True
            )
            # VerifiedMobile.objects.filter(mobile=mobile).delete()  delete the entry from VerifiedMobile table for the mobile number
            return Response({"message":"User Registered Successfully "},status=status.HTTP_201_CREATED)
        except Exception as e:
            print("[ERROR] Registration failed:", str(e))
            return Response({"error": "An error occurred during registration."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False,methods=["POST"],permission_classes=[AllowAny],url_path='login')
    def login(self,request):
        serializer=UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Login successfully",
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email
            }
        }, status=status.HTTP_200_OK)

    @action(detail=False,methods=['POST'],permission_classes=[IsAuthenticated],url_path='change-password')
    def change_password(self,request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)

    @action(detail=False,methods=['POST'],permission_classes=[IsAuthenticated],url_path='logout')
    def logout_user(self,request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except Exception:
                    pass  # Token might already be invalid
            logout(request)
            return Response({"message": "User logged out successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminViewSet(viewsets.ViewSet):
    """
    Admin endpoints:
    - POST /admin-login/ - Admin login
    - GET /devotees/ - List all devotees (with search)
    - GET /devotees/{id}/ - Get devotee details
    """
    
    @action(detail=False, methods=['POST'], permission_classes=[AllowAny], url_path='admin-login')
    def admin_login(self, request):
        """Admin login - only allows staff/superuser"""
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {"error": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(username=username, password=password)
        
        if not user:
            return Response(
                {"error": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not (user.is_staff or user.is_superuser):
            return Response(
                {"error": "Access denied. Admin privileges required."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not user.is_active:
            return Response(
                {"error": "Account is disabled."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Admin login successful",
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "is_superuser": user.is_superuser,
                "is_staff": user.is_staff
            }
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['GET'], permission_classes=[IsAuthenticated])
    def devotees(self, request):
        """List all devotees with optional search"""
        # Check if user is admin
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {"error": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get search query
        search = request.query_params.get('search', '').strip()
        
        # Filter out admin users, only show regular devotees
        queryset = User.objects.filter(is_staff=False, is_superuser=False)
        
        # Apply search filter
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search) |
                Q(email__icontains=search)
            )
        
        # Order by creation date (newest first)
        queryset = queryset.order_by('-created_at')
        
        serializer = DevoteeListSerializer(queryset, many=True)
        
        return Response({
            "total_count": queryset.count(),
            "devotees": serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated], url_path='devotee-detail')
    def devotee_detail(self, request, pk=None):
        """Get detailed information about a specific devotee"""
        # Check if user is admin
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {"error": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            devotee = User.objects.get(pk=pk, is_staff=False, is_superuser=False)
        except User.DoesNotExist:
            return Response(
                {"error": "Devotee not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Error retrieving devotee: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        try:
            serializer = DevoteeDetailSerializer(devotee)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Error serializing devotee data: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated], url_path='filter-activities')
    def filter_devotee_activities(self, request, pk=None):
        """
        Filter devotee activities by date range, week, month, or year.
        Query params: start_date, end_date, week_id, month, year
        """
        # Check if user is admin
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {"error": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            devotee = User.objects.get(pk=pk, is_staff=False, is_superuser=False)
        except User.DoesNotExist:
            return Response(
                {"error": "Devotee not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get filter parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        week_id = request.query_params.get('week_id')
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        
        # Start with all activities for this devotee
        daily_activities = DailyActivity.objects.filter(user=devotee)
        monthly_activities = MonthlyActivity.objects.filter(user=devotee)
        
        # Apply filters
        if start_date and end_date:
            try:
                start = date.fromisoformat(start_date)
                end = date.fromisoformat(end_date)
                daily_activities = daily_activities.filter(date__range=[start, end])
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
        
        if week_id:
            try:
                week_obj = Week.objects.get(id=week_id)
                daily_activities = daily_activities.filter(week=week_obj)
            except Week.DoesNotExist:
                return Response({"error": "Week not found."}, status=404)
        
        if month:
            try:
                month = int(month)
                if month < 1 or month > 12:
                    return Response({"error": "Invalid month. Must be 1-12."}, status=400)
                daily_activities = daily_activities.filter(date__month=month)
                monthly_activities = monthly_activities.filter(month=month)
            except ValueError:
                return Response({"error": "Invalid month format."}, status=400)
        
        if year:
            try:
                year = int(year)
                daily_activities = daily_activities.filter(date__year=year)
                monthly_activities = monthly_activities.filter(year=year)
            except ValueError:
                return Response({"error": "Invalid year format."}, status=400)
        
        # Serialize activities
        daily_serializer = AdminDailyActivitySerializer(daily_activities.order_by('-date'), many=True)
        monthly_serializer = MonthlyActivitySerializer(monthly_activities.order_by('-year', '-month'), many=True)
        
        return Response({
            "daily_activities": daily_serializer.data,
            "monthly_activities": monthly_serializer.data,
            "total_daily": daily_activities.count(),
            "total_monthly": monthly_activities.count()
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['GET'], permission_classes=[IsAuthenticated], url_path='analytics')
    def get_analytics(self, request):
        """
        Get analytics data for admin dashboard.
        Query params: start_date, end_date, week_id, month, year, devotee_id (optional)
        """
        # Check if user is admin
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {"error": "Admin access required."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get filter parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        week_id = request.query_params.get('week_id')
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        devotee_id = request.query_params.get('devotee_id')
        
        # Base queryset
        daily_activities = DailyActivity.objects.all()
        monthly_activities = MonthlyActivity.objects.all()
        
        # Filter by devotee if provided
        if devotee_id:
            try:
                devotee = User.objects.get(pk=devotee_id, is_staff=False, is_superuser=False)
                daily_activities = daily_activities.filter(user=devotee)
                monthly_activities = monthly_activities.filter(user=devotee)
            except User.DoesNotExist:
                return Response({"error": "Devotee not found."}, status=404)
        
        # Apply date filters
        if start_date and end_date:
            try:
                start = date.fromisoformat(start_date)
                end = date.fromisoformat(end_date)
                daily_activities = daily_activities.filter(date__range=[start, end])
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
        
        if week_id:
            try:
                week_obj = Week.objects.get(id=week_id)
                daily_activities = daily_activities.filter(week=week_obj)
            except Week.DoesNotExist:
                return Response({"error": "Week not found."}, status=404)
        
        if month:
            try:
                month = int(month)
                if month < 1 or month > 12:
                    return Response({"error": "Invalid month. Must be 1-12."}, status=400)
                daily_activities = daily_activities.filter(date__month=month)
                monthly_activities = monthly_activities.filter(month=month)
            except ValueError:
                return Response({"error": "Invalid month format."}, status=400)
        
        if year:
            try:
                year = int(year)
                daily_activities = daily_activities.filter(date__year=year)
                monthly_activities = monthly_activities.filter(year=year)
            except ValueError:
                return Response({"error": "Invalid year format."}, status=400)
        
        # Calculate statistics
        total_activities = daily_activities.count()
        total_devotees = User.objects.filter(is_staff=False, is_superuser=False).count()
        
        # Activity completion rates
        hearing_completed = daily_activities.filter(daily_hearing='Completed').count()
        reading_completed = daily_activities.filter(daily_reading='Completed').count()
        total_chanting_rounds = daily_activities.aggregate(total=Sum('daily_chanting'))['total'] or 0
        avg_chanting_rounds = daily_activities.aggregate(avg=Avg('daily_chanting'))['avg'] or 0
        
        # Attendance statistics
        sport_attended = daily_activities.filter(sport_session_attendance='Attended').count()
        sport_total = daily_activities.exclude(sport_session_attendance='No Session Today').count()
        
        # Group by date for chart data
        daily_stats = defaultdict(lambda: {
            'date': None,
            'hearing_completed': 0,
            'reading_completed': 0,
            'chanting_rounds': 0,
            'activities_count': 0
        })
        
        for activity in daily_activities:
            date_str = str(activity.date)
            if date_str not in daily_stats:
                daily_stats[date_str]['date'] = date_str
            daily_stats[date_str]['hearing_completed'] += 1 if activity.daily_hearing == 'Completed' else 0
            daily_stats[date_str]['reading_completed'] += 1 if activity.daily_reading == 'Completed' else 0
            daily_stats[date_str]['chanting_rounds'] += activity.daily_chanting
            daily_stats[date_str]['activities_count'] += 1
        
        # Group by week for weekly chart
        weekly_stats = defaultdict(lambda: {
            'week_name': None,
            'activities_count': 0,
            'hearing_completed': 0,
            'reading_completed': 0,
            'chanting_rounds': 0
        })
        
        for activity in daily_activities.select_related('week'):
            week_id = activity.week.id
            if week_id not in weekly_stats:
                weekly_stats[week_id]['week_name'] = activity.week.name
            weekly_stats[week_id]['activities_count'] += 1
            weekly_stats[week_id]['hearing_completed'] += 1 if activity.daily_hearing == 'Completed' else 0
            weekly_stats[week_id]['reading_completed'] += 1 if activity.daily_reading == 'Completed' else 0
            weekly_stats[week_id]['chanting_rounds'] += activity.daily_chanting
        
        # Group by month for monthly chart
        monthly_stats = defaultdict(lambda: {
            'month': None,
            'year': None,
            'activities_count': 0,
            'hearing_completed': 0,
            'reading_completed': 0,
            'chanting_rounds': 0
        })
        
        for activity in daily_activities:
            month_key = f"{activity.date.year}-{activity.date.month}"
            if month_key not in monthly_stats:
                monthly_stats[month_key]['month'] = activity.date.month
                monthly_stats[month_key]['year'] = activity.date.year
            monthly_stats[month_key]['activities_count'] += 1
            monthly_stats[month_key]['hearing_completed'] += 1 if activity.daily_hearing == 'Completed' else 0
            monthly_stats[month_key]['reading_completed'] += 1 if activity.daily_reading == 'Completed' else 0
            monthly_stats[month_key]['chanting_rounds'] += activity.daily_chanting
        
        return Response({
            "summary": {
                "total_activities": total_activities,
                "total_devotees": total_devotees,
                "hearing_completion_rate": round((hearing_completed / total_activities * 100) if total_activities > 0 else 0, 2),
                "reading_completion_rate": round((reading_completed / total_activities * 100) if total_activities > 0 else 0, 2),
                "total_chanting_rounds": total_chanting_rounds,
                "avg_chanting_rounds": round(avg_chanting_rounds, 2),
                "sport_attendance_rate": round((sport_attended / sport_total * 100) if sport_total > 0 else 0, 2),
            },
            "daily_chart_data": sorted(list(daily_stats.values()), key=lambda x: x['date']),
            "weekly_chart_data": list(weekly_stats.values()),
            "monthly_chart_data": sorted(list(monthly_stats.values()), key=lambda x: (x['year'], x['month'])),
        }, status=status.HTTP_200_OK)











