# hrms/admin.py

from django.contrib import admin
from .models import (
    Rank, Officer, Education, PromotionHistory, TransferHistory,
    LeaveType, LeaveRequest, AnnualLeaveBalance, OfficerDocument,
    PerformanceMetric, OfficerPerformance, Attendance, DisciplinaryCase,
    OfficeAssignment
)
from accounts.models import CustomUser # Import CustomUser for raw_id_fields

# Inlines for Officer Model
class EducationInline(admin.TabularInline):
    """Inline for Education Qualifications within Officer admin."""
    model = Education
    extra = 1 # Number of empty forms to display
    fields = ('institution', 'qualification', 'year_obtained', 'supporting_document')
    # 'officer' field is implicitly handled by the inline, no need for raw_id_fields here

class PromotionHistoryInline(admin.TabularInline):
    """Inline for Promotion History within Officer admin."""
    model = PromotionHistory
    extra = 0 # Don't show empty forms by default
    fields = ('previous_rank', 'new_rank', 'promotion_date', 'notes')
    raw_id_fields = ('previous_rank', 'new_rank', 'recorded_by')
    readonly_fields = ('recorded_by',) # Recorded by is set by view/auto_now_add

class TransferHistoryInline(admin.TabularInline):
    """Inline for Transfer History within Officer admin."""
    model = TransferHistory
    extra = 0
    fields = ('previous_station', 'new_station', 'transfer_date', 'notes')
    raw_id_fields = ('previous_station', 'new_station', 'recorded_by')
    readonly_fields = ('recorded_by',)

class LeaveRequestInline(admin.TabularInline):
    """Inline for Leave Requests within Officer admin."""
    model = LeaveRequest
    extra = 0
    fields = ('leave_type', 'start_date', 'number_of_days', 'end_date', 'status', 'supporting_document', 'rejection_notes', 'approved_by', 'approved_at')
    raw_id_fields = ('leave_type', 'approved_by')
    readonly_fields = ('end_date', 'requested_at', 'approved_by', 'approved_at') # End date is auto-calculated, timestamps are auto
    show_change_link = True # Allow clicking to full leave request detail

class OfficerDocumentInline(admin.TabularInline):
    """Inline for Officer Documents within Officer admin."""
    model = OfficerDocument
    extra = 0
    fields = ('file_name', 'file_type', 'document', 'action_to', 'status', 'notes', 'uploaded_by', 'uploaded_at', 'reviewed_by', 'reviewed_at')
    raw_id_fields = ('uploaded_by', 'reviewed_by')
    readonly_fields = ('uploaded_at', 'reviewed_at')
    show_change_link = True

class OfficerPerformanceInline(admin.TabularInline):
    """Inline for Officer Performance records within Officer admin."""
    model = OfficerPerformance
    extra = 0
    fields = ('metric', 'date', 'score', 'notes', 'recorded_by', 'created_at')
    raw_id_fields = ('metric', 'recorded_by')
    readonly_fields = ('created_at',)

class AttendanceInline(admin.TabularInline):
    """Inline for Attendance records within Officer admin."""
    model = Attendance
    extra = 0
    fields = ('date', 'status', 'notes', 'recorded_by', 'created_at')
    raw_id_fields = ('recorded_by',)
    readonly_fields = ('created_at',)

class DisciplinaryCaseInline(admin.TabularInline):
    """Inline for Disciplinary Cases within Officer admin."""
    model = DisciplinaryCase
    extra = 0
    fields = ('case_date', 'offense', 'description', 'action_taken', 'action_date', 'recorded_by', 'created_at')
    raw_id_fields = ('recorded_by',)
    readonly_fields = ('created_at', 'updated_at')


# Admin classes for each model
@admin.register(Rank)
class RankAdmin(admin.ModelAdmin):
    list_display = ('name', 'leave_days_annual')
    search_fields = ('name',)
    list_filter = ('leave_days_annual',)

