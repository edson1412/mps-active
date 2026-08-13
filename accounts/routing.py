"""Role based routing for the single sign-in page.

Both modules (inmate management in ``prison`` and officer management in ``hrms``)
are served by one login page; the landing page depends on the user's role.
"""

from django.urls import reverse

from .models import CustomUser

# Landing url name per role. Names without a namespace belong to the prison app.
ROLE_LANDING_URLS = {
    CustomUser.ROLE_SUPERUSER: 'dashboard',
    CustomUser.ROLE_ADMIN: 'dashboard',
    CustomUser.ROLE_RECEPTION: 'release_hub',
    CustomUser.ROLE_OFFICER_IN_CHARGE: 'release_hub',
    CustomUser.ROLE_STATION_OFFICER: 'release_hub',
    CustomUser.ROLE_VISITOR_ATTENDANT: 'visitor_list',
    CustomUser.ROLE_MEDICAL: 'medical_record_list',
    CustomUser.ROLE_NATIONAL_COMMISSIONER: 'hrms:dashboard',
    CustomUser.ROLE_NATIONAL_HR: 'hrms:dashboard',
    CustomUser.ROLE_RCO: 'hrms:dashboard',
    CustomUser.ROLE_RHO: 'hrms:dashboard',
    CustomUser.ROLE_REGIONAL_HR: 'hrms:dashboard',
    CustomUser.ROLE_STATION_HR: 'hrms:dashboard',
}

DEFAULT_LANDING_URL_NAME = 'dashboard'


def landing_url_name_for(user):
    if user.is_super_admin():
        return ROLE_LANDING_URLS[CustomUser.ROLE_SUPERUSER]
    return ROLE_LANDING_URLS.get(user.role, DEFAULT_LANDING_URL_NAME)


def landing_url_for(user):
    """Absolute path the user should land on right after signing in."""
    return reverse(landing_url_name_for(user))
