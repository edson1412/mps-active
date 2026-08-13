from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import date, timedelta
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from accounts.models import CustomUser
from prison.models import PrisonStation, Region

# --- Helper Functions ---

def calculate_end_date_excluding_weekends(start_date, leave_days):
    """
    Calculates the leave end date by adding the specified number of leave days,
    excluding Saturdays and Sundays.

    Args:
        start_date (date): The date when the leave starts.
        leave_days (int): The total number of leave days requested.

    Returns:
        date: The calculated end date of the leave.
    """
    # Ensure a positive number of leave days
    if leave_days < 0:
        raise ValueError("leave_days cannot be negative.")

    # Initialize the current date to the start date
    current_date = start_date
    days_counted = 0

    while days_counted < leave_days:
        # Check if the current day is a weekday (Monday is 0, Sunday is 6)
        if current_date.weekday() < 5:
            days_counted += 1
        current_date += timedelta(days=1)

    # The loop adds an extra day, so subtract one to get the correct end date.
    return current_date - timedelta(days=1)


# --- Core Models ---

class Rank(models.Model):
    """
    Represents the different ranks within the prison department.
    """
    RANK_CHOICES = (
        ('watchman', _('Watchman')),
        ('messenger', _('Messenger')),
        ('warder', _('Warder')),
        ('sergeant', _('Sergeant')),
        ('gaoler', _('Gaoler')),
        ('inspector', _('Inspector')),
        ('assistant_superintendent', _('Assistant Superintendent')),
        ('superintendent', _('Superintendent')),
        ('senior_superintendent', _('Senior Superintendent')),
        ('assistant_commissioner', _('Assistant Commissioner of Prison')),
        ('deputy_commissioner', _('Deputy Commissioner of Prison')),
        ('commissioner', _('Commissioner')),
        ('commissioner_general', _('Commissioner General')),
    )
    name = models.CharField(max_length=50, choices=RANK_CHOICES, unique=True, verbose_name=_("Rank Name"))
    leave_days_annual = models.IntegerField(default=24, verbose_name=_("Annual Leave Days"))

    class Meta:
        verbose_name = _("Rank")
        verbose_name_plural = _("Ranks")
        ordering = ['name']

    def __str__(self):
        # This ensures the human-readable name is displayed in dropdowns and admin
        return self.get_name_display()


