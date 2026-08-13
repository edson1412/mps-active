# hrms/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Sum, F, Count, Avg
from django.db.models.functions import ExtractYear, ExtractMonth
from django.contrib import messages
from django.utils import timezone
from datetime import date, timedelta
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.urls import reverse
from dateutil.relativedelta import relativedelta


from .models import (
    Officer, Education, PromotionHistory, TransferHistory, LeaveType, LeaveRequest, OfficerDocument,
    OfficerPerformance, OfficeAssignment, Rank, Attendance, DisciplinaryCase, AnnualLeaveBalance,
    PerformanceMetric, Notification
)
from .forms import (
    OfficerForm, EducationFormSet, PromotionHistoryForm, TransferHistoryForm,
    LeaveRequestForm, LeaveApprovalForm, OfficerDocumentForm, OfficerFileResponseForm,
    OfficerPerformanceForm, AttendanceForm, DisciplinaryCaseForm, OfficeAssignmentForm,
    RegionForm, PrisonStationForm
)
from accounts.models import CustomUser
from prison.models import PrisonStation, Region

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Sum, F, Count, Avg
from django.db.models.functions import ExtractYear, ExtractMonth
from django.contrib import messages
from django.utils import timezone
from datetime import date, timedelta
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from dateutil.relativedelta import relativedelta


from .models import (
    Officer, Education, PromotionHistory, TransferHistory, LeaveType, LeaveRequest, OfficerDocument,
    OfficerPerformance, OfficeAssignment, Rank, Attendance, DisciplinaryCase, AnnualLeaveBalance,
    PerformanceMetric, Notification
)
from .forms import (
    OfficerForm, EducationFormSet, PromotionHistoryForm, TransferHistoryForm,
    LeaveRequestForm, LeaveApprovalForm, OfficerDocumentForm, OfficerFileResponseForm,
    OfficerPerformanceForm, AttendanceForm, DisciplinaryCaseForm, OfficeAssignmentForm,
    RegionForm, PrisonStationForm
)
from accounts.models import CustomUser
from prison.models import PrisonStation, Region



# --- Helper Functions for Permissions ---

def is_national_level(user):
    """Checks if the user has a national-level role."""
    return user.is_authenticated and user.role in ['national_commissioner', 'national_hr']

def is_regional_level(user):
    """Checks if the user has a regional-level role."""
    return user.is_authenticated and user.role in ['regional_commanding_officer', 'regional_headquarters_officer', 'regional_hr']

def is_station_level(user):
    """Checks if the user has a station-level role."""
    return user.is_authenticated and user.role in ['officer_in_charge', 'station_officer', 'station_hr']

def can_manage_officer_data(user, officer_station=None, officer_region=None):
    """
    Checks if the user has permission to manage officer data based on their role and assigned location.
    - National level: Can manage all officers.
    - Regional level: Can manage officers in their assigned region.
    - Station level: Can manage officers in their assigned station.
    """
    if user.is_superuser or is_national_level(user):
        return True
    # For regional level, check if the user's region matches the officer's region
    if is_regional_level(user) and user.region and officer_region and user.region == officer_region:
        return True
    # For station level, check if the user's station matches the officer's station
    if is_station_level(user) and user.prison_station and officer_station and user.prison_station == officer_station:
        return True
    return False

def can_manage_regions(user):
    """
    Checks if the user has permission to manage regions (only national level or superuser).
    """
    return user.is_superuser or is_national_level(user)

def can_manage_prison_stations(user, station_region=None):
    """
    Checks if the user has permission to manage prison stations.
    - National level: Can manage all stations.
    - Regional level: Can manage stations within their assigned region.
    """
    if user.is_superuser or is_national_level(user):
        return True
    if is_regional_level(user) and user.region and station_region and user.region == station_region:
        return True
    return False


def get_filtered_officers_queryset(user):
    """
    Returns a queryset of officers visible to the current user based on their role.
    """
    print(f"DEBUG: get_filtered_officers_queryset called for user: {user.username}, role: {user.role}")
    if user.is_superuser or is_national_level(user):
        print("DEBUG: User is Superuser or National Level. Returning all officers.")
        return Officer.objects.all()
    elif is_regional_level(user) and user.region:
        print(f"DEBUG: User is Regional Level. Filtering by region: {user.region.name}")
        # Regional users see all officers in their assigned region, across all stations in that region
        return Officer.objects.filter(region=user.region)
    elif is_station_level(user) and user.prison_station:
        print(f"DEBUG: User is Station Level. Filtering by station: {user.prison_station.name}")
        return Officer.objects.filter(prison_station=user.prison_station)
    print("DEBUG: No matching role/location. Returning empty queryset.")
    return Officer.objects.none() # No officers visible if no matching role/location

def get_recent_files_queryset(user):
    """
    Returns officer documents visible to the user ordered by recency.
    """
    if user.is_superuser or is_national_level(user):
        return OfficerDocument.objects.order_by('-uploaded_at')
    if is_regional_level(user) and user.region:
        return OfficerDocument.objects.filter(officer__region=user.region).order_by('-uploaded_at')
    if is_station_level(user) and user.prison_station:
        return OfficerDocument.objects.filter(officer__prison_station=user.prison_station).order_by('-uploaded_at')
    return OfficerDocument.objects.none()

def get_pending_leave_requests_queryset(user):
    """
    Returns pending leave requests visible to the user ordered by newest request first.
    """
    if user.is_superuser or is_national_level(user):
        return LeaveRequest.objects.filter(status='pending').order_by('-requested_at')
    if is_regional_level(user) and user.region:
        return LeaveRequest.objects.filter(
            status='pending',
            officer__region=user.region
        ).order_by('-requested_at')
    if is_station_level(user) and user.prison_station:
        return LeaveRequest.objects.filter(
            status='pending',
            officer__prison_station=user.prison_station
        ).order_by('-requested_at')
    return LeaveRequest.objects.none()

def get_retirement_alerts(officers_queryset, months_ahead, retirement_age=60):
    """
    Builds a list of officers approaching retirement within the provided window.
    Returns dictionaries friendly for templates and APIs.
    """
    today = date.today()
    cutoff_date = today + relativedelta(months=+months_ahead)
    alerts = []

    for officer in officers_queryset.exclude(date_of_birth__isnull=True):
        if not officer.date_of_birth:
            continue
        retirement_date = officer.date_of_birth + relativedelta(years=retirement_age)
        if today <= retirement_date <= cutoff_date:
            alerts.append({
                'full_name': officer.full_name,
                'service_number': officer.service_number,
                'station_name': officer.prison_station.name if officer.prison_station else 'Unassigned',
                'retirement_date': retirement_date,
                'detail_url': reverse('hrms:officer_detail', kwargs={'service_number': officer.service_number})
            })

    alerts.sort(key=lambda item: item['retirement_date'])
    return alerts

def sync_officer_leave_statuses():
    """
    Ensures officer.status reflects whether they are currently on an approved leave.
    - Officers with an active approved leave window move to 'on_leave'.
    - Officers whose approved leave window has passed move back to 'active'.
    """
    today = date.today()

    officers_with_current_leave_ids = list(
        Officer.objects.filter(
            leave_requests__status='approved',
            leave_requests__start_date__lte=today,
            leave_requests__end_date__gte=today,
            status='active'
        ).values_list('id', flat=True)
    )
    if officers_with_current_leave_ids:
        Officer.objects.filter(id__in=officers_with_current_leave_ids).update(status='on_leave')

    officers_ready_for_activation_ids = list(
        Officer.objects.filter(
            status='on_leave',
            leave_requests__status='approved',
            leave_requests__end_date__lt=today
        ).exclude(
            leave_requests__status='approved',
            leave_requests__start_date__lte=today,
            leave_requests__end_date__gte=today
        ).values_list('id', flat=True)
    )
    if officers_ready_for_activation_ids:
        Officer.objects.filter(id__in=officers_ready_for_activation_ids).update(status='active')


# --- Notification Helper Function ---
def create_notification(recipient, sender, message, notification_type, content_object=None):
    """
    Creates a new notification.
    recipient: The CustomUser who receives the notification.
    sender: The CustomUser who initiated the action (can be None for system alerts).
    message: The notification message.
    notification_type: One of the NOTIFICATION_TYPE_CHOICES from Notification model.
    content_object: The related Django model instance (e.g., LeaveRequest, OfficerDocument).
    """
    content_type = None
    object_id = None
    if content_object:
        content_type = ContentType.objects.get_for_model(content_object)
        object_id = content_object.pk

    Notification.objects.create(
        recipient=recipient,
        sender=sender,
        message=message,
        notification_type=notification_type,
        content_type=content_type,
        object_id=object_id
    )



# --- Dashboard View ---

@login_required
def dashboard_view(request):
    """
    Displays the HRMS dashboard with key metrics and recent activities
    filtered by the user's permissions.
    """
    sync_officer_leave_statuses()
    user = request.user
    officers_queryset = get_filtered_officers_queryset(user)

    # Use aggregate to get counts more efficiently
    total_officers = officers_queryset.count()
    status_counts = officers_queryset.values('status').annotate(count=Count('status'))
    active_officers = 0
    on_leave_officers = 0
    retired_officers = 0
    for item in status_counts:
        if item['status'] == 'active':
            active_officers = item['count']
        elif item['status'] == 'on_leave':
            on_leave_officers = item['count']
        elif item['status'] == 'retired':
            retired_officers = item['count']

    retirement_alerts_12 = get_retirement_alerts(officers_queryset, months_ahead=12)
    retirement_alerts_4 = get_retirement_alerts(officers_queryset, months_ahead=4)

    recent_files_queryset = get_recent_files_queryset(user)
    recent_files = recent_files_queryset[:5]
    recent_files_total = recent_files_queryset.count()

    pending_leave_queryset = get_pending_leave_requests_queryset(user)
    pending_leave_requests = pending_leave_queryset[:5]
    pending_leave_requests_total = pending_leave_queryset.count()

    def calculate_percentage(part):
        return round((part / total_officers) * 100, 2) if total_officers else 0

    active_percentage = calculate_percentage(active_officers)
    on_leave_percentage = calculate_percentage(on_leave_officers)
    retired_percentage = calculate_percentage(retired_officers)

    # Fetch unread notifications for the current user (for initial page load)
    unread_notifications = Notification.objects.filter(recipient=user, is_read=False).order_by('-created_at')[:5]

    context = {
        'total_officers': total_officers,
        'active_officers': active_officers,
        'on_leave_officers': on_leave_officers,
        'retired_officers': retired_officers,
        'status_distribution': {
            'active': active_officers,
            'on_leave': on_leave_officers,
            'retired': retired_officers,
        },
        'retirement_alerts_12': retirement_alerts_12,
        'retirement_alerts_4': retirement_alerts_4,
        'recent_files': recent_files,
        'recent_files_total': recent_files_total,
        'pending_leave_requests': pending_leave_requests,
        'pending_leave_requests_total': pending_leave_requests_total,
        'user_role': user.get_role_display(),
        'unread_notifications': unread_notifications,
        'user': user,
        'is_national_level': is_national_level(user),
        'is_regional_level': is_regional_level(user),
        'is_station_level': is_station_level(user),
        'title': 'Dashboard',
        'last_refreshed': timezone.now(),
        'active_percentage': active_percentage,
        'on_leave_percentage': on_leave_percentage,
        'retired_percentage': retired_percentage,
        'initial_metrics': {
            'total_officers': total_officers,
            'active_officers': active_officers,
            'on_leave_officers': on_leave_officers,
            'retired_officers': retired_officers,
        }
    }

    return render(request, 'hrms/dashboard.html', context)


