---
name: testing-mps-active
description: How to run and end-to-end test the merged Malawi Prison Service Django app (prison inmates at /, HRMS officers at /hr/, auth at /accounts/), including seeding role-based test users and known defect patterns.
---

# Testing mps-active (prison + HRMS merged Django project)

## Run it
```bash
/home/ubuntu/venv/bin/python manage.py migrate
/home/ubuntu/venv/bin/python manage.py runserver 0.0.0.0:8000
```
URL layout: `/` inmates (prison app), `/hr/` officers (hrms app, namespace `hrms:`), `/accounts/` auth.
SQLite `db.sqlite3` is committed, so existing prisoners/stations are usually already present.

## Seed role users fast
One `accounts.CustomUser` model holds both role sets plus `region` (prison.Region FK) and
`prison_station` (prison.PrisonStation FK). Seed with a shell one-liner rather than the UI:
```bash
/home/ubuntu/venv/bin/python manage.py shell -c "
from accounts.models import CustomUser
from prison.models import Region, PrisonStation
r=Region.objects.get(name__icontains='Southern'); s=PrisonStation.objects.get(name__icontains='Blantyre')
for un,role in [('adm','admin'),('oic','officer_in_charge'),('nathr','national_hr'),('sthr','station_hr')]:
    u,_=CustomUser.objects.get_or_create(username=un)
    u.role=role; u.region=r; u.prison_station=s; u.must_change_password=False
    u.set_password('TestPass123!'); u.save()
"
```
Landing pages come from `accounts/routing.py` (`landing_url_for`): admin/superuser → `/`,
reception/officer_in_charge/station_officer → `/release-hub/`, visitor_attendant → `/visitors/`,
medical → `/medical/`, all HR/commissioner roles → `/hr/`.

For the forced-password-change test, set `must_change_password=True` and re-`set_password` before
each attempt (the flag flips permanently once the change succeeds).

## Log in/out quickly in the browser
Navigating to `http://127.0.0.1:8000/accounts/logout/` logs out and lands on the login form, so a
role switch is: go to that URL, type username, password, Enter. Typing a URL into the omnibox may
leave an autocomplete suffix — after typing, press `Delete` then `Return`.

## Defect patterns worth checking first
- HRMS templates that render a model form with `{% crispy form %}` inside their own `<form>` need
  `helper.form_tag = False`, otherwise crispy emits a nested `<form>`, the page's Save
  `<button type="submit">` ends up **outside** it, and clicking Save produces no POST at all — the
  page just sits there with no error. Confirm by checking whether the submit button is inside
  `<form>` in the DOM and that no row was created in `manage.py shell`.
- Scoping is easy to apply only to dashboard aggregates (`get_filtered_officers_queryset` in
  `hrms/views.py`) and forget on list views: check `/hr/officers/` as a regional/station HR user and
  compare against the dashboard "Total Officers" count. `is_station_level()`/`is_regional_level()`
  match raw role strings, so a typo there silently unscopes a whole role.
- Known preexisting bugs (may still be present, not regressions): `PrisonerSearchForm` does
  `PrisonStation.objects.get(name=user.prison_station)` so `/prisoners/` 500s for station-assigned
  users — test prisoner pages as a superuser instead; `accounts/mixins.py RoleRequiredMixin` calls
  `getattr(user,'is_superuser')()` on a bool, which can 500 HR roles visiting `/medical/`.

## Devin Secrets Needed
None — fully local SQLite app.
