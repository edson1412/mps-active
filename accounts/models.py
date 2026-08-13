from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    """Single user model for both the inmates (prison) and officers (HRMS) modules."""

    # Inmate management roles
    ROLE_SUPERUSER = 'superuser'
    ROLE_ADMIN = 'admin'
    ROLE_RECEPTION = 'reception'
    ROLE_OFFICER_IN_CHARGE = 'officer_in_charge'
    ROLE_STATION_OFFICER = 'station_officer'
    ROLE_VISITOR_ATTENDANT = 'visitor_attendant'
    ROLE_MEDICAL = 'medical'

    # Officer management (HRMS) roles
    ROLE_NATIONAL_COMMISSIONER = 'national_commissioner'
    ROLE_NATIONAL_HR = 'national_hr'
    ROLE_RCO = 'regional_commanding_officer'
    ROLE_RHO = 'regional_headquarters_officer'
    ROLE_REGIONAL_HR = 'regional_hr'
    ROLE_STATION_HR = 'station_hr'

    ROLE_CHOICES = [
        (ROLE_SUPERUSER, 'Super Administrator'),
        (ROLE_ADMIN, 'Prison Administrator'),
        (ROLE_RECEPTION, 'Reception Officer'),
        (ROLE_OFFICER_IN_CHARGE, 'Officer in Charge'),
        (ROLE_STATION_OFFICER, 'Station Officer'),
        (ROLE_VISITOR_ATTENDANT, 'Visitor Attendant'),
        (ROLE_MEDICAL, 'Medical Officer'),
        (ROLE_NATIONAL_COMMISSIONER, 'Commissioner of Administration/HR (National)'),
        (ROLE_NATIONAL_HR, 'National HR Officer'),
        (ROLE_RCO, 'Region Commanding Officer (RCO)'),
        (ROLE_RHO, 'Region Headquarters Officer (RHO)'),
        (ROLE_REGIONAL_HR, 'Regional HR Officer'),
        (ROLE_STATION_HR, 'Station HR Officer'),
    ]

    # Roles that work inside the officers (HRMS) module
    HRMS_ROLES = [
        ROLE_NATIONAL_COMMISSIONER,
        ROLE_NATIONAL_HR,
        ROLE_RCO,
        ROLE_RHO,
        ROLE_REGIONAL_HR,
        ROLE_STATION_HR,
        ROLE_OFFICER_IN_CHARGE,
    ]

    # Roles that work inside the inmates (prison) module
    INMATE_ROLES = [
        ROLE_ADMIN,
        ROLE_RECEPTION,
        ROLE_OFFICER_IN_CHARGE,
        ROLE_STATION_OFFICER,
        ROLE_VISITOR_ATTENDANT,
        ROLE_MEDICAL,
        ROLE_RCO,
        ROLE_RHO,
    ]

    RANK_CHOICES = [
        ('warder', 'Warder'),
        ('sergeant', 'Sergeant'),
        ('gaoler', 'Gaoler'),
        ('inspector', 'Inspector'),
        ('Supritendent', 'Supritendent'),
        ('ACP', 'ACP'),
        ('DCP', 'DCP'),
    ]

    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default=ROLE_RECEPTION)
    rank = models.CharField(max_length=20, choices=RANK_CHOICES, blank=True)
    prison_station = models.ForeignKey(
        'prison.PrisonStation',  # Use string reference to avoid circular import
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
    )
    region = models.ForeignKey(
        'prison.Region',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_("Assigned Region"),
        help_text=_("Region scope, required for regional level roles."),
    )
    must_change_password = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ['username']

    def __str__(self):
        station_name = self.prison_station.name if self.prison_station else 'No station'
        return f"{self.get_full_name() or self.username} ({station_name})"

    # ------------------------------------------------------------------
    # Inmate module role helpers (callables, kept for prison app/templates)
    # ------------------------------------------------------------------
    def is_super_admin(self):
        return self.role == self.ROLE_SUPERUSER or self.is_superuser

    def is_prison_admin(self):
        return self.role == self.ROLE_ADMIN

    def is_reception(self):
        return self.role == self.ROLE_RECEPTION

    def is_officer_in_charge(self):
        return self.role == self.ROLE_OFFICER_IN_CHARGE

    def is_station_officer(self):
        return self.role == self.ROLE_STATION_OFFICER

    def is_visitor_attendant(self):
        return self.role == self.ROLE_VISITOR_ATTENDANT

    def is_medical_officer(self):
        return self.role == self.ROLE_MEDICAL

    def has_region_permission(self):
        """Whether the user is scoped to a whole region."""
        return self.region is not None and (
            self.is_super_admin() or self.is_prison_admin() or self.is_regional_level
        )

    def has_station_permission(self):
        return self.prison_station is not None

    # ------------------------------------------------------------------
    # Officer module (HRMS) role helpers (properties, kept for hrms templates)
    # ------------------------------------------------------------------
    @property
    def is_national_level(self):
        return self.is_super_admin() or self.role in [
            self.ROLE_NATIONAL_COMMISSIONER,
            self.ROLE_NATIONAL_HR,
        ]

    @property
    def is_regional_level(self):
        return self.role in [self.ROLE_RCO, self.ROLE_RHO, self.ROLE_REGIONAL_HR]

    @property
    def is_station_level(self):
        return self.role in [
            self.ROLE_OFFICER_IN_CHARGE,
            self.ROLE_STATION_OFFICER,
            self.ROLE_STATION_HR,
            self.ROLE_RECEPTION,
            self.ROLE_VISITOR_ATTENDANT,
            self.ROLE_MEDICAL,
        ]

    @property
    def is_commissioner(self):
        return self.role == self.ROLE_NATIONAL_COMMISSIONER

    @property
    def is_national_hr(self):
        return self.role == self.ROLE_NATIONAL_HR

    @property
    def is_rco(self):
        return self.role == self.ROLE_RCO

    @property
    def is_rho(self):
        return self.role == self.ROLE_RHO

    @property
    def is_regional_hr(self):
        return self.role == self.ROLE_REGIONAL_HR

    @property
    def is_oc(self):
        return self.role == self.ROLE_OFFICER_IN_CHARGE

    @property
    def is_so(self):
        return self.role == self.ROLE_STATION_OFFICER

    @property
    def is_station_hr(self):
        return self.role == self.ROLE_STATION_HR

    # ------------------------------------------------------------------
    # Module access
    # ------------------------------------------------------------------
    @property
    def can_access_hrms(self):
        return self.is_super_admin() or self.role in self.HRMS_ROLES

    @property
    def can_access_inmates(self):
        return self.is_super_admin() or self.role in self.INMATE_ROLES