@login_required
def dashboard_data_api_view(request):
    """
    Lightweight JSON endpoint consumed by the dashboard front-end for live updates.
    """
    sync_officer_leave_statuses()
    user = request.user
    officers_queryset = get_filtered_officers_queryset(user)

    total_officers = officers_queryset.count()
    status_counts = officers_queryset.values('status').annotate(count=Count('status'))
    status_map = {'active': 0, 'on_leave': 0, 'retired': 0}
    for item in status_counts:
        status_map[item['status']] = item['count']

    retirement_alerts_4 = get_retirement_alerts(officers_queryset, months_ahead=4)
    retirement_alerts_12 = get_retirement_alerts(officers_queryset, months_ahead=12)

    recent_files = get_recent_files_queryset(user)[:5]
    pending_leaves = get_pending_leave_requests_queryset(user)[:5]
    unread_notifications = Notification.objects.filter(recipient=user, is_read=False).order_by('-created_at')[:5]

    data = {
        'timestamp': timezone.now().isoformat(),
        'metrics': {
            'total_officers': total_officers,
            'active_officers': status_map['active'],
            'on_leave_officers': status_map['on_leave'],
            'retired_officers': status_map['retired'],
        },
        'retirement_alerts': {
            'next_four_months': [
                {
                    'full_name': alert['full_name'],
                    'service_number': alert['service_number'],
                    'station_name': alert['station_name'],
                    'retirement_date': alert['retirement_date'].isoformat(),
                    'detail_url': alert['detail_url'],
                } for alert in retirement_alerts_4
            ],
            'next_twelve_months': [
                {
                    'full_name': alert['full_name'],
                    'service_number': alert['service_number'],
                    'station_name': alert['station_name'],
                    'retirement_date': alert['retirement_date'].isoformat(),
                    'detail_url': alert['detail_url'],
                } for alert in retirement_alerts_12
            ],
        },
        'recent_files': [
            {
                'file_name': officer_file.file_name,
                'uploader': officer_file.officer.full_name if officer_file.officer else 'Unknown Officer',
                'uploaded_at': officer_file.uploaded_at.isoformat() if officer_file.uploaded_at else None,
                'status_display': officer_file.get_status_display(),
                'status': officer_file.status,
                'detail_url': reverse('hrms:officer_file_detail', kwargs={'pk': officer_file.pk})
            } for officer_file in recent_files
        ],
        'pending_leave_requests': [
            {
                'officer_name': leave.officer.full_name if leave.officer else 'Unknown Officer',
                'leave_type': leave.leave_type.name if leave.leave_type else 'N/A',
                'start_date': leave.start_date.isoformat() if leave.start_date else None,
                'end_date': leave.end_date.isoformat() if leave.end_date else None,
                'requested_at': leave.requested_at.isoformat() if leave.requested_at else None,
                'detail_url': reverse('hrms:leave_request_detail', kwargs={'pk': leave.pk})
            } for leave in pending_leaves
        ],
        'notifications': [
            {
                'message': notification.message,
                'created_at': notification.created_at.isoformat() if notification.created_at else None,
                'sender': notification.sender.get_full_name() if notification.sender else 'System',
                'detail_url': notification.get_absolute_url()
            } for notification in unread_notifications
        ]
    }

    return JsonResponse(data)

# --- Officer Management Views ---