class OfficeAssignment(models.Model):
    """
    Represents various office assignments or departments within the prison service.
    """
    OFFICE_CHOICES = (
        ('general_duties', _('General Duties')),
        ('medical_officer', _('Medical Officer')),
        ('female_in_charge', _('Female In-Charge')),
        ('administration', _('Administration')),
        ('accounts_office', _('Accounts Office')),
        ('research_office', _('Research Office')),
        ('gender', _('Gender Desk')),
        ('rehabilitation', _('Rehabilitation')),
        ('public_relations_office', _('Public Relations Office')),
        ('chaplaincy', _('Chaplaincy')),
        ('secretary', _('Secretary')),
        ('staff_officer', _('Staff Officer')),
        ('protocol', _('Protocol')),
        ('restorative_justice', _('Restorative Justice')),
        ('radio_communication', _('Radio Communication')),
        ('registry', _('Registry')),
        ('ict', _('ICT')),
        ('education', _('Education')),
        ('driver', _('Driver')),
        ('transport', _('Transport')),
        ('logistics', _('Logistics')),
        ('intelligence', _('Intelligence')),
        ('legal_office', _('Legal Office')),
        ('human_resources', _('Human Resources')),
        ('trainer/instructor', _('Trainer/Instructor')),
        ('disciplinary', _('Disciplinary')),
        ('procurement', _('Procurement')),
        ('audit', _('Audit')),
        ('stores', _('Stores')),
        ('gatekeeper', _('Gatekeeper')),
        ('station_officer', _('Station Officer')),
        ('station_hr', _('Station HR')),
        ('regional_commanding_officer', _('Regional Commanding Officer')),
        ('regional_headquarters_officer', _('Regional Headquarters Officer')),
        ('regional_hr', _('Regional HR')),
        ('commissioner_administration_and_human_resource', _('Commissioner of Admin')),
        ('commissioner_rehabilitation', _('Commissioner of Rehab')),
        ('commissioner_operations', _('Commissioner of Ops')),
        ('commissioner_training_school', _('Commissioner of Training School')),
        ('commissioner_correctional_services', _('Commissioner of Correctional Services')),
        ('director_of_farms', _('Director of Farms')),
        ('national_hr', _('National HR')),
        ('station_officer_in_charge', _('Station Officer (SO)')),
        ('general_duties_officer', _('General Duties Officer (GDO)')),
        ("disciplinary_officer", _('Disciplinary Officer (DO)')),
        ('messenger', _('Messenger')),
        ('watchman', _('Watchman')),
        ('farms', _('Farms')),
        ('finance_officer', _('Finance Officer')),
        ('male_in_charge',_('Male In-Charge')),
        ('hiv/aids_coordinator', _('HIV/AIDS Coordinator')),
        ('htc', _('HTC')), # Changed duplicated key
        ('mental_health_officer', _('Mental Health Officer')),
        ('youth_officer', _('Youth Officer')),
        ('commandant', _('Commandant')),
        ('deputy_commandant', _('Deputy Commandant')),
        ('o/c_junior_training_school', _('Officer In-Charge of Junior Training School')),
        ('o/c_advance_training_school', _('Officer In-Charge of Advance Training School')),
        ('field_officer', _('Field Officer')),
        ('reception_officer', _('Reception Officer')),
        ('nutrition_officer', _('Nutritionist')),
        ('welfare_officer', _('Welfare Officer')),
        ('plumbing_officer', _('Plumbing Officer')),
        ('electrician_officer', _('Electrician Officer')),
        ('mechanical_officer', _('Mechanical Officer')),
        ('welder_officer', _('Welder Officer')),
        ('carpentry_officer', _('Carpentry Officer')),
    )
    name = models.CharField(max_length=100, choices=OFFICE_CHOICES, unique=True, verbose_name=_("Office Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    class Meta:
        verbose_name = _("Office Assignment")
        verbose_name_plural = _("Office Assignments")
        ordering = ['name']

    def __str__(self):
        return self.get_name_display()


class Officer(models.Model):
    """
    Represents a prison officer with their personal, employment, and other details.
    """
    # Personal Details
    officer_picture = models.ImageField(upload_to='officer_pictures/', blank=True, null=True, verbose_name=_("Officer Picture"))
    service_number = models.CharField(max_length=50, unique=True, verbose_name=_("Service Number"), help_text=_("Unique official service number."))
    employment_number = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name=_("Employment Number"), help_text=_("Internal government employment number."))
    first_name = models.CharField(max_length=100, verbose_name=_("First Name"))
    middle_name = models.CharField(max_length=100, blank=True, verbose_name=_("Middle Name"))
    surname = models.CharField(max_length=100, verbose_name=_("Surname"))
    date_of_birth = models.DateField(verbose_name=_("Date of Birth"))
    date_joined_service = models.DateField(verbose_name=_("Date Joined Service"))
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='officer_profile', verbose_name=_("Associated User Account"))
    GENDER_CHOICES = (
        ('male', _('Male')),
        ('female', _('Female')),

    )
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, verbose_name=_("Gender"))

    STATUS_CHOICES = (
        ('active', _('Active')),
        ('on_leave', _('On Leave')),
        ('suspended', _('Suspended')),
        ('interdicted', _('Interdicted')),
        ('retired', _('Retired')),
        ('resigned', _('Resigned')),
        ('deceased', _('Deceased')),

    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name=_("Current Status"))

    rank = models.ForeignKey(Rank, on_delete=models.SET_NULL, null=True, blank=True, related_name='officers', verbose_name=_("Current Rank"))
    current_office_assignment = models.ForeignKey(OfficeAssignment, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_officers', verbose_name=_("Current Office Assignment"))
    grade = models.CharField(max_length=5, blank= True, verbose_name=_("Grade"))

    # Contact Information
    contact_number = models.CharField(max_length=20, blank=True, verbose_name=_("Contact Number"))
    email = models.EmailField(max_length=255, unique=True, blank=True, null=True, verbose_name=_("Official Email"))

    # Location Information
    village = models.CharField(max_length=100, blank=True, verbose_name=_("Village"))
    traditional_authority = models.CharField(max_length=100, blank=True, verbose_name=_("Traditional Authority (T/A)"))
    district = models.CharField(max_length=100, blank=True, verbose_name=_("District"))
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True, related_name='officers', verbose_name=_("Assigned Region"))
    prison_station = models.ForeignKey(PrisonStation, on_delete=models.SET_NULL, null=True, blank=True, related_name='officers', verbose_name=_("Assigned Prison Station"))

    # Family Information
    MARITAL_STATUS_CHOICES = (
        ('single', _('Single')),
        ('married', _('Married')),
        ('divorced', _('Divorced')),
        ('widowed', _('Widowed')),
    )
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True, verbose_name=_("Marital Status"))
    spouse_name = models.CharField(max_length=200, blank=True, verbose_name=_("Spouse Name"))
    number_of_children = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)], verbose_name=_("Number of Children"))

    # Next of Kin
    next_of_kin_name = models.CharField(max_length=200, blank=True, verbose_name=_("Next of Kin Name"))
    next_of_kin_relationship = models.CharField(max_length=100, blank=True, verbose_name=_("Next of Kin Relationship"))
    next_of_kin_location = models.CharField(max_length=255, blank=True, verbose_name=_("Next of Kin Location"))
    next_of_kin_contact = models.CharField(max_length=20, blank=True, verbose_name=_("Next of Kin Contact"))

    # Skills and Languages
    notable_skills = models.TextField(blank=True, verbose_name=_("Notable Skills"))
    languages_spoken = models.TextField(blank=True, verbose_name=_("Languages Spoken"))

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Officer")
        verbose_name_plural = _("Officers")
        ordering = ['surname', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.surname} ({self.service_number})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.middle_name} {self.surname}".strip()

    @property
    def age(self):
        """Calculates the current age of the officer in years."""
        if self.date_of_birth:
            today = date.today()
            # Calculate years, then adjust if birthday hasn't occurred yet this year
            years = today.year - self.date_of_birth.year
            if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
                years -= 1
            return max(0, years) # Ensure age is not negative
        return None # Return None if date_of_birth is not set

    @property
    def retirement_date(self):
        """Calculates the estimated retirement date (60 years after birth date)."""
        if self.date_of_birth:
            return self.date_of_birth.replace(year=self.date_of_birth.year + 60)
        return None

    @property
    def period_of_service(self):
        """Calculates the period of service in years."""
        if self.date_joined_service:
            today = date.today()
            # Calculate years, then adjust if anniversary hasn't occurred yet this year
            years = today.year - self.date_joined_service.year
            if (today.month, today.day) < (self.date_joined_service.month, self.date_joined_service.day):
                years -= 1
            return max(0, years) # Ensure it's not negative
        return 0

    @property
    def months_until_retirement(self):
        """Calculates months until retirement (assuming retirement at 60 years old)."""
        if self.date_of_birth:
            retirement_date = self.retirement_date # Use the newly defined retirement_date property
            today = date.today()

            if not retirement_date or today >= retirement_date:
                return 0 # Already retired or retirement date cannot be calculated

            # Calculate total months difference
            delta_months = (retirement_date.year - today.year) * 12 + (retirement_date.month - today.month)

            # Adjust if current day is after retirement day in the retirement month
            if today.day > retirement_date.day:
                delta_months -= 1

            return max(0, delta_months)
        return None