@admin.register(OfficeAssignment)
class OfficeAssignmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Officer)
class OfficerAdmin(admin.ModelAdmin):
    list_display = (
        'service_number', 'employment_number', 'full_name', 'rank',
        'prison_station', 'status', 'date_joined_service',
        'period_of_service', 'months_until_retirement'
    )
    list_filter = ('status', 'rank', 'prison_station__region', 'prison_station', 'gender', 'marital_status')
    search_fields = (
        'service_number', 'employment_number', 'first_name', 'middle_name', 'surname',
        'email', 'contact_number', 'village', 'traditional_authority', 'district'
    )
    raw_id_fields = ('rank', 'region', 'prison_station', 'current_office_assignment')
    readonly_fields = ('period_of_service', 'months_until_retirement', 'created_at', 'updated_at')
    inlines = [
        EducationInline,
        PromotionHistoryInline,
        TransferHistoryInline,
        LeaveRequestInline,
        OfficerDocumentInline,
        OfficerPerformanceInline,
        AttendanceInline,
        DisciplinaryCaseInline,
    ]
    fieldsets = (
        (None, {'fields': ('officer_picture', 'service_number', 'employment_number', 'status', 'gender', 'first_name', 'middle_name', 'surname', 'date_of_birth', 'date_joined_service', 'rank', 'current_office_assignment')}),
        ('Contact Information', {'fields': ('contact_number', 'email')}),
        ('Location Information', {'fields': ('village', 'traditional_authority', 'district', 'region', 'prison_station')}),
        ('Family Information', {'fields': ('marital_status', 'spouse_name', 'number_of_children')}),
        ('Next of Kin', {'fields': ('next_of_kin_name', 'next_of_kin_relationship', 'next_of_kin_location', 'next_of_kin_contact')}),
        ('Skills & Languages', {'fields': ('notable_skills', 'languages_spoken')}),
        ('Auto-Calculated Fields', {'fields': ('period_of_service', 'months_until_retirement')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def get_queryset(self, request):
        # Prefetch related data for efficiency in list display
        return super().get_queryset(request).select_related('rank', 'prison_station', 'region')

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Full Name'


@admin.register(PromotionHistory)
class PromotionHistoryAdmin(admin.ModelAdmin):
    list_display = ('officer', 'previous_rank', 'new_rank', 'promotion_date', 'recorded_by')
    list_filter = ('promotion_date', 'previous_rank', 'new_rank', 'officer__prison_station__region')
    search_fields = ('officer__service_number', 'officer__first_name', 'officer__surname', 'notes')
    raw_id_fields = ('officer', 'previous_rank', 'new_rank', 'recorded_by')
    date_hierarchy = 'promotion_date'

@admin.register(TransferHistory)
class TransferHistoryAdmin(admin.ModelAdmin):
    list_display = ('officer', 'previous_station', 'new_station', 'transfer_date', 'recorded_by')
    list_filter = ('transfer_date', 'previous_station__region', 'new_station__region')
    search_fields = ('officer__service_number', 'officer__first_name', 'officer__surname', 'notes')
    raw_id_fields = ('officer', 'previous_station', 'new_station', 'recorded_by')
    date_hierarchy = 'transfer_date'

@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'default_days', 'is_maternity', 'is_study')
    search_fields = ('name',)
    list_filter = ('is_maternity', 'is_study')

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = (
        'officer', 'leave_type', 'start_date', 'end_date', 'number_of_days',
        'status', 'requested_at', 'approved_by', 'approved_at'
    )
    list_filter = ('status', 'leave_type', 'officer__prison_station__region', 'officer__prison_station')
    search_fields = (
        'officer__service_number', 'officer__first_name', 'officer__surname',
        'leave_type__name', 'rejection_notes'
    )
    raw_id_fields = ('officer', 'leave_type', 'approved_by')
    readonly_fields = ('end_date', 'requested_at', 'approved_at')
    date_hierarchy = 'requested_at'

@admin.register(AnnualLeaveBalance)
class AnnualLeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ('officer', 'year', 'total_days_entitled', 'days_taken', 'remaining_days', 'last_reset_date')
    list_filter = ('year', 'officer__prison_station__region', 'officer__prison_station')
    search_fields = ('officer__service_number', 'officer__first_name', 'officer__surname')
    raw_id_fields = ('officer',)
    readonly_fields = ('remaining_days',) # Calculated property

@admin.register(OfficerDocument)
class OfficerDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'officer', 'file_name', 'file_type', 'uploaded_at', 'action_to',
        'status', 'reviewed_by', 'reviewed_at'
    )
    list_filter = ('file_type', 'status', 'action_to', 'officer__prison_station__region')
    search_fields = (
        'officer__service_number', 'officer__first_name', 'officer__surname',
        'file_name', 'notes'
    )
    raw_id_fields = ('officer', 'uploaded_by', 'reviewed_by')
    date_hierarchy = 'uploaded_at'

@admin.register(PerformanceMetric)
class PerformanceMetricAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(OfficerPerformance)
class OfficerPerformanceAdmin(admin.ModelAdmin):
    list_display = ('officer', 'metric', 'date', 'score', 'recorded_by')
    list_filter = ('metric', 'date', 'officer__prison_station__region')
    search_fields = ('officer__service_number', 'officer__first_name', 'officer__surname', 'notes')
    raw_id_fields = ('officer', 'metric', 'recorded_by')
    date_hierarchy = 'date'

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('officer', 'date', 'status', 'recorded_by')
    list_filter = ('status', 'date', 'officer__prison_station__region')
    search_fields = ('officer__service_number', 'officer__first_name', 'officer__surname', 'notes')
    raw_id_fields = ('officer', 'recorded_by')
    date_hierarchy = 'date'

@admin.register(DisciplinaryCase)
class DisciplinaryCaseAdmin(admin.ModelAdmin):
    list_display = ('officer', 'case_date', 'offense', 'action_taken', 'action_date', 'recorded_by')
    list_filter = ('action_taken', 'case_date', 'officer__prison_station__region')
    search_fields = ('officer__service_number', 'officer__first_name', 'officer__surname', 'offense', 'description')
    raw_id_fields = ('officer', 'recorded_by')
    date_hierarchy = 'case_date'