@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def officer_list_view(request):
    """
    Displays a list of all officers with filtering options.
    """
    sync_officer_leave_statuses()
    # Get all available filter options to pass to the template
    ranks = Rank.objects.all().order_by('name')
    stations = PrisonStation.objects.all().order_by('name')
    regions = Region.objects.all().order_by('name')

    # Start from the officers this user is allowed to see (region/station scoped)
    officers = get_filtered_officers_queryset(request.user)

    if is_regional_level(request.user) and request.user.region:
        stations = stations.filter(region=request.user.region)
        regions = regions.filter(pk=request.user.region.pk)
    elif is_station_level(request.user) and request.user.prison_station:
        stations = stations.filter(pk=request.user.prison_station.pk)
        regions = regions.filter(pk=request.user.prison_station.region_id)

    # Get filter parameters from the request
    current_rank_filter = request.GET.get('rank', 'all')
    current_station_filter = request.GET.get('station', 'all')
    current_region_filter = request.GET.get('region', 'all')
    current_status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')

    # Apply filters based on request parameters
    filter_kwargs = {}
    if current_rank_filter and current_rank_filter != 'all':
        filter_kwargs['rank__name'] = current_rank_filter

    if current_station_filter and current_station_filter != 'all':
        filter_kwargs['prison_station__name'] = current_station_filter

    if current_status_filter and current_status_filter != 'all':
        filter_kwargs['status'] = current_status_filter

    # Apply the regional filter only for national level users
    if is_national_level(request.user) and current_region_filter and current_region_filter != 'all':
        filter_kwargs['region__name'] = current_region_filter

    # Filter the queryset
    if filter_kwargs:
        officers = officers.filter(**filter_kwargs)

    # Apply search query
    if search_query:
        officers = officers.filter(
            Q(service_number__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(surname__icontains=search_query) |
            Q(rank__name__icontains=search_query)
        )

    context = {
        'title': 'Officers',
        'officers': officers,
        'ranks': ranks,
        'stations': stations,
        'regions': regions,
        'current_rank_filter': current_rank_filter,
        'current_station_filter': current_station_filter,
        'current_region_filter': current_region_filter,
        'current_status_filter': current_status_filter,
        'search_query': search_query,
        'is_national_level_user': is_national_level(request.user)
    }
    return render(request, 'hrms/officer_list.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def officer_create_view(request):
    """
    Allows authorized users to add new officer records.
    Station HR can only add officers to their station.
    Regional HR can only add officers to stations within their region.
    National HR/Commissioner can add officers to any station/region.
    """
    user = request.user
    if not (user.is_superuser or is_national_level(user) or is_regional_level(user) or is_station_level(user)):
        messages.error(request, "You do not have permission to add officers.")
        return redirect('hrms:dashboard')

    if request.method == 'POST':
        officer_form = OfficerForm(request.POST, request.FILES, user=user)
        education_formset = EducationFormSet(request.POST, request.FILES, prefix='education')

        if officer_form.is_valid() and education_formset.is_valid():
            officer = officer_form.save(commit=False)

            # Enforce location constraints based on user role
            if is_station_level(user) and user.prison_station:
                officer.prison_station = user.prison_station
                officer.region = officer.prison_station.region # Ensure region is set from station
            elif is_regional_level(user) and user.region:
                # If a regional user, ensure the selected region for the officer matches their own
                if officer.region and officer.region != user.region: # Check if officer.region is set before comparing
                    messages.error(request, "You can only add officers to stations within your assigned region.")
                    return render(request, 'hrms/officer_form.html', {
                        'officer_form': officer_form,
                        'education_formset': education_formset,
                        'title': 'Add New Officer'
                    })
                # Ensure the selected prison_station is within the user's region
                if officer.prison_station and officer.prison_station.region != user.region:
                     messages.error(request, "The selected prison station is not within your assigned region.")
                     return render(request, 'hrms/officer_form.html', {
                        'officer_form': officer_form,
                        'education_formset': education_formset,
                        'title': 'Add New Officer'
                    })

            officer.save()

            education_formset.instance = officer
            education_formset.save()

            messages.success(request, f"Officer {officer.full_name} added successfully.")

            # Create notification for relevant users (e.g., National HR, Regional HR)
            hr_users = CustomUser.objects.filter(
                Q(is_superuser=True) |
                Q(role='national_commissioner') | # National Commissioner
                Q(role='national_hr') |           # National HR
                Q(role='regional_commanding_officer', region=officer.region) | # RCO in officer's region
                Q(role='regional_headquarters_officer', region=officer.region) | # RHO in officer's region
                Q(role='regional_hr', region=officer.region) # Regional HR in officer's region
            ).distinct()
            for hr_user in hr_users:
                if hr_user != user: # Don't notify the user who just created the officer
                    create_notification(
                        recipient=hr_user,
                        sender=user,
                        message=f"New officer {officer.full_name} ({officer.service_number}) added to {officer.prison_station.name if officer.prison_station else 'an unassigned station'} in {officer.region.name if officer.region else 'an unassigned region'}.",
                        notification_type='new_officer',
                        content_object=officer
                    )

            return redirect('hrms:officer_detail', service_number=officer.service_number)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        officer_form = OfficerForm(user=user)
        education_formset = EducationFormSet(prefix='education')

    context = {
        'officer_form': officer_form,
        'education_formset': education_formset,
        'title': 'Add New Officer'
    }
    return render(request, 'hrms/officer_form.html', context)

@login_required
def officer_detail_view(request, service_number):
    """
    Displays detailed information about a single officer.
    Permissions:
    - National level: View all.
    - Regional level: View officers in their region.
    - Station level: View officers in their station.
    """
    officer = get_object_or_404(Officer.objects.select_related('rank', 'prison_station', 'region', 'current_office_assignment'), service_number=service_number)
    user = request.user

    # Check permission to view this officer
    if not can_manage_officer_data(user, officer.prison_station, officer.region):
        messages.error(request, "You do not have permission to view this officer's details.")
        return redirect('hrms:dashboard')

    # Fetching limited records for display on detail page
    education_qualifications = officer.education.all().order_by('-year_obtained')[:5]
    promotion_history = officer.promotions.all().order_by('-promotion_date')[:5]
    transfer_history = officer.transfers.all().order_by('-transfer_date')[:5]
    leave_requests = officer.leave_requests.all().order_by('-requested_at')[:5]
    officer_documents = officer.documents.all().order_by('-uploaded_at')[:5]
    performance_records = officer.performance_records.all().order_by('-date')[:5]
    attendance_records = officer.attendance_records.all().order_by('-date')[:5]
    disciplinary_cases = officer.disciplinary_cases.all().order_by('-case_date')[:5]


    # Calculate current annual leave balance
    annual_leave_balance_obj = AnnualLeaveBalance.objects.filter(officer=officer, year=date.today().year).first()
    annual_leave_balance = annual_leave_balance_obj.remaining_days if annual_leave_balance_obj else 0
    total_entitled_days = annual_leave_balance_obj.total_days_entitled if annual_leave_balance_obj else 0

    # Check for forfeited leave (if previous year's annual leave wasn't fully taken)
    previous_year_start = date(date.today().year - 1, 4, 1) # Assuming leave year starts April 1st

    previous_year_balance_obj = AnnualLeaveBalance.objects.filter(officer=officer, year=previous_year_start.year).first()
    forfeited_leave = 0
    if previous_year_balance_obj:
        forfeited_leave = max(0, previous_year_balance_obj.total_days_entitled - previous_year_balance_obj.days_taken)


    context = {
        'officer': officer,
        'education_qualifications': education_qualifications,
        'promotion_history': promotion_history,
        'transfer_history': transfer_history,
        'leave_requests': leave_requests,
        'officer_documents': officer_documents,
        'performance_records': performance_records,
        'attendance_records': attendance_records,
        'disciplinary_cases': disciplinary_cases,
        'annual_leave_balance': annual_leave_balance,
        'total_entitled_days': total_entitled_days,
        'forfeited_leave': forfeited_leave,
    }
    return render(request, 'hrms/officer_detail.html', context)

@login_required
def officer_update_view(request, service_number):
    """
    Allows authorized users to update existing officer records.
    Permissions are checked by `can_manage_officer_data`.
    """
    officer = get_object_or_404(Officer, service_number=service_number)
    user = request.user

    if not can_manage_officer_data(user, officer.prison_station, officer.region):
        messages.error(request, "You do not have permission to edit this officer's details.")
        return redirect('hrms:officer_detail', service_number=officer.service_number)

    if request.method == 'POST':
        officer_form = OfficerForm(request.POST, request.FILES, instance=officer, user=user)
        education_formset = EducationFormSet(request.POST, request.FILES, prefix='education', instance=officer) # Pass instance to formset

        if officer_form.is_valid() and education_formset.is_valid():
            officer = officer_form.save(commit=False)

            # Enforce location constraints based on user role (similar to create view)
            if is_station_level(user) and user.prison_station:
                officer.prison_station = user.prison_station
                officer.region = officer.prison_station.region # Ensure region is set from station
            elif is_regional_level(user) and user.region:
                if officer.region and officer.region != user.region: # Check if officer.region is set before comparing
                    messages.error(request, "You can only update officers within your assigned region.")
                    return render(request, 'hrms/officer_form.html', {
                        'officer_form': officer_form,
                        'education_formset': education_formset,
                        'title': f'Edit Officer: {officer.service_number}'
                    })
                if officer.prison_station and officer.prison_station.region != user.region:
                     messages.error(request, "The selected prison station is not within your assigned region.")
                     return render(request, 'hrms/officer_form.html', {
                        'officer_form': officer_form,
                        'education_formset': education_formset,
                        'title': f'Edit Officer: {officer.service_number}'
                    })

            officer.save()
            education_formset.instance = officer
            education_formset.save()

            messages.success(request, f"Officer {officer.full_name} updated successfully.")
            return redirect('hrms:officer_detail', service_number=officer.service_number)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        officer_form = OfficerForm(instance=officer, user=user)
        education_formset = EducationFormSet(instance=officer, prefix='education')

    context = {
        'officer_form': officer_form,
        'education_formset': education_formset,
        'title': f'Edit Officer: {officer.full_name}'
    }
    return render(request, 'hrms/officer_form.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u))
def officer_delete_view(request, service_number):
    """
    Deletes an officer record. Restricted to national/superuser.
    Regional users can delete officers in their region.
    """
    officer = get_object_or_404(Officer, service_number=service_number)
    user = request.user

    if not can_manage_officer_data(user, officer.prison_station, officer.region):
        messages.error(request, "You do not have permission to delete this officer.")
        return redirect('hrms:officer_detail', service_number=service_number)

    if request.method == 'POST':
        officer_full_name = officer.full_name
        officer.delete()
        messages.success(request, f"Officer {officer_full_name} deleted successfully.")
        return redirect('hrms:officer_list')

    context = {
        'officer': officer
    }
    return render(request, 'hrms/officer_confirm_delete.html', context)

# --- Service History Views (Promotions & Transfers) ---

@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def service_history_create_view(request, service_number):
    """
    Allows adding new promotion or transfer history for an officer.
    """
    officer = get_object_or_404(Officer, service_number=service_number)
    user = request.user

    if not can_manage_officer_data(user, officer.prison_station, officer.region):
        messages.error(request, "You do not have permission to add service history for this officer.")
        return redirect('hrms:officer_detail', service_number=officer.service_number)

    promotion_form = PromotionHistoryForm(prefix='promotion')
    transfer_form = TransferHistoryForm(prefix='transfer')

    if request.method == 'POST':
        if 'promotion_submit' in request.POST:
            promotion_form = PromotionHistoryForm(request.POST, prefix='promotion')
            if promotion_form.is_valid():
                promotion = promotion_form.save(commit=False)
                promotion.officer = officer
                promotion.recorded_by = user
                promotion.save()
                # Update officer's current rank if promoted
                officer.rank = promotion.new_rank
                officer.save()
                messages.success(request, "Promotion history added successfully.")

                # Create notification for the officer
                if officer.user:
                    create_notification(
                        recipient=officer.user,
                        sender=user,
                        message=f"Congratulations! You have been promoted to {promotion.new_rank.get_name_display()} on {promotion.promotion_date.strftime('%Y-%m-%d')}.",
                        notification_type='promotion',
                        content_object=promotion
                    )
                # Also notify relevant HR (e.g., National HR, Regional HR)
                hr_users = CustomUser.objects.filter(
                    Q(is_superuser=True) |
                    Q(role='national_commissioner') |
                    Q(role='national_hr') |
                    Q(role='regional_commanding_officer', region=officer.region) |
                    Q(role='regional_headquarters_officer', region=officer.region) |
                    Q(role='regional_hr', region=officer.region)
                ).distinct()
                for hr_user in hr_users:
                    if hr_user != user:
                        create_notification(
                            recipient=hr_user,
                            sender=user,
                            message=f"Officer {officer.full_name} promoted to {promotion.new_rank.get_name_display()}.",
                            notification_type='promotion',
                            content_object=promotion
                        )


                return redirect('hrms:officer_detail', service_number=officer.service_number)
            else:
                messages.error(request, "Error adding promotion history. Please correct the errors.")
        elif 'transfer_submit' in request.POST:
            transfer_form = TransferHistoryForm(request.POST, prefix='transfer')
            if transfer_form.is_valid():
                transfer = transfer_form.save(commit=False)
                transfer.officer = officer
                transfer.recorded_by = user
                transfer.save()
                # Update officer's current prison station and region if transferred
                officer.prison_station = transfer.new_station
                officer.region = transfer.new_station.region
                officer.save()
                messages.success(request, "Transfer history added successfully.")

                # Create notification for the officer
                if officer.user:
                    create_notification(
                        recipient=officer.user,
                        sender=user,
                        message=f"You have been transferred to {transfer.new_station.name} on {transfer.transfer_date.strftime('%Y-%m-%d')}.",
                        notification_type='transfer',
                        content_object=transfer
                    )
                # Also notify relevant HR
                hr_users = CustomUser.objects.filter(
                    Q(is_superuser=True) |
                    Q(role='national_commissioner') |
                    Q(role='national_hr') |
                    Q(role='regional_commanding_officer', region=officer.region) |
                    Q(role='regional_headquarters_officer', region=officer.region) |
                    Q(role='regional_hr', region=officer.region)
                ).distinct()
                for hr_user in hr_users:
                    if hr_user != user:
                        create_notification(
                            recipient=hr_user,
                            sender=user,
                            message=f"Officer {officer.full_name} transferred to {transfer.new_station.name}.",
                            notification_type='transfer',
                            content_object=transfer
                        )

                return redirect('hrms:officer_detail', service_number=officer.service_number)
            else:
                messages.error(request, "Error adding transfer history. Please correct the errors.")

    context = {
        'officer': officer,
        'promotion_form': promotion_form,
        'transfer_form': transfer_form,
        'title': f'Add Service History for {officer.full_name}'
    }
    return render(request, 'hrms/service_history_form.html', context)

@login_required
def service_history_list_view(request):
    """
    Lists promotion and transfer records relevant to the user's role.
    Can be filtered by officer service_number and type (promotion/transfer).
    """
    user = request.user
    officer_service_number = request.GET.get('officer_service_number')
    history_type = request.GET.get('type') # 'promotion' or 'transfer'

    officer_filter = None
    if officer_service_number:
        officer_filter = get_object_or_404(Officer, service_number=officer_service_number)

    promotions = PromotionHistory.objects.none()
    transfers = TransferHistory.objects.none()

    if history_type == 'promotion' or not history_type:
        promotions = PromotionHistory.objects.all().select_related('officer', 'previous_rank', 'new_rank', 'recorded_by')
        if officer_filter:
            promotions = promotions.filter(officer=officer_filter)
        if is_station_level(user) and user.prison_station:
            promotions = promotions.filter(officer__prison_station=user.prison_station)
        elif is_regional_level(user) and user.region:
            promotions = promotions.filter(officer__region=user.region)
        promotions = promotions.order_by('-promotion_date')

    if history_type == 'transfer' or not history_type:
        transfers = TransferHistory.objects.all().select_related('officer', 'previous_station', 'new_station', 'recorded_by')
        if officer_filter:
            transfers = transfers.filter(officer=officer_filter)
        if is_station_level(user) and user.prison_station:
            transfers = transfers.filter(officer__prison_station=user.prison_station)
        elif is_regional_level(user) and user.region:
            transfers = transfers.filter(officer__region=user.region)
        transfers = transfers.order_by('-transfer_date')

    title = "Service History"
    if officer_filter:
        title = f"Service History for {officer_filter.full_name}"
    if history_type == 'promotion':
        title = f"Promotion History for {officer_filter.full_name if officer_filter else 'All Officers'}"
    elif history_type == 'transfer':
        title = f"Transfer History for {officer_filter.full_name if officer_filter else 'All Officers'}"


    context = {
        'promotions': promotions,
        'transfers': transfers,
        'officer_filter': officer_filter,
        'history_type': history_type,
        'title': title,
    }
    return render(request, 'hrms/service_history_list.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def service_history_update_view(request, pk):
    """
    Allows updating an existing promotion or transfer history record.
    """
    promotion_history = PromotionHistory.objects.filter(pk=pk).first()
    transfer_history = TransferHistory.objects.filter(pk=pk).first()

    if promotion_history:
        instance = promotion_history
        form_class = PromotionHistoryForm
        history_type = 'Promotion'
        officer = instance.officer
    elif transfer_history:
        instance = transfer_history
        form_class = TransferHistoryForm
        history_type = 'Transfer'
        officer = instance.officer
    else:
        messages.error(request, "Service history record not found.")
        return redirect('hrms:dashboard')

    user = request.user
    if not can_manage_officer_data(user, officer.prison_station, officer.region):
        messages.error(request, "You do not have permission to edit this service history record.")
        return redirect('hrms:officer_detail', service_number=officer.service_number)

    if request.method == 'POST':
        form = form_class(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, f"{history_type} history updated successfully.")
            return redirect('hrms:officer_detail', service_number=officer.service_number)
        else:
            messages.error(request, f"Error updating {history_type} history. Please correct the errors.")
    else:
        form = form_class(instance=instance)

    context = {
        'form': form,
        'officer': officer,
        'history_type': history_type,
        'title': f'Edit {history_type} History for {officer.full_name}'
    }
    return render(request, 'hrms/service_history_form.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u))
def service_history_delete_view(request, pk):
    """
    Allows deleting a promotion or transfer history record.
    """
    promotion_history = PromotionHistory.objects.filter(pk=pk).first()
    transfer_history = TransferHistory.objects.filter(pk=pk).first()

    if promotion_history:
        instance = promotion_history
        history_type = 'Promotion'
        officer = instance.officer
    elif transfer_history:
        instance = transfer_history
        history_type = 'Transfer'
        officer = instance.officer
    else:
        messages.error(request, "Service history record not found.")
        return redirect('hrms:dashboard')

    user = request.user
    if not (is_national_level(user) or user.is_superuser):
        messages.error(request, "You do not have permission to delete service history records.")
        return redirect('hrms:officer_detail', service_number=officer.service_number)

    if request.method == 'POST':
        instance.delete()
        messages.success(request, f"{history_type} history deleted successfully.")
        return redirect('hrms:officer_detail', service_number=officer.service_number)

    context = {
        'officer': officer,
        'history_type': history_type,
        'instance': instance,
    }
    return render(request, 'hrms/service_history_confirm_delete.html', context)

# --- Leave Requests Views ---

@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def leave_request_create_view(request, service_number):
    """
    Allows an officer or HR to request leave for an officer.
    """
    officer = get_object_or_404(Officer, service_number=service_number)
    user = request.user

    if not can_manage_officer_data(user, officer.prison_station, officer.region):
        messages.error(request, "You do not have permission to request leave for this officer.")
        return redirect('hrms:officer_detail', service_number=officer.service_number)

    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, request.FILES)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.officer = officer
            leave_request.save()
            messages.success(request, "Leave request submitted successfully.")

            # Notify relevant HR users about the new leave request
            hr_users_to_notify = CustomUser.objects.filter(
                Q(is_superuser=True) |
                Q(role='national_commissioner') |
                Q(role='national_hr') |
                Q(role='regional_commanding_officer', region=officer.region) |
                Q(role='regional_headquarters_officer', region=officer.region) |
                Q(role='regional_hr', region=officer.region) |
                Q(role='station_officer_in_charge', prison_station=officer.prison_station) |
                Q(role='station_hr', prison_station=officer.prison_station)
            ).distinct()

            for hr_user in hr_users_to_notify:
                if hr_user != user:
                    create_notification(
                        recipient=hr_user,
                        sender=user,
                        message=f"New leave request from {officer.full_name} for {leave_request.leave_type.name} ({leave_request.start_date.strftime('%Y-%m-%d')}).",
                        notification_type='leave_request',
                        content_object=leave_request
                    )

            return redirect('hrms:leave_request_detail', pk=leave_request.pk)
        else:
            messages.error(request, "Error submitting leave request. Please correct the errors.")
    else:
        form = LeaveRequestForm()

    context = {
        'form': form,
        'officer': officer,
        'title': f'Request Leave for {officer.full_name}'
    }
    return render(request, 'hrms/leave_request_form.html', context)

@login_required
def leave_request_list_view(request):
    """
    Lists leave requests relevant to the user's role.
    Can be filtered by officer service_number.
    """
    user = request.user
    leave_requests = LeaveRequest.objects.all().select_related('officer', 'leave_type')

    if is_station_level(user) and user.prison_station:
        leave_requests = leave_requests.filter(officer__prison_station=user.prison_station)
    elif is_regional_level(user) and user.region:
        leave_requests = leave_requests.filter(officer__region=user.region)
    # National level/superuser sees all

    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        leave_requests = leave_requests.filter(status=status_filter)

    officer_service_number = request.GET.get('officer_service_number')
    officer_filter = None
    if officer_service_number:
        officer_filter = get_object_or_404(Officer, service_number=officer_service_number)
        leave_requests = leave_requests.filter(officer=officer_filter)

    context = {
        'leave_requests': leave_requests.order_by('-requested_at'),
        'title': 'Leave Requests',
        'current_status_filter': status_filter,
        'officer_filter': officer_filter,
    }
    return render(request, 'hrms/leave_request_list.html', context)

@login_required
def leave_request_detail_view(request, pk):
    """
    Displays details of a single leave request.
    """
    leave_request = get_object_or_404(LeaveRequest.objects.select_related('officer', 'leave_type', 'approved_by'), pk=pk)
    user = request.user

    if not can_manage_officer_data(user, leave_request.officer.prison_station, leave_request.officer.region):
        messages.error(request, "You do not have permission to view this leave request.")
        return redirect('hrms:leave_request_list')

    context = {
        'leave_request': leave_request,
        'title': f'Leave Request: {leave_request.officer.full_name} ({leave_request.leave_type.name})'
    }
    return render(request, 'hrms/leave_request_detail.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def leave_request_approve_view(request, pk):
    """
    Allows authorized users to approve a leave request.
    """
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    user = request.user

    if not can_manage_officer_data(user, leave_request.officer.prison_station, leave_request.officer.region):
        messages.error(request, "You do not have permission to approve this leave request.")
        return redirect('hrms:leave_request_detail', pk=pk)

    if leave_request.status != 'pending':
        messages.warning(request, "This leave request has already been processed.")
        return redirect('hrms:leave_request_detail', pk=pk)

    if request.method == 'POST':
        form = LeaveApprovalForm(request.POST, instance=leave_request)
        if form.is_valid():
            leave_request.status = 'approved'
            leave_request.approved_by = user
            leave_request.approved_at = timezone.now()
            leave_request.save()

            if leave_request.start_date <= date.today() <= leave_request.end_date:
                officer = leave_request.officer
                officer.status = 'on_leave'
                officer.save()

            if leave_request.leave_type.name == 'Annual Leave':
                current_year = date.today().year
                annual_balance, created = AnnualLeaveBalance.objects.get_or_create(
                    officer=leave_request.officer,
                    year=current_year,
                    defaults={'total_days_entitled': leave_request.officer.rank.leave_days_annual if leave_request.officer.rank else 0}
                )
                annual_balance.days_taken += leave_request.number_of_days
                annual_balance.save()

            messages.success(request, "Leave request approved successfully.")

            if leave_request.officer.user:
                create_notification(
                    recipient=leave_request.officer.user,
                    sender=user,
                    message=f"Your leave request for {leave_request.leave_type.name} from {leave_request.start_date.strftime('%Y-%m-%d')} has been APPROVED.",
                    notification_type='leave_request',
                    content_object=leave_request
                )

            return redirect('hrms:leave_request_detail', pk=pk)
        else:
            messages.error(request, "Error approving leave request. Please correct the errors.")
    else:
        form = LeaveApprovalForm(instance=leave_request)

    context = {
        'form': form,
        'leave_request': leave_request,
        'title': f'Approve Leave for {leave_request.officer.full_name}'
    }
    return render(request, 'hrms/leave_approval_form.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def leave_request_reject_view(request, pk):
    """
    Allows authorized users to reject a leave request.
    """
    leave_request = get_object_or_404(LeaveRequest, pk=pk)
    user = request.user

    if not can_manage_officer_data(user, leave_request.officer.prison_station, leave_request.officer.region):
        messages.error(request, "You do not have permission to reject this leave request.")
        return redirect('hrms:leave_request_detail', pk=pk)

    if leave_request.status != 'pending':
        messages.warning(request, "This leave request has already been processed.")
        return redirect('hrms:leave_request_detail', pk=pk)

    if request.method == 'POST':
        form = LeaveApprovalForm(request.POST, instance=leave_request)
        if form.is_valid():
            leave_request.status = 'rejected'
            leave_request.approved_by = user
            leave_request.approved_at = timezone.now()
            leave_request.save()
            messages.success(request, "Leave request rejected successfully.")

            if leave_request.officer.user:
                create_notification(
                    recipient=leave_request.officer.user,
                    sender=user,
                    message=f"Your leave request for {leave_request.leave_type.name} from {leave_request.start_date.strftime('%Y-%m-%d')} has been REJECTED. Reason: {leave_request.rejection_notes or 'N/A'}",
                    notification_type='leave_request',
                    content_object=leave_request
                )

            return redirect('hrms:leave_request_detail', pk=pk)
        else:
            messages.error(request, "Error rejecting leave request. Please provide rejection notes.")
    else:
        form = LeaveApprovalForm(instance=leave_request)

    context = {
        'form': form,
        'leave_request': leave_request,
        'title': f'Reject Leave for {leave_request.officer.full_name}'
    }
    return render(request, 'hrms/leave_approval_form.html', context)

# --- Officer Files Views ---

@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def officer_file_upload_view(request, service_number):
    """
    Allows uploading a new file for an officer.
    """
    officer = get_object_or_404(Officer, service_number=service_number)
    user = request.user

    if not can_manage_officer_data(user, officer.prison_station, officer.region):
        messages.error(request, "You do not have permission to upload files for this officer.")
        return redirect('hrms:officer_detail', service_number=officer.service_number)

    if request.method == 'POST':
        form = OfficerDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            officer_file = form.save(commit=False)
            officer_file.officer = officer
            officer_file.uploaded_by = user

            # Determine the specific user to whom the action is directed
            action_to_role = officer_file.action_to
            action_recipient_user = None

            if action_to_role:
                # Start with a base queryset for CustomUser
                recipient_qs = CustomUser.objects.all()

                # Filter by role
                recipient_qs = recipient_qs.filter(role=action_to_role)

                # Apply regional filtering if the role is regional
                if action_to_role in ['regional_commanding_officer', 'regional_headquarters_officer', 'regional_hr']:
                    if officer.region:
                        recipient_qs = recipient_qs.filter(region=officer.region)
                    else:
                        messages.warning(request, f"Cannot send notification to {action_to_role} as officer's region is not set.")
                        action_recipient_user = None # No specific recipient found
                # Apply station filtering if the role is station-level
                elif action_to_role in ['station_officer_in_charge', 'station_officer', 'station_hr']:
                    if officer.prison_station:
                        recipient_qs = recipient_qs.filter(prison_station=officer.prison_station)
                    else:
                        messages.warning(request, f"Cannot send notification to {action_to_role} as officer's prison station is not set.")
                        action_recipient_user = None # No specific recipient found

                # Try to get one recipient. If multiple, pick the first one, or handle as needed.
                action_recipient_user = recipient_qs.first()

            officer_file.action_to_user = action_recipient_user # Assign the determined user object
            officer_file.save()
            messages.success(request, "File uploaded successfully.")

            # Notify the officer who the document is about
            if officer.user:
                create_notification(
                    recipient=officer.user,
                    sender=user,
                    message=f"A new document '{officer_file.file_name}' has been uploaded to your file.",
                    notification_type='file_action',
                    content_object=officer_file
                )

            # Notify the specific user/role for whom action is required
            if officer_file.action_to_user and officer_file.action_to_user != user: # Ensure not notifying self if action_to_user is the uploader
                create_notification(
                    recipient=officer_file.action_to_user,
                    sender=user,
                    message=f"Action required: New document '{officer_file.file_name}' for {officer.full_name} needs your review.",
                    notification_type='file_action',
                    content_object=officer_file
                )
            elif officer_file.action_to_user is None and action_to_role and action_to_role != 'officer_self' and action_to_role != 'all':
                # This means a specific role was selected but no user was found for that role/location
                messages.warning(request, f"No specific user found for the selected 'Action Required By Role': {action_to_role}. Notification could not be sent to that role.")


            return redirect('hrms:officer_file_detail', pk=officer_file.pk)
        else:
            messages.error(request, "Error uploading file. Please correct the errors.")
    else:
        form = OfficerDocumentForm()

    context = {
        'form': form,
        'officer': officer,
        'title': f'Upload File for {officer.full_name}'
    }
    return render(request, 'hrms/officer_file_form.html', context)

@login_required
def officer_file_list_view(request):
    """
    Lists officer files relevant to the user's role.
    Can be filtered by officer service_number and status.
    """
    user = request.user
    officer_files = OfficerDocument.objects.all().select_related('officer', 'uploaded_by')

    if is_station_level(user) and user.prison_station:
        officer_files = officer_files.filter(officer__prison_station=user.prison_station)
    elif is_regional_level(user) and user.region:
        officer_files = officer_files.filter(officer__region=user.region)
    # National level/superuser sees all

    officer_service_number = request.GET.get('officer_service_number')
    officer_filter = None
    if officer_service_number:
        officer_filter = get_object_or_404(Officer, service_number=officer_service_number)
        officer_files = officer_files.filter(officer=officer_filter)

    search_query = request.GET.get('search', '')
    if search_query:
        officer_files = officer_files.filter(
            Q(file_name__icontains=search_query) |
            Q(officer__service_number__icontains=search_query) |
            Q(officer__first_name__icontains=search_query) |
            Q(officer__surname__icontains=search_query)
        )

    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        officer_files = officer_files.filter(status=status_filter)


    context = {
        'officer_files': officer_files.order_by('-uploaded_at'),
        'title': 'Officer Files',
        'current_status_filter': status_filter,
        'search_query': search_query,
        'officer_filter': officer_filter,
    }
    return render(request, 'hrms/officer_file_list.html', context)

@login_required
def officer_file_detail_view(request, pk):
    """
    Displays details of a single officer file.
    """
    officer_file = get_object_or_404(OfficerDocument.objects.select_related('officer', 'uploaded_by', 'reviewed_by'), pk=pk)
    user = request.user

    if not can_manage_officer_data(user, officer_file.officer.prison_station, officer_file.officer.region):
        messages.error(request, "You do not have permission to view this file.")
        return redirect('hrms:officer_file_list')

    context = {
        'officer_file': officer_file,
        'title': f'File: {officer_file.file_name}'
    }
    return render(request, 'hrms/officer_file_detail.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def officer_file_respond_view(request, pk):
    """
    Allows authorized users to respond to an officer file (approve/reject).
    """
    officer_file = get_object_or_404(OfficerDocument, pk=pk)
    user = request.user

    if not can_manage_officer_data(user, officer_file.officer.prison_station, officer_file.officer.region):
        messages.error(request, "You do not have permission to respond to this file.")
        return redirect('hrms:officer_file_detail', pk=pk)

    if officer_file.status != 'pending':
        messages.warning(request, "This file has already been responded to.")
        return redirect('hrms:officer_file_detail', pk=pk)

    if request.method == 'POST':
        form = OfficerFileResponseForm(request.POST, instance=officer_file)
        if form.is_valid():
            file_response = form.save(commit=False)
            file_response.reviewed_by = user
            file_response.reviewed_at = timezone.now()
            file_response.save()
            messages.success(request, "File response recorded successfully.")

            # Notify the user who uploaded the document about the response
            if officer_file.uploaded_by:
                create_notification(
                    recipient=officer_file.uploaded_by,
                    sender=user,
                    message=f"Your uploaded document '{officer_file.file_name}' for {officer_file.officer.full_name} has been {file_response.get_status_display().lower()}. Notes: {file_response.response_notes or 'N/A'}",
                    notification_type='file_action',
                    content_object=officer_file
                )
            # Notify the officer themselves if they have a user account
            if officer_file.officer.user and officer_file.officer.user != officer_file.uploaded_by:
                create_notification(
                    recipient=officer_file.officer.user,
                    sender=user,
                    message=f"Your document '{officer_file.file_name}' has been reviewed and {file_response.get_status_display().lower()}. Notes: {file_response.response_notes or 'N/A'}",
                    notification_type='file_action',
                    content_object=officer_file
                )


            return redirect('hrms:officer_file_detail', pk=pk)
        else:
            messages.error(request, "Error responding to file. Please correct the errors.")
    else:
        form = OfficerFileResponseForm(instance=officer_file)

    context = {
        'form': form,
        'officer_file': officer_file,
        'title': f'Respond to File: {officer_file.file_name}'
    }
    return render(request, 'hrms/officer_file_response_form.html', context)

# --- Performance Views ---

@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def performance_record_create_view(request, service_number):
    """
    Allows adding a new performance record for an officer.
    """
    officer = get_object_or_404(Officer, service_number=service_number)
    user = request.user

    if not can_manage_officer_data(user, officer.prison_station, officer.region):
        messages.error(request, "You do not have permission to add performance records for this officer.")
        return redirect('hrms:officer_detail', service_number=officer.service_number)

    if request.method == 'POST':
        form = OfficerPerformanceForm(request.POST)
        if form.is_valid():
            performance_record = form.save(commit=False)
            performance_record.officer = officer
            performance_record.recorded_by = user
            performance_record.save()
            messages.success(request, "Performance record added successfully.")
            return redirect('hrms:officer_detail', service_number=officer.service_number)
        else:
            messages.error(request, "Error adding performance record. Please correct the errors.")
    else:
        form = OfficerPerformanceForm()

    context = {
        'form': form,
        'officer': officer,
        'title': f'Add Performance Record for {officer.full_name}'
    }
    return render(request, 'hrms/performance_record_form.html', context)

@login_required
def performance_record_list_view(request):
    """
    Lists performance records relevant to the user's role.
    Can be filtered by officer service_number.
    """
    user = request.user
    performance_records = OfficerPerformance.objects.all().select_related('officer', 'metric', 'recorded_by')

    if is_station_level(user) and user.prison_station:
        performance_records = performance_records.filter(officer__prison_station=user.prison_station)
    elif is_regional_level(user) and user.region:
        performance_records = performance_records.filter(officer__region=user.region)
    # National level/superuser sees all

    officer_service_number = request.GET.get('officer_service_number')
    officer_filter = None
    if officer_service_number:
        officer_filter = get_object_or_404(Officer, service_number=officer_service_number)
        performance_records = performance_records.filter(officer=officer_filter)

    search_query = request.GET.get('search', '')
    if search_query:
        performance_records = performance_records.filter(
            Q(officer__service_number__icontains=search_query) |
            Q(officer__first_name__icontains=search_query) |
            Q(officer__surname__icontains=search_query) |
            Q(metric__name__icontains=search_query)
        )

    context = {
        'performance_records': performance_records.order_by('-date', 'officer__surname'),
        'title': 'Officer Performance Records',
        'search_query': search_query,
        'officer_filter': officer_filter,
    }
    return render(request, 'hrms/performance_record_list.html', context)

# --- Office Assignments Views ---

@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def office_assignment_create_view(request, service_number):
    """
    Allows assigning an officer to a new office.
    This updates the 'current_office_assignment' field on the Officer model.
    """
    officer = get_object_or_404(Officer, service_number=service_number)
    user = request.user

    if not can_manage_officer_data(user, officer.prison_station, officer.region):
        messages.error(request, "You do not have permission to assign offices for this officer.")
        return redirect('hrms:officer_detail', service_number=officer.service_number)

    if request.method == 'POST':
        form = OfficeAssignmentForm(request.POST, instance=officer)
        if form.is_valid():
            form.save()
            messages.success(request, f"Officer {officer.full_name} assigned to new office successfully.")
            return redirect('hrms:officer_detail', service_number=officer.service_number)
        else:
            messages.error(request, "Error assigning office. Please correct the errors.")
    else:
        form = OfficeAssignmentForm(instance=officer)

    context = {
        'form': form,
        'officer': officer,
        'title': f'Assign Office to {officer.full_name}'
    }
    return render(request, 'hrms/office_assignment_form.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def office_assignment_update_view(request, pk):
    """
    Allows updating an officer's current office assignment.
    """
    officer = get_object_or_404(Officer, pk=pk)
    user = request.user

    if not can_manage_officer_data(user, officer.prison_station, officer.region):
        messages.error(request, "You do not have permission to update this officer's assignment.")
        return redirect('hrms:officer_detail', service_number=officer.service_number)

    if request.method == 'POST':
        form = OfficeAssignmentForm(request.POST, instance=officer)
        if form.is_valid():
            form.save()
            messages.success(request, f"Officer {officer.full_name}'s office assignment updated successfully.")
            return redirect('hrms:officer_detail', service_number=officer.service_number)
        else:
            messages.error(request, "Error updating office assignment. Please correct the errors.")
    else:
        form = OfficeAssignmentForm(instance=officer)

    context = {
        'form': form,
        'officer': officer,
        'title': f'Update Office Assignment for {officer.full_name}'
    }
    return render(request, 'hrms/office_assignment_form.html', context)


# --- Region Management Views ---

@login_required
@user_passes_test(can_manage_regions)
def region_list_view(request):
    """
    Lists all regions. Only accessible by national-level users or superusers.
    """
    regions = Region.objects.all().order_by('name')
    search_query = request.GET.get('search', '')
    if search_query:
        regions = regions.filter(Q(name__icontains=search_query) | Q(description__icontains=search_query))

    context = {
        'regions': regions,
        'title': 'Manage Regions',
        'search_query': search_query,
    }
    return render(request, 'hrms/region_list.html', context)

@login_required
@user_passes_test(can_manage_regions)
def region_create_view(request):
    """
    Allows creating a new region. Only accessible by national-level users or superusers.
    """
    if request.method == 'POST':
        form = RegionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Region added successfully.")
            return redirect('hrms:region_list')
        else:
            messages.error(request, "Error adding region. Please correct the errors.")
    else:
        form = RegionForm()

    context = {
        'form': form,
        'title': 'Add New Region'
    }
    return render(request, 'hrms/region_form.html', context)

@login_required
@user_passes_test(can_manage_regions)
def region_update_view(request, pk):
    """
    Allows updating an existing region. Only accessible by national-level users or superusers.
    """
    region = get_object_or_404(Region, pk=pk)
    if request.method == 'POST':
        form = RegionForm(request.POST, instance=region)
        if form.is_valid():
            form.save()
            messages.success(request, f"Region '{region.name}' updated successfully.")
            return redirect('hrms:region_list')
        else:
            messages.error(request, "Error updating region. Please correct the errors.")
    else:
        form = RegionForm(instance=region)

    context = {
        'form': form,
        'title': f'Edit Region: {region.name}'
    }
    return render(request, 'hrms/region_form.html', context)

@login_required
@user_passes_test(can_manage_regions)
def region_delete_view(request, pk):
    """
    Allows deleting a region. Only accessible by national-level users or superusers.
    """
    region = get_object_or_404(Region, pk=pk)
    if request.method == 'POST':
        region_name = region.name
        region.delete()
        messages.success(request, f"Region '{region_name}' deleted successfully.")
        return redirect('hrms:region_list')

    context = {
        'region': region,
        'title': f'Delete Region: {region.name}'
    }
    return render(request, 'hrms/region_confirm_delete.html', context)

# --- Prison Station Management Views ---

@login_required
@user_passes_test(lambda u: can_manage_prison_stations(u))
def prison_station_list_view(request):
    """
    Lists all prison stations. National level sees all, regional level sees stations in their region.
    """
    user = request.user
    prison_stations = PrisonStation.objects.all().select_related('region').order_by('name')

    if is_regional_level(user) and user.region:
        print(f"DEBUG: prison_station_list_view - Regional user {user.username}. Filtering stations by region: {user.region.name}")
        prison_stations = prison_stations.filter(region=user.region)
    else:
        print(f"DEBUG: prison_station_list_view - Non-regional user {user.username} or no region assigned. Showing all/unfiltered stations.")


    search_query = request.GET.get('search', '')
    if search_query:
        prison_stations = prison_stations.filter(
            Q(name__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(region__name__icontains=search_query)
        )

    context = {
        'prison_stations': prison_stations,
        'title': 'Manage Prison Stations',
        'search_query': search_query,
    }
    return render(request, 'hrms/prison_station_list.html', context)

@login_required
@user_passes_test(lambda u: can_manage_prison_stations(u))
def prison_station_create_view(request):
    """
    Allows creating a new prison station. National level can create anywhere,
    regional level can create only in their region.
    """
    user = request.user
    if request.method == 'POST':
        form = PrisonStationForm(request.POST)
        if form.is_valid():
            prison_station = form.save(commit=False)
            if is_regional_level(user) and user.region:
                if prison_station.region and prison_station.region != user.region: # Check if prison_station.region is set before comparing
                    messages.error(request, "You can only add prison stations within your assigned region.")
                    return render(request, 'hrms/prison_station_form.html', {'form': form, 'title': 'Add New Prison Station'})
            prison_station.save()
            messages.success(request, "Prison Station added successfully.")
            return redirect('hrms:prison_station_list')
        else:
            messages.error(request, "Error adding prison station. Please correct the errors.")
    else:
        form = PrisonStationForm()
        if is_regional_level(user) and user.region:
            form.fields['region'].queryset = Region.objects.filter(pk=user.region.pk)
            form.fields['region'].initial = user.region
            form.fields['region'].widget.attrs['readonly'] = True

    context = {
        'form': form,
        'title': 'Add New Prison Station'
    }
    return render(request, 'hrms/prison_station_form.html', context)

@login_required
@user_passes_test(lambda u: can_manage_prison_stations(u))
def prison_station_update_view(request, pk):
    """
    Allows updating an existing prison station. National level can update anywhere,
    regional level can update only in their region.
    """
    prison_station = get_object_or_404(PrisonStation, pk=pk)
    user = request.user

    if not can_manage_prison_stations(user, prison_station.region):
        messages.error(request, "You do not have permission to edit this prison station.")
        return redirect('hrms:prison_station_list')

    if request.method == 'POST':
        form = PrisonStationForm(request.POST, instance=prison_station)
        if form.is_valid():
            updated_station = form.save(commit=False)
            if is_regional_level(user) and user.region:
                if updated_station.region and updated_station.region != user.region: # Check if updated_station.region is set before comparing
                    messages.error(request, "You can only update prison stations within your assigned region.")
                    return render(request, 'hrms/prison_station_form.html', {'form': form, 'title': f'Edit Prison Station: {prison_station.name}'})
            updated_station.save()
            messages.success(request, f"Prison Station '{prison_station.name}' updated successfully.")
            return redirect('hrms:prison_station_list')
        else:
            messages.error(request, "Error updating prison station. Please correct the errors.")
    else:
        form = PrisonStationForm(instance=prison_station)
        if is_regional_level(user) and user.region:
            form.fields['region'].queryset = Region.objects.filter(pk=user.region.pk)
            form.fields['region'].initial = user.region
            form.fields['region'].widget.attrs['readonly'] = True

    context = {
        'form': form,
        'title': f'Edit Prison Station: {prison_station.name}'
    }
    return render(request, 'hrms/prison_station_form.html', context)

@login_required
@user_passes_test(lambda u: can_manage_prison_stations(u))
def prison_station_delete_view(request, pk):
    """
    Allows deleting a prison station. National level can delete anywhere,
    regional level can delete only in their region.
    """
    prison_station = get_object_or_404(PrisonStation, pk=pk)
    user = request.user

    if not can_manage_prison_stations(user, prison_station.region):
        messages.error(request, "You do not have permission to delete this prison station.")
        return redirect('hrms:prison_station_list')

    if request.method == 'POST':
        station_name = prison_station.name
        prison_station.delete()
        messages.success(request, f"Prison Station '{station_name}' deleted successfully.")
        return redirect('hrms:prison_station_list')

    context = {
        'prison_station': prison_station,
        'title': f'Delete Prison Station: {prison_station.name}'
    }
    return render(request, 'hrms/prison_station_confirm_delete.html', context)

# --- Attendance Views ---

@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def attendance_record_create_view(request, service_number):
    """
    Allows adding a new attendance record for an officer.
    """
    officer = get_object_or_404(Officer, service_number=service_number)
    user = request.user

    if not can_manage_officer_data(user, officer.prison_station, officer.region):
        messages.error(request, "You do not have permission to add attendance records for this officer.")
        return redirect('hrms:officer_detail', service_number=officer.service_number)

    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            attendance_record = form.save(commit=False)
            attendance_record.officer = officer
            attendance_record.recorded_by = user
            attendance_record.save()
            messages.success(request, "Attendance record added successfully.")
            return redirect('hrms:officer_detail', service_number=officer.service_number)
        else:
            messages.error(request, "Error adding attendance record. Please correct the errors.")
    else:
        form = AttendanceForm()

    context = {
        'form': form,
        'officer': officer,
        'title': f'Add Attendance Record for {officer.full_name}'
    }
    return render(request, 'hrms/attendance_form.html', context)

@login_required
def attendance_record_list_view(request):
    """
    Lists attendance records relevant to the user's role.
    """
    user = request.user
    attendance_records = Attendance.objects.all().select_related('officer', 'recorded_by')

    if is_station_level(user) and user.prison_station:
        attendance_records = attendance_records.filter(officer__prison_station=user.prison_station)
    elif is_regional_level(user) and user.region:
        attendance_records = attendance_records.filter(officer__region=user.region)
    # National level/superuser sees all

    search_query = request.GET.get('search', '')
    if search_query:
        attendance_records = attendance_records.filter(
            Q(officer__service_number__icontains=search_query) |
            Q(officer__first_name__icontains=search_query) |
            Q(officer__surname__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        attendance_records = attendance_records.filter(status=status_filter)

    officer_service_number = request.GET.get('officer_service_number')
    officer_filter = None
    if officer_service_number:
        officer_filter = get_object_or_404(Officer, service_number=officer_service_number)
        attendance_records = attendance_records.filter(officer=officer_filter)


    context = {
        'attendance_records': attendance_records.order_by('-date', 'officer__surname'),
        'title': 'Officer Attendance Records',
        'search_query': search_query,
        'current_status_filter': status_filter,
        'officer_filter': officer_filter,
    }
    return render(request, 'hrms/attendance_list.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def attendance_record_update_view(request, pk):
    """
    Allows updating an existing attendance record.
    """
    attendance_record = get_object_or_404(Attendance, pk=pk)
    user = request.user

    if not can_manage_officer_data(user, attendance_record.officer.prison_station, attendance_record.officer.region):
        messages.error(request, "You do not have permission to edit this attendance record.")
        return redirect('hrms:attendance_record_list')

    if request.method == 'POST':
        form = AttendanceForm(request.POST, instance=attendance_record)
        if form.is_valid():
            form.save()
            messages.success(request, "Attendance record updated successfully.")
            return redirect('hrms:officer_detail', service_number=attendance_record.officer.service_number)
        else:
            messages.error(request, "Error updating attendance record. Please correct the errors.")
    else:
        form = AttendanceForm(instance=attendance_record)

    context = {
        'form': form,
        'officer': attendance_record.officer,
        'title': f'Edit Attendance for {attendance_record.officer.full_name}'
    }
    return render(request, 'hrms/attendance_form.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u))
def attendance_record_delete_view(request, pk):
    """
    Deletes an attendance record. Restricted to national/regional/superuser.
    """
    attendance_record = get_object_or_404(Attendance, pk=pk)
    user = request.user

    if not can_manage_officer_data(user, attendance_record.officer.prison_station, attendance_record.officer.region):
        messages.error(request, "You do not have permission to delete this attendance record.")
        return redirect('hrms:attendance_record_list')

    if request.method == 'POST':
        officer_name = attendance_record.officer.full_name
        attendance_record.delete()
        messages.success(request, f"Attendance record for {officer_name} on {attendance_record.date} deleted successfully.")
        return redirect('hrms:attendance_record_list')

    context = {
        'attendance_record': attendance_record,
        'title': f'Delete Attendance for {attendance_record.officer.full_name}'
    }
    return render(request, 'hrms/attendance_confirm_delete.html', context)


# --- Disciplinary Cases Views ---

@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def disciplinary_case_create_view(request, service_number):
    """
    Allows adding a new disciplinary case for an officer.
    """
    officer = get_object_or_404(Officer, service_number=service_number)
    user = request.user

    if not can_manage_officer_data(user, officer.prison_station, officer.region):
        messages.error(request, "You do not have permission to add disciplinary cases for this officer.")
        return redirect('hrms:officer_detail', service_number=officer.service_number)

    if request.method == 'POST':
        form = DisciplinaryCaseForm(request.POST)
        if form.is_valid():
            disciplinary_case = form.save(commit=False)
            disciplinary_case.officer = officer
            disciplinary_case.recorded_by = user
            disciplinary_case.save()
            messages.success(request, "Disciplinary case added successfully.")

            if officer.user:
                create_notification(
                    recipient=officer.user,
                    sender=user,
                    message=f"A new disciplinary case has been recorded against you for '{disciplinary_case.offense}' on {disciplinary_case.case_date.strftime('%Y-%m-%d')}.",
                    notification_type='disciplinary_action',
                    content_object=disciplinary_case
                )
            hr_users = CustomUser.objects.filter(
                Q(is_superuser=True) |
                Q(role='national_commissioner') |
                Q(role='national_hr') |
                Q(role='regional_commanding_officer', region=officer.region) |
                Q(role='regional_headquarters_officer', region=officer.region) |
                Q(role='regional_hr', region=officer.region)
            ).distinct()
            for hr_user in hr_users:
                if hr_user != user:
                    create_notification(
                        recipient=hr_user,
                        sender=user,
                        message=f"New disciplinary case for {officer.full_name}: '{disciplinary_case.offense}'.",
                        notification_type='disciplinary_action',
                        content_object=disciplinary_case
                    )


            return redirect('hrms:officer_detail', service_number=officer.service_number)
        else:
            messages.error(request, "Error adding disciplinary case. Please correct the errors.")
    else:
        form = DisciplinaryCaseForm()

    context = {
        'form': form,
        'officer': officer,
        'title': f'Add Disciplinary Case for {officer.full_name}'
    }
    return render(request, 'hrms/disciplinary_case_form.html', context)

@login_required
def disciplinary_case_list_view(request):
    """
    Lists disciplinary cases relevant to the user's role.
    Can be filtered by officer service_number.
    """
    user = request.user
    disciplinary_cases = DisciplinaryCase.objects.all().select_related('officer', 'recorded_by')

    if is_station_level(user) and user.prison_station:
        disciplinary_cases = disciplinary_cases.filter(officer__prison_station=user.prison_station)
    elif is_regional_level(user) and user.region:
        disciplinary_cases = disciplinary_cases.filter(officer__region=user.region)
    # National level/superuser sees all

    officer_service_number = request.GET.get('officer_service_number')
    officer_filter = None
    if officer_service_number:
        officer_filter = get_object_or_404(Officer, service_number=officer_service_number)
        disciplinary_cases = disciplinary_cases.filter(officer=officer_filter)

    search_query = request.GET.get('search', '')
    if search_query:
        disciplinary_cases = disciplinary_cases.filter(
            Q(offense__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(officer__service_number__icontains=search_query) |
            Q(officer__first_name__icontains=search_query) |
            Q(officer__surname__icontains=search_query)
        )

    action_taken_filter = request.GET.get('action_taken')
    if action_taken_filter and action_taken_filter != 'all':
        disciplinary_cases = disciplinary_cases.filter(action_taken=action_taken_filter)


    context = {
        'disciplinary_cases': disciplinary_cases.order_by('-case_date', 'officer__surname'),
        'title': 'Officer Disciplinary Cases',
        'search_query': search_query,
        'action_taken_filter': action_taken_filter,
        'officer_filter': officer_filter,
    }
    return render(request, 'hrms/disciplinary_case_list.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def disciplinary_case_update_view(request, pk):
    """
    Allows updating an existing disciplinary case.
    """
    disciplinary_case = get_object_or_404(DisciplinaryCase, pk=pk)
    user = request.user

    if not can_manage_officer_data(user, disciplinary_case.officer.prison_station, disciplinary_case.officer.region):
        messages.error(request, "You do not have permission to edit this disciplinary case.")
        return redirect('hrms:disciplinary_case_list')

    if request.method == 'POST':
        form = DisciplinaryCaseForm(request.POST, instance=disciplinary_case)
        if form.is_valid():
            form.save()
            messages.success(request, "Disciplinary case updated successfully.")
            return redirect('hrms:officer_detail', service_number=disciplinary_case.officer.service_number)
        else:
            messages.error(request, "Error updating disciplinary case. Please correct the errors.")
    else:
        form = DisciplinaryCaseForm(instance=disciplinary_case)

    context = {
        'form': form,
        'officer': disciplinary_case.officer,
        'title': f'Edit Disciplinary Case for {disciplinary_case.officer.full_name}'
    }
    return render(request, 'hrms/disciplinary_case_form.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u))
def disciplinary_case_delete_view(request, pk):
    """
    Deletes a disciplinary case record. Restricted to national/regional/superuser.
    """
    disciplinary_case = get_object_or_404(DisciplinaryCase, pk=pk)
    user = request.user

    if not can_manage_officer_data(user, disciplinary_case.officer.prison_station, disciplinary_case.officer.region):
        messages.error(request, "You do not have permission to delete this disciplinary case.")
        return redirect('hrms:disciplinary_case_list')

    if request.method == 'POST':
        officer_name = disciplinary_case.officer.full_name
        case_date = disciplinary_case.case_date
        disciplinary_case.delete()
        messages.success(request, f"Disciplinary case for {officer_name} on {case_date} deleted successfully.")
        return redirect('hrms:disciplinary_case_list')

    context = {
        'disciplinary_case': disciplinary_case,
        'title': f'Delete Disciplinary Case for {disciplinary_case.officer.full_name}'
    }
    return render(request, 'hrms/disciplinary_case_confirm_delete.html', context)


# Initial data setup views (for superuser only)
@login_required
def setup_initial_data(request):
    """
    A view to populate initial Ranks, OfficeAssignments, and LeaveTypes.
    Accessible only to superusers.
    """
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('hrms:dashboard')

    if request.method == 'POST':
        # Populate Ranks
        ranks_to_create = [
            {'name': 'watchman', 'leave_days_annual': 21},
            {'name': 'messenger', 'leave_days_annual': 21},
            {'name': 'warder', 'leave_days_annual': 24},
            {'name': 'sergeant', 'leave_days_annual': 24},
            {'name': 'gaoler', 'leave_days_annual': 24},
            {'name': 'inspector', 'leave_days_annual': 24},
            {'name': 'assistant_superintendent', 'leave_days_annual': 30},
            {'name': 'superintendent', 'leave_days_annual': 30},
            {'name': 'senior_superintendent', 'leave_days_annual': 30},
            {'name': 'assistant_commissioner', 'leave_days_annual': 36},
            {'name': 'deputy_commissioner', 'leave_days_annual': 36},
            {'name': 'commissioner', 'leave_days_annual': 36},
            {'name': 'commissioner_general', 'leave_days_annual': 36},
        ]
        for rank_data in ranks_to_create:
            Rank.objects.get_or_create(name=rank_data['name'], defaults=rank_data)
        messages.info(request, "Ranks populated.")

        # Populate Office Assignments
        office_assignments_to_create = [
            {'name': 'general_duties'}, {'name': 'hospital'}, {'name': 'female_in_charge'},
            {'name': 'administration'}, {'name': 'accounts_office'}, {'name': 'research_office'},
            {'name': 'gender'}, {'name': 'rehabilitation'}, {'name': 'public_relations_office'},
            {'name': 'chaplaincy'}, {'name': 'secretary'}, {'name': 'protocol'},
            {'name': 'restorative_justice'}, {'name': 'radio_communication'}, {'name': 'registry'},
            {'name': 'ict'}, {'name': 'education'}, {'name': 'driver'},
        ]
        for office_data in office_assignments_to_create:
            OfficeAssignment.objects.get_or_create(name=office_data['name'], defaults=office_data)
        messages.info(request, "Office Assignments populated.")

        # Populate Leave Types
        leave_types_to_create = [
            {'name': 'Annual Leave', 'is_maternity': False, 'is_study': False, 'default_days': None},
            {'name': 'Maternity Leave', 'is_maternity': True, 'is_study': False, 'default_days': 90},
            {'name': 'Study Leave', 'is_maternity': False, 'is_study': True, 'default_days': None},
            {'name': 'Sick Leave', 'is_maternity': False, 'is_study': False, 'default_days': None},
            {'name': 'Compassionate Leave', 'is_maternity': False, 'is_study': False, 'default_days': None},
        ]
        for leave_type_data in leave_types_to_create:
            LeaveType.objects.get_or_create(name=leave_type_data['name'], defaults=leave_type_data)
        messages.info(request, "Leave Types populated.")

        # Populate Performance Metrics
        performance_metrics_to_create = [
            {'name': 'Punctuality', 'description': 'Adherence to schedules and deadlines.'},
            {'name': 'Teamwork', 'description': 'Ability to collaborate effectively with colleagues.'},
            {'name': 'Communication Skills', 'description': 'Clarity and effectiveness in conveying information.'},
            {'name': 'Report Writing Skills', 'description': 'Accuracy, clarity, and conciseness in written reports.'},
            {'name': 'Problem Identification', 'description': 'Ability to accurately identify and define problems.'},
            {'name': 'Solution Generation', 'description': 'Capacity to develop creative and effective solutions.'},
            {'name': 'Decision Making', 'description': 'Skill in making sound and timely decisions based on available information.'},
            {'name': 'Implementation Effectiveness', 'description': 'Proficiency in putting solutions into practice and evaluating their success.'},
        ]
        for metric_data in performance_metrics_to_create:
            PerformanceMetric.objects.get_or_create(name=metric_data['name'], defaults=metric_data)
        messages.info(request, "Performance Metrics populated.")

        messages.success(request, "Initial data setup complete!")
        return redirect('hrms:dashboard')

    return render(request, 'hrms/setup_initial_data.html')


@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u))
def annual_leave_reset_view(request):
    """
    A view to manually trigger the annual leave reset for all officers.
    This should typically be a scheduled task, but a manual trigger is useful for testing/admin.
    """
    if request.method == 'POST':
        current_year = date.today().year
        reset_count = 0

        officers = Officer.objects.filter(status='active')

        for officer in officers:
            entitled_days = officer.rank.leave_days_annual if officer.rank else 0

            annual_balance, created = AnnualLeaveBalance.objects.get_or_create(
                officer=officer,
                year=current_year,
                defaults={
                    'total_days_entitled': entitled_days,
                    'days_taken': 0,
                    'last_reset_date': date.today()
                }
            )

            if not created:
                if annual_balance.last_reset_date != date.today():
                    annual_balance.total_days_entitled = entitled_days
                    annual_balance.days_taken = 0
                    annual_balance.last_reset_date = date.today()
                    annual_balance.save()
                    reset_count += 1
                else:
                    messages.info(request, f"Leave for {officer.full_name} already reset today.")
            else:
                reset_count += 1

        messages.success(request, f"Annual leave reset process completed. {reset_count} officer(s) had their leave balance reset/created for {current_year}.")
        return redirect('hrms:dashboard')

    context = {
        'title': 'Annual Leave Reset',
        'current_year': date.today().year,
        'next_reset_date_info': 'This action will reset annual leave balances for all active officers for the current year. It should typically be run once at the start of your leave year (e.g., April 1st).',
    }
    return render(request, 'hrms/annual_leave_reset_confirm.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def attendance_report_view(request):
    """
    Generates an attendance report with filtering options.
    Users can filter by year, month, region, and prison station.
    """
    user = request.user

    selected_year = request.GET.get('year', str(date.today().year))
    selected_month = request.GET.get('month', '')
    selected_region_id = request.GET.get('region', '')
    selected_station_id = request.GET.get('station', '')

    attendance_records = Attendance.objects.all().select_related('officer__region', 'officer__prison_station')

    if is_station_level(user) and user.prison_station:
        attendance_records = attendance_records.filter(officer__prison_station=user.prison_station)
    elif is_regional_level(user) and user.region:
        attendance_records = attendance_records.filter(officer__region=user.region)

    if selected_year:
        attendance_records = attendance_records.filter(date__year=selected_year)
    if selected_month:
        attendance_records = attendance_records.filter(date__month=selected_month)
    if selected_region_id:
        attendance_records = attendance_records.filter(officer__region_id=selected_region_id)
    if selected_station_id:
        attendance_records = attendance_records.filter(officer__prison_station_id=selected_station_id)

    attendance_summary = attendance_records.values('status').annotate(count=Count('status'))
    summary_dict = {item['status']: item['count'] for item in attendance_summary}

    available_years = Attendance.objects.annotate(year=ExtractYear('date')).values_list('year', flat=True).distinct().order_by('-year')
    if not available_years:
        available_years = [date.today().year]

    regions = Region.objects.all().order_by('name')
    stations = PrisonStation.objects.all().order_by('name')

    if is_regional_level(user) and user.region:
        regions = regions.filter(pk=user.region.pk)
        stations = stations.filter(region=user.region)
    elif is_station_level(user) and user.prison_station:
        regions = regions.filter(pk=user.prison_station.region.pk)
        stations = stations.filter(pk=user.prison_station.pk)

    context = {
        'title': 'Attendance Report',
        'summary_data': summary_dict,
        'total_records': attendance_records.count(),
        'available_years': available_years,
        'months': [
            {'value': 1, 'name': 'January'}, {'value': 2, 'name': 'February'},
            {'value': 3, 'name': 'March'}, {'value': 4, 'name': 'April'},
            {'value': 5, 'name': 'May'}, {'value': 6, 'name': 'June'},
            {'value': 7, 'name': 'July'}, {'value': 8, 'name': 'August'},
            {'value': 9, 'name': 'September'}, {'value': 10, 'name': 'October'},
            {'value': 11, 'name': 'November'}, {'value': 12, 'name': 'December'},
        ],
        'regions': regions,
        'stations': stations,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'selected_region_id': selected_region_id,
        'selected_station_id': selected_station_id,
    }
    return render(request, 'hrms/attendance_report.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def performance_report_view(request):
    """
    Generates a performance report with filtering options.
    Users can filter by year, month, specific metric, region, and prison station.
    """
    user = request.user

    selected_year = request.GET.get('year', str(date.today().year))
    selected_month = request.GET.get('month', '')
    selected_metric_id = request.GET.get('metric', '')
    selected_region_id = request.GET.get('region', '')
    selected_station_id = request.GET.get('station', '')

    performance_records = OfficerPerformance.objects.all().select_related('officer__region', 'officer__prison_station', 'metric')

    if is_station_level(user) and user.prison_station:
        performance_records = performance_records.filter(officer__prison_station=user.prison_station)
    elif is_regional_level(user) and user.region:
        performance_records = performance_records.filter(officer__region=user.region)

    if selected_year:
        performance_records = performance_records.filter(date__year=selected_year)
    if selected_month:
        performance_records = performance_records.filter(date__month=selected_month)
    if selected_metric_id:
        performance_records = performance_records.filter(metric_id=selected_metric_id)
    if selected_region_id:
        performance_records = performance_records.filter(officer__region_id=selected_region_id)
    if selected_station_id:
        performance_records = performance_records.filter(officer__prison_station_id=selected_station_id)

    overall_average_score = performance_records.aggregate(Avg('score'))['score__avg']

    average_scores_by_metric = []
    if not selected_metric_id:
        average_scores_by_metric = performance_records.values('metric__name').annotate(avg_score=Avg('score')).order_by('metric__name')

    officer_performance_summary = performance_records.values(
        'officer__service_number',
        'officer__first_name',
        'officer__surname'
    ).annotate(
        avg_score=Avg('score'),
        record_count=Count('pk')
    ).order_by('-avg_score')

    available_years = OfficerPerformance.objects.annotate(year=ExtractYear('date')).values_list('year', flat=True).distinct().order_by('-year')
    if not available_years:
        available_years = [date.today().year]

    all_metrics = PerformanceMetric.objects.all().order_by('name')

    regions = Region.objects.all().order_by('name')
    stations = PrisonStation.objects.all().order_by('name')

    if is_regional_level(user) and user.region:
        regions = regions.filter(pk=user.region.pk)
        stations = stations.filter(region=user.region)
    elif is_station_level(user) and user.prison_station:
        regions = regions.filter(pk=user.prison_station.region.pk)
        stations = stations.filter(pk=user.prison_station.pk)

    context = {
        'title': 'Performance Report',
        'overall_average_score': round(overall_average_score, 2) if overall_average_score else 'N/A',
        'average_scores_by_metric': average_scores_by_metric,
        'officer_performance_summary': officer_performance_summary,
        'total_records': performance_records.count(),
        'available_years': available_years,
        'months': [
            {'value': 1, 'name': 'January'}, {'value': 2, 'name': 'February'},
            {'value': 3, 'name': 'March'}, {'value': 4, 'name': 'April'},
            {'value': 5, 'name': 'May'}, {'value': 6, 'name': 'June'},
            {'value': 7, 'name': 'July'}, {'value': 8, 'name': 'August'},
            {'value': 9, 'name': 'September'}, {'value': 10, 'name': 'October'},
            {'value': 11, 'name': 'November'}, {'value': 12, 'name': 'December'},
        ],
        'all_metrics': all_metrics,
        'regions': regions,
        'stations': stations,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'selected_metric_id': selected_metric_id,
        'selected_region_id': selected_region_id,
        'selected_station_id': selected_station_id,
    }
    return render(request, 'hrms/performance_report.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def disciplinary_report_view(request):
    """
    Generates a disciplinary cases report with filtering options.
    Users can filter by year, month, action taken, region, and prison station.
    """
    user = request.user

    selected_year = request.GET.get('year', str(date.today().year))
    selected_month = request.GET.get('month', '')
    selected_action_taken = request.GET.get('action_taken', '')
    selected_region_id = request.GET.get('region', '')
    selected_station_id = request.GET.get('station', '')

    disciplinary_cases = DisciplinaryCase.objects.all().select_related('officer__region', 'officer__prison_station')

    if is_station_level(user) and user.prison_station:
        disciplinary_cases = disciplinary_cases.filter(officer__prison_station=user.prison_station)
    elif is_regional_level(user) and user.region:
        disciplinary_cases = disciplinary_cases.filter(officer__region=user.region)

    if selected_year:
        disciplinary_cases = disciplinary_cases.filter(case_date__year=selected_year)
    if selected_month:
        disciplinary_cases = disciplinary_cases.filter(case_date__month=selected_month)
    if selected_action_taken:
        disciplinary_cases = disciplinary_cases.filter(action_taken=selected_action_taken)
    if selected_region_id:
        disciplinary_cases = disciplinary_cases.filter(officer__region_id=selected_region_id)
    if selected_station_id:
        disciplinary_cases = disciplinary_cases.filter(officer__prison_station_id=selected_station_id)

    total_cases = disciplinary_cases.count()

    cases_by_offense = disciplinary_cases.values('offense').annotate(count=Count('offense')).order_by('-count')

    cases_by_action = disciplinary_cases.values('action_taken').annotate(count=Count('action_taken')).order_by('-count')

    available_years = DisciplinaryCase.objects.annotate(year=ExtractYear('case_date')).values_list('year', flat=True).distinct().order_by('-year')
    if not available_years:
        available_years = [date.today().year]

    action_taken_choices = DisciplinaryCase.ACTION_TAKEN_CHOICES

    regions = Region.objects.all().order_by('name')
    stations = PrisonStation.objects.all().order_by('name')

    if is_regional_level(user) and user.region:
        regions = regions.filter(pk=user.region.pk)
        stations = stations.filter(region=user.region)
    elif is_station_level(user) and user.prison_station:
        regions = regions.filter(pk=user.prison_station.region.pk)
        stations = stations.filter(pk=user.prison_station.pk)

    context = {
        'title': 'Disciplinary Cases Report',
        'total_cases': total_cases,
        'cases_by_offense': cases_by_offense,
        'cases_by_action': cases_by_action,
        'available_years': available_years,
        'months': [
            {'value': 1, 'name': 'January'}, {'value': 2, 'name': 'February'},
            {'value': 3, 'name': 'March'}, {'value': 4, 'name': 'April'},
            {'value': 5, 'name': 'May'}, {'value': 6, 'name': 'June'},
            {'value': 7, 'name': 'July'}, {'value': 8, 'name': 'August'},
            {'value': 9, 'name': 'September'}, {'value': 10, 'name': 'October'},
            {'value': 11, 'name': 'November'}, {'value': 12, 'name': 'December'},
        ],
        'action_taken_choices': action_taken_choices,
        'regions': regions,
        'stations': stations,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'selected_action_taken': selected_action_taken,
        'selected_region_id': selected_region_id,
        'selected_station_id': selected_station_id,
    }
    return render(request, 'hrms/disciplinary_report.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def leave_report_view(request):
    """
    Generates a leave report with filtering options.
    Users can filter by year, month, leave type, status, region, and prison station.
    """
    user = request.user

    selected_year = request.GET.get('year', str(date.today().year))
    selected_month = request.GET.get('month', '')
    selected_leave_type_id = request.GET.get('leave_type', '')
    selected_status = request.GET.get('status', '')
    selected_region_id = request.GET.get('region', '')
    selected_station_id = request.GET.get('station', '')

    leave_requests = LeaveRequest.objects.all().select_related('officer__region', 'officer__prison_station', 'leave_type')

    if is_station_level(user) and user.prison_station:
        leave_requests = leave_requests.filter(officer__prison_station=user.prison_station)
    elif is_regional_level(user) and user.region:
        leave_requests = leave_requests.filter(officer__region=user.region)

    if selected_year:
        leave_requests = leave_requests.filter(start_date__year=selected_year)
    if selected_month:
        leave_requests = leave_requests.filter(start_date__month=selected_month)
    if selected_leave_type_id:
        leave_requests = leave_requests.filter(leave_type_id=selected_leave_type_id)
    if selected_status:
        leave_requests = leave_requests.filter(status=selected_status)
    if selected_region_id:
        leave_requests = leave_requests.filter(officer__region_id=selected_region_id)
    if selected_station_id:
        leave_requests = leave_requests.filter(officer__prison_station_id=selected_station_id)

    total_leave_requests = leave_requests.count()
    total_days_requested = leave_requests.aggregate(Sum('number_of_days'))['number_of_days__sum'] or 0

    requests_by_status = leave_requests.values('status').annotate(count=Count('status')).order_by('status')

    requests_by_type = leave_requests.values('leave_type__name').annotate(count=Count('leave_type__name'), total_days=Sum('number_of_days')).order_by('leave_type__name')

    available_years = LeaveRequest.objects.annotate(year=ExtractYear('start_date')).values_list('year', flat=True).distinct().order_by('-year')
    if not available_years:
        available_years = [date.today().year]

    all_leave_types = LeaveType.objects.all().order_by('name')

    leave_status_choices = LeaveRequest.STATUS_CHOICES

    regions = Region.objects.all().order_by('name')
    stations = PrisonStation.objects.all().order_by('name')

    if is_regional_level(user) and user.region:
        regions = regions.filter(pk=user.region.pk)
        stations = stations.filter(region=user.region)
    elif is_station_level(user) and user.prison_station:
        regions = regions.filter(pk=user.prison_station.region.pk)
        stations = stations.filter(pk=user.prison_station.pk)

    context = {
        'title': 'Leave Report',
        'total_leave_requests': total_leave_requests,
        'total_days_requested': total_days_requested,
        'requests_by_status': requests_by_status,
        'requests_by_type': requests_by_type,
        'available_years': available_years,
        'months': [
            {'value': 1, 'name': 'January'}, {'value': 2, 'name': 'February'},
            {'value': 3, 'name': 'March'}, {'value': 4, 'name': 'April'},
            {'value': 5, 'name': 'May'}, {'value': 6, 'name': 'June'},
            {'value': 7, 'name': 'July'}, {'value': 8, 'name': 'August'},
            {'value': 9, 'name': 'September'}, {'value': 10, 'name': 'October'},
            {'value': 11, 'name': 'November'}, {'value': 12, 'name': 'December'},
        ],
        'all_leave_types': all_leave_types,
        'leave_status_choices': leave_status_choices,
        'regions': regions,
        'stations': stations,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'selected_leave_type_id': selected_leave_type_id,
        'selected_status': selected_status,
        'selected_region_id': selected_region_id,
        'selected_station_id': selected_station_id,
    }
    return render(request, 'hrms/leave_report.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def demographics_report_view(request):
    """
    Generates a demographics report with filtering options.
    Users can filter by region and prison station.
    The report provides breakdowns by gender, marital status, and rank.
    """
    user = request.user

    selected_region_id = request.GET.get('region', '')
    selected_station_id = request.GET.get('station', '')
    selected_status = request.GET.get('status', '')

    officers = Officer.objects.all().select_related('region', 'prison_station', 'rank')

    if is_station_level(user) and user.prison_station:
        officers = officers.filter(prison_station=user.prison_station)
    elif is_regional_level(user) and user.region:
        officers = officers.filter(region=user.region)

    if selected_region_id:
        officers = officers.filter(region_id=selected_region_id)
    if selected_station_id:
        officers = officers.filter(prison_station_id=selected_station_id)
    if selected_status:
        officers = officers.filter(status=selected_status)

    total_officers = officers.count()

    gender_breakdown = officers.values('gender').annotate(count=Count('gender')).order_by('gender')
    gender_display_map = dict(Officer.GENDER_CHOICES)
    gender_breakdown_display = [{'gender': gender_display_map.get(item['gender'], item['gender']), 'count': item['count']} for item in gender_breakdown]


    marital_status_breakdown = officers.values('marital_status').annotate(count=Count('marital_status')).order_by('marital_status')
    marital_status_display_map = dict(Officer.MARITAL_STATUS_CHOICES)
    marital_status_breakdown_display = [{'marital_status': marital_status_display_map.get(item['marital_status'], item['marital_status']), 'count': item['count']} for item in marital_status_breakdown]


    rank_breakdown = officers.values('rank__name').annotate(count=Count('rank__name')).order_by('rank__name')
    rank_display_map = dict(Rank.RANK_CHOICES)
    rank_breakdown_display = [{'rank': rank_display_map.get(item['rank__name'], item['rank__name']), 'count': item['count']} for item in rank_breakdown]


    age_groups = {
        'Under 30': 0,
        '30-39': 0,
        '40-49': 0,
        '50-59': 0,
        '60+': 0,
    }
    today = date.today()
    for officer in officers:
        if officer.date_of_birth:
            age = today.year - officer.date_of_birth.year - ((today.month, today.day) < (officer.date_of_birth.month, officer.date_of_birth.day))
            if age < 30:
                age_groups['Under 30'] += 1
            elif 30 <= age <= 39:
                age_groups['30-39'] += 1
            elif 40 <= age <= 49:
                age_groups['40-49'] += 1
            elif 50 <= age <= 59:
                age_groups['50-59'] += 1
            else:
                age_groups['60+'] += 1
    age_group_breakdown = [{'age_group': k, 'count': v} for k, v in age_groups.items()]


    regions = Region.objects.all().order_by('name')
    stations = PrisonStation.objects.all().order_by('name')

    if is_regional_level(user) and user.region:
        regions = regions.filter(pk=user.region.pk)
        stations = stations.filter(region=user.region)
    elif is_station_level(user) and user.prison_station:
        regions = regions.filter(pk=user.prison_station.region.pk)
        stations = stations.filter(pk=user.prison_station.pk)

    context = {
        'title': 'Demographics Report',
        'total_officers': total_officers,
        'gender_breakdown': gender_breakdown_display,
        'marital_status_breakdown': marital_status_breakdown_display,
        'rank_breakdown': rank_breakdown_display,
        'age_group_breakdown': age_group_breakdown,
        'officer_status_choices': Officer.STATUS_CHOICES,
        'regions': regions,
        'stations': stations,
        'selected_region_id': selected_region_id,
        'selected_station_id': selected_station_id,
        'selected_status': selected_status,
    }
    return render(request, 'hrms/demographics_report.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def service_history_report_view(request):
    """
    Generates a service history report (promotions and transfers) with filtering options.
    Users can filter by year, month, type (promotion/transfer), rank, region, and prison station.
    """
    user = request.user

    selected_year = request.GET.get('year', str(date.today().year))
    selected_month = request.GET.get('month', '')
    selected_history_type = request.GET.get('history_type', '')
    selected_rank_id = request.GET.get('rank', '')
    selected_region_id = request.GET.get('region', '')
    selected_station_id = request.GET.get('station', '')

    promotions_queryset = PromotionHistory.objects.all().select_related('officer__region', 'officer__prison_station', 'previous_rank', 'new_rank')
    transfers_queryset = TransferHistory.objects.all().select_related('officer__region', 'officer__prison_station', 'previous_station', 'new_station')

    if is_station_level(user) and user.prison_station:
        promotions_queryset = promotions_queryset.filter(officer__prison_station=user.prison_station)
        transfers_queryset = transfers_queryset.filter(officer__prison_station=user.prison_station)
    elif is_regional_level(user) and user.region:
        promotions_queryset = promotions_queryset.filter(officer__region=user.region)
        transfers_queryset = transfers_queryset.filter(officer__region=user.region)

    if selected_year:
        promotions_queryset = promotions_queryset.filter(promotion_date__year=selected_year)
        transfers_queryset = transfers_queryset.filter(transfer_date__year=selected_year)
    if selected_month:
        promotions_queryset = promotions_queryset.filter(promotion_date__month=selected_month)
        transfers_queryset = transfers_queryset.filter(transfer_date__month=selected_month)
    if selected_region_id:
        promotions_queryset = promotions_queryset.filter(officer__region_id=selected_region_id)
        transfers_queryset = transfers_queryset.filter(officer__region_id=selected_region_id)
    if selected_station_id:
        promotions_queryset = promotions_queryset.filter(officer__prison_station_id=selected_station_id)
        transfers_queryset = transfers_queryset.filter(officer__prison_station_id=selected_station_id)
    if selected_rank_id:
        promotions_queryset = promotions_queryset.filter(new_rank_id=selected_rank_id)


    total_records = 0
    promotions_summary = []
    transfers_summary = []

    if selected_history_type == 'promotion' or not selected_history_type:
        total_promotions = promotions_queryset.count()
        promotions_by_new_rank = promotions_queryset.values('new_rank__name').annotate(count=Count('new_rank__name')).order_by('-count')
        promotions_summary = [{'type': 'Promotion', 'detail': item['new_rank__name'], 'count': item['count']} for item in promotions_by_new_rank]
        total_records += total_promotions

    if selected_history_type == 'transfer' or not selected_history_type:
        total_transfers = transfers_queryset.count()
        transfers_by_new_station = transfers_queryset.values('new_station__name', 'new_station__region__name').annotate(count=Count('new_station__name')).order_by('-count')
        transfers_summary = [{'type': 'Transfer', 'detail': f"{item['new_station__name']} ({item['new_station__region__name']})", 'count': item['count']} for item in transfers_by_new_station]
        total_records += total_transfers


    available_years_promo = PromotionHistory.objects.annotate(year=ExtractYear('promotion_date')).values_list('year', flat=True)
    available_years_transfer = TransferHistory.objects.annotate(year=ExtractYear('transfer_date')).values_list('year', flat=True)
    available_years = sorted(list(set(list(available_years_promo) + list(available_years_transfer))), reverse=True)
    if not available_years:
        available_years = [date.today().year]

    all_ranks = Rank.objects.all().order_by('name')
    regions = Region.objects.all().order_by('name')
    stations = PrisonStation.objects.all().order_by('name')

    if is_regional_level(user) and user.region:
        regions = regions.filter(pk=user.region.pk)
        stations = stations.filter(region=user.region)
    elif is_station_level(user) and user.prison_station:
        regions = regions.filter(pk=user.prison_station.region.pk)
        stations = stations.filter(pk=user.prison_station.pk)


    context = {
        'title': 'Service History Report',
        'total_records': total_records,
        'promotions_summary': promotions_summary,
        'transfers_summary': transfers_summary,
        'available_years': available_years,
        'months': [
            {'value': 1, 'name': 'January'}, {'value': 2, 'name': 'February'},
            {'value': 3, 'name': 'March'}, {'value': 4, 'name': 'April'},
            {'value': 5, 'name': 'May'}, {'value': 6, 'name': 'June'},
            {'value': 7, 'name': 'July'}, {'value': 8, 'name': 'August'},
            {'value': 9, 'name': 'September'}, {'value': 10, 'name': 'October'},
            {'value': 11, 'name': 'November'}, {'value': 12, 'name': 'December'},
        ],
        'all_ranks': all_ranks,
        'regions': regions,
        'stations': stations,
        'history_type_choices': [
            {'value': 'promotion', 'label': 'Promotion'},
            {'value': 'transfer', 'label': 'Transfer'},
        ],
        'selected_year': selected_year,
        'selected_month': selected_month,
        'selected_history_type': selected_history_type,
        'selected_rank_id': selected_rank_id,
        'selected_region_id': selected_region_id,
        'selected_station_id': selected_station_id,
    }
    return render(request, 'hrms/service_history_report.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or is_national_level(u) or is_regional_level(u) or is_station_level(u))
def report_list_view(request):
    """
    Displays a list of all available reports.
    """
    context = {
        'title': 'Reports Overview',
    }
    return render(request, 'hrms/report_list.html', context)


# --- Notification Views ---

@login_required
def notification_list_view(request):
    """
    Lists all notifications for the current user.
    """
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    context = {
        'notifications': notifications,
        'title': 'Your Notifications'
    }
    return render(request, 'hrms/notification_list.html', context)

@login_required
def notification_detail_view(request, pk):
    """
    Displays a single notification and marks it as read.
    """
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save()
    context = {
        'notification': notification,
        'title': 'Notification Details'
    }
    return render(request, 'hrms/notification_detail.html', context)

@login_required
def mark_notification_read(request, pk):
    """
    Marks a single notification as read via POST request.
    """
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save()
        messages.success(request, "Notification marked as read.")
    return redirect('hrms:notification_list')

@login_required
def mark_all_notifications_read(request):
    """
    Marks all notifications for the current user as read via POST request.
    """
    notifications = Notification.objects.filter(recipient=request.user, is_read=False)
    count = notifications.update(is_read=True)
    messages.success(request, f"{count} notifications marked as read.")
    return redirect('hrms:notification_list')

# View to get unread notification count for AJAX
@login_required
def get_unread_notification_count_view(request):
    """
    Returns the count of unread notifications for the current user as JSON.
    """
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return JsonResponse({'unread_count': unread_count})
    return JsonResponse({'unread_count': 0})