class Education(models.Model):
    """
    Records educational qualifications of an officer.
    """
    officer = models.ForeignKey(Officer, on_delete=models.CASCADE, related_name='education', verbose_name=_("Officer"))
    institution = models.CharField(max_length=255, verbose_name=_("Institution"))
    qualification = models.CharField(max_length=255, verbose_name=_("Qualification"))
    year_obtained = models.IntegerField(validators=[MinValueValidator(1900), MaxValueValidator(date.today().year)], verbose_name=_("Year Obtained"))
    supporting_document = models.FileField(upload_to='education_documents/', blank=True, null=True, verbose_name=_("Supporting Document"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Education Qualification")
        verbose_name_plural = _("Education Qualifications")
        ordering = ['-year_obtained']

    def __str__(self):
        return f"{self.officer.full_name} - {self.qualification} ({self.year_obtained})"


class PromotionHistory(models.Model):
    """
    Records an officer's promotion history.
    """
    officer = models.ForeignKey(Officer, on_delete=models.CASCADE, related_name='promotions', verbose_name=_("Officer"))
    previous_rank = models.ForeignKey(Rank, on_delete=models.SET_NULL, null=True, blank=True, related_name='promoted_from', verbose_name=_("Previous Rank"))
    new_rank = models.ForeignKey(Rank, on_delete=models.CASCADE, related_name='promoted_to', verbose_name=_("New Rank"))
    promotion_date = models.DateField(default=timezone.now, verbose_name=_("Promotion Date"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    recorded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Recorded By"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Promotion History")
        verbose_name_plural = _("Promotion Histories")
        ordering = ['-promotion_date']

    def __str__(self):
        return f"{self.officer.full_name} promoted to {self.new_rank.get_name_display()} on {self.promotion_date}"


class TransferHistory(models.Model):
    """
    Records an officer's transfer history between prison stations.
    """
    officer = models.ForeignKey(Officer, on_delete=models.CASCADE, related_name='transfers', verbose_name=_("Officer"))
    previous_station = models.ForeignKey(PrisonStation, on_delete=models.SET_NULL, null=True, blank=True, related_name='transferred_from', verbose_name=_("Previous Station"))
    new_station = models.ForeignKey(PrisonStation, on_delete=models.CASCADE, related_name='transferred_to', verbose_name=_("New Station"))
    transfer_date = models.DateField(default=timezone.now, verbose_name=_("Transfer Date"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    recorded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Recorded By"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Transfer History")
        verbose_name_plural = _("Transfer Histories")
        ordering = ['-transfer_date']

    def __str__(self):
        return f"{self.officer.full_name} transferred to {self.new_station.name} on {self.transfer_date}"


class LeaveType(models.Model):
    """
    Defines different types of leave available (e.g., Annual, Maternity, Study).
    """
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Leave Type Name"))
    is_maternity = models.BooleanField(default=False, verbose_name=_("Is Maternity Leave?"))
    is_study = models.BooleanField(default=False, verbose_name=_("Is Study Leave?"))
    default_days = models.IntegerField(null=True, blank=True, verbose_name=_("Default Days (if applicable)"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    class Meta:
        verbose_name = _("Leave Type")
        verbose_name_plural = _("Leave Types")
        ordering = ['name']

    def __str__(self):
        return self.name


class LeaveRequest(models.Model):
    """
    Records an officer's leave requests.
    """
    officer = models.ForeignKey(Officer, on_delete=models.CASCADE, related_name='leave_requests', verbose_name=_("Officer"))
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='requests', verbose_name=_("Leave Type"))
    start_date = models.DateField(verbose_name=_("Start Date"))
    number_of_days = models.IntegerField(validators=[MinValueValidator(1)], verbose_name=_("Number of Days"))
    end_date = models.DateField(null=True, blank=True, verbose_name=_("End Date"))  # Auto-calculated
    supporting_document = models.FileField(upload_to='leave_documents/', blank=True, null=True, verbose_name=_("Supporting Document"))

    STATUS_CHOICES = (
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('cancelled', _('Cancelled')),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name=_("Status"))
    rejection_notes = models.TextField(blank=True, verbose_name=_("Rejection Notes"))
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Requested At"))
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leave_requests', verbose_name=_("Approved/Rejected By"))
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Approved/Rejected At"))

    class Meta:
        verbose_name = _("Leave Request")
        verbose_name_plural = _("Leave Requests")
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.officer.full_name} - {self.leave_type.name} ({self.status})"

    def save(self, *args, **kwargs):
        # Auto-calculate the end date based on the number of days, excluding weekends
        if self.start_date and self.number_of_days:
            self.end_date = calculate_end_date_excluding_weekends(self.start_date, self.number_of_days)
        super().save(*args, **kwargs)


class AnnualLeaveBalance(models.Model):
    """
    Tracks an officer's annual leave balance for a given year.
    """
    officer = models.OneToOneField(Officer, on_delete=models.CASCADE, related_name='annual_leave_balance', verbose_name=_("Officer"))
    year = models.IntegerField(verbose_name=_("Year"))
    total_days_entitled = models.IntegerField(default=0, verbose_name=_("Total Days Entitled"))
    days_taken = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name=_("Days Taken"))
    last_reset_date = models.DateField(null=True, blank=True, verbose_name=_("Last Reset Date"))

    class Meta:
        verbose_name = _("Annual Leave Balance")
        verbose_name_plural = _("Annual Leave Balances")
        unique_together = ('officer', 'year')

    def __str__(self):
        return f"{self.officer.full_name} - {self.year} Leave Balance"

    @property
    def remaining_days(self):
        return self.total_days_entitled - self.days_taken


class OfficerDocument(models.Model):
    """
    Stores various official documents related to an officer (e.g., appointment letters, disciplinary records).
    """
    FILE_TYPE_CHOICES = (
        ('letter_of_appointment', _('Letter of Appointment')),
        ('academic_certificate', _('Academic Certificate')),
        ('id_card', _('ID Card')),
        ('disciplinary_case', _('Disciplinary Case Document')),
        ('transfer_order', _('Transfer Order')),
        ('promotion_letter', _('Promotion Letter')),
        ('marriage_certificate', _('Marriage Certificate')),
        )

    officer = models.ForeignKey(Officer, on_delete=models.CASCADE, related_name='documents', verbose_name=_("Officer"))
    file_name = models.CharField(max_length=50, verbose_name=_("File Name"))
    file_number = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("File Number"))
    file_type = models.CharField(max_length=50, choices=FILE_TYPE_CHOICES, verbose_name=_("File Type"))
    document = models.FileField(upload_to='officer_documents/', verbose_name=_("Document File"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    response_notes = models.TextField(blank=True, verbose_name=_("Response Notes"))

    STATUS_CHOICES = (
        ('pending', _('Pending Review')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name=_("Status"))

    ACTION_TO_CHOICES = (
        ('national_commissioner', _('National Commissioner')),
        ('national_hr', _('National HR')),
        ('regional_commanding_officer', _('Regional Commanding Officer')),
        ('regional_headquarters_officer', _('Regional Headquarters Officer')),
        ('regional_hr', _('Regional HR')),
        ('station_officer_in_charge', _('Station Officer In-Charge')),
        ('station_officer', _('Station Officer')),
        ('station_hr', _('Station HR')),
        ('officer_self', _('Officer (Self)')),
        ('all', _('All Relevant Parties')),
    )
    action_to = models.CharField(max_length=50, choices=ACTION_TO_CHOICES, blank=True, null=True, verbose_name=_("Action Required By Role"))
    action_to_user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents_for_action', verbose_name=_("Action Required By Specific User"))

    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_documents', verbose_name=_("Uploaded By"))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Uploaded At"))
    reviewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_documents', verbose_name=_("Reviewed By"))
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Reviewed At"))
    response_notes = models.TextField(blank=True, verbose_name=_("Response Notes"))

    class Meta:
        verbose_name = _("Officer Document")
        verbose_name_plural = _("Officer Documents")
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.officer.full_name} - {self.file_name} ({self.get_status_display()})"


class PerformanceMetric(models.Model):
    """
    Defines different metrics for officer performance evaluation.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Metric Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active?"))

    class Meta:
        verbose_name = _("Performance Metric")
        verbose_name_plural = _("Performance Metrics")
        ordering = ['name']

    def __str__(self):
        return self.name


class OfficerPerformance(models.Model):
    """
    Records an officer's performance against specific metrics.
    """
    officer = models.ForeignKey(Officer, on_delete=models.CASCADE, related_name='performance_records', verbose_name=_("Officer"))
    metric = models.ForeignKey(PerformanceMetric, on_delete=models.CASCADE, related_name='performance_entries', verbose_name=_("Metric"))
    date = models.DateField(default=timezone.now, verbose_name=_("Date of Record"))
    score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name=_("Score (0-100)"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    recorded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Recorded By"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Officer Performance")
        verbose_name_plural = _("Officer Performance")
        ordering = ['-date', 'officer__surname']
        unique_together = ('officer', 'metric', 'date')

    def __str__(self):
        return f"{self.officer.full_name} - {self.metric.name} ({self.score})"


class Attendance(models.Model):
    """
    Records daily attendance for officers.
    """
    officer = models.ForeignKey(Officer, on_delete=models.CASCADE, related_name='attendance_records', verbose_name=_("Officer"))
    date = models.DateField(default=timezone.now, verbose_name=_("Date"))
    STATUS_CHOICES = (
        ('present', _('Present')),
        ('absent', _('Absent')),
        ('on_leave', _('On Leave')),
        ('sick', _('Sick Leave')),
        ('official_duty', _('Official Duty')),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name=_("Status"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    recorded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Recorded By"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Attendance")
        verbose_name_plural = _("Attendance")
        unique_together = ('officer', 'date')
        ordering = ['-date', 'officer__surname']

    def __str__(self):
        return f"{self.officer.full_name} - {self.date}: {self.get_status_display()}"


class DisciplinaryCase(models.Model):
    """
    Records disciplinary cases against officers.
    """
    officer = models.ForeignKey(Officer, on_delete=models.CASCADE, related_name='disciplinary_cases', verbose_name=_("Officer"))
    case_date = models.DateField(default=timezone.now, verbose_name=_("Case Date"))
    offense = models.CharField(max_length=255, verbose_name=_("Offense"))
    description = models.TextField(verbose_name=_("Description"))
    ACTION_TAKEN_CHOICES = (
        ('warning', _('Warning')),
        ('suspension', _('Suspension')),
        ('interdiction', _('Interdiction')),
        ('dismissal', _('Dismissal')),
        ('extra_duty', _('Extra duty')),
    )
    action_taken = models.CharField(max_length=50, choices=ACTION_TAKEN_CHOICES, blank=True, verbose_name=_("Action Taken"))
    action_date = models.DateField(null=True, blank=True, verbose_name=_("Action Date"))
    recorded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Recorded By"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Disciplinary Case")
        verbose_name_plural = _("Disciplinary Cases")
        ordering = ['-case_date']

    def __str__(self):
        return f"{self.officer.full_name} - {self.offense} ({self.case_date})"


class Notification(models.Model):
    """
    Model to store notifications for users.
    """
    NOTIFICATION_TYPE_CHOICES = (
        ('leave_request', _('Leave Request')),
        ('file_action', _('File Action')),
        ('disciplinary_action', _('Disciplinary Action')),
        ('promotion', _('Promotion')),
        ('transfer', _('Transfer')),
        ('system_alert', _('System Alert')),
        ('new_officer', _('New Officer Added')),
    )

    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='hrms_notifications', verbose_name=_("Recipient"))
    sender = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_hrms_notifications', verbose_name=_("Sender"))
    message = models.TextField(verbose_name=_("Message"))
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPE_CHOICES, verbose_name=_("Notification Type"))
    is_read = models.BooleanField(default=False, verbose_name=_("Is Read"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.username} - {self.get_notification_type_display()}: {self.message[:50]}..."

    def get_absolute_url(self):
        # This method will return the URL to the related object if available,
        # or a generic notification detail page.
        if self.notification_type == 'leave_request' and self.content_object:
            return reverse('hrms:leave_request_detail', kwargs={'pk': self.content_object.pk})
        elif self.notification_type == 'file_action' and self.content_object:
            return reverse('hrms:officer_file_detail', kwargs={'pk': self.content_object.pk})
        elif self.notification_type == 'disciplinary_action' and self.content_object:
            return reverse('hrms:disciplinary_case_detail', kwargs={'pk': self.content_object.pk})
        elif self.notification_type == 'promotion' and self.content_object:
            return reverse('hrms:officer_detail', kwargs={'service_number': self.content_object.officer.service_number})
        elif self.notification_type == 'transfer' and self.content_object:
            return reverse('hrms:officer_detail', kwargs={'service_number': self.content_object.officer.service_number})
        elif self.notification_type == 'new_officer' and self.content_object:
            return reverse('hrms:officer_detail', kwargs={'service_number': self.content_object.service_number})
        # Fallback to a generic notification detail if no specific URL is found
        return reverse('hrms:notification_detail', kwargs={'pk': self.pk})

