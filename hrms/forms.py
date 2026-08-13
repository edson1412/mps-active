# hrms/forms.py

from django import forms
from prison.models import PrisonStation, Region
from .models import Officer, Education, PromotionHistory, TransferHistory, LeaveRequest, OfficerDocument, PerformanceMetric, OfficerPerformance, Attendance, DisciplinaryCase, Rank, OfficeAssignment, LeaveType
from django.forms import inlineformset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Fieldset, Field, HTML
from django.utils.translation import gettext_lazy as _

class OfficerForm(forms.ModelForm):
    """
    Form for creating and updating Officer records.
    Uses crispy-forms for better layout.
    """
    class Meta:
        model = Officer
        # Include all fields you want to be editable via the form
        fields = [
            'officer_picture', 'service_number', 'employment_number', 'status', 'gender',
            'first_name', 'middle_name', 'surname', 'date_of_birth', 'date_joined_service',
            'rank', 'grade', 'contact_number', 'email', 'village', 'traditional_authority', 'district',
            'marital_status', 'spouse_name', 'number_of_children',
            'next_of_kin_name', 'next_of_kin_relationship', 'next_of_kin_location', 'next_of_kin_contact',
            'region', 'prison_station', 'current_office_assignment',
            'notable_skills', 'languages_spoken'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_joined_service': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notable_skills': forms.Textarea(attrs={'rows': 3}),
            'languages_spoken': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            # Personal Information Section
            HTML('''
                <div class="card shadow-sm rounded-3 mb-4 border-primary">
                    <div class="card-header bg-primary text-white rounded-top-3">
                        <h5 class="mb-0"><i class="fas fa-info-circle me-2"></i>Personal Information</h5>
                    </div>
                    <div class="card-body">
            '''),
            Row(
                Column('officer_picture', css_class='form-group col-md-12 mb-3'),
                Column('service_number', css_class='form-group col-md-12 mb-3'),
                Column('employment_number', css_class='form-group col-md-12 mb-3'),
                Column('first_name', css_class='form-group col-md-12 mb-3'),
                Column('middle_name', css_class='form-group col-md-12 mb-3'),
                Column('surname', css_class='form-group col-md-12 mb-3'),
                Column('date_of_birth', css_class='form-group col-md-12 mb-3'),
                Column('date_joined_service', css_class='form-group col-md-12 mb-3'),
                Column('gender', css_class='form-group col-md-12 mb-3'),
                Column('status', css_class='form-group col-md-12 mb-3'),
                Column('rank', css_class='form-group col-md-12 mb-3'),
                Column('current_office_assignment', css_class='form-group col-md-12 mb-3'),
                Column('grade',css_class='form-group col-md-12 mb-3'),
                css_class='row' # Ensure these columns are within a row
            ),
            HTML('</div></div>'), # Close card-body and card

            # Contact & Location Section
            HTML('''
                <div class="card shadow-sm rounded-3 mb-4 border-success">
                    <div class="card-header bg-success text-white rounded-top-3">
                        <h5 class="mb-0"><i class="fas fa-map-marker-alt me-2"></i>Contact & Location</h5>
                    </div>
                    <div class="card-body">
            '''),
            Row(
                Column('contact_number', css_class='form-group col-md-12 mb-3'),
                Column('email', css_class='form-group col-md-12 mb-3'),
                Column('village', css_class='form-group col-md-12 mb-3'),
                Column('traditional_authority', css_class='form-group col-md-12 mb-3'),
                Column('district', css_class='form-group col-md-12 mb-3'),
                Column('region', css_class='form-group col-md-12 mb-3'),
                Column('prison_station', css_class='form-group col-md-12 mb-3'),
                css_class='row'
            ),
            HTML('</div></div>'), # Close card-body and card

            # Family Information Section
            HTML('''
                <div class="card shadow-sm rounded-3 mb-4 border-info">
                    <div class="card-header bg-info text-white rounded-top-3">
                        <h5 class="mb-0"><i class="fas fa-heart me-2"></i>Family Information</h5>
                    </div>
                    <div class="card-body">
            '''),
            Row(
                Column('marital_status', css_class='form-group col-md-12 mb-3'),
                Column('spouse_name', css_class='form-group col-md-12 mb-3'),
                Column('number_of_children', css_class='form-group col-md-12 mb-3'),
                css_class='row'
            ),
            HTML('</div></div>'), # Close card-body and card

            # Next of Kin Section
            HTML('''
                <div class="card shadow-sm rounded-3 mb-4 border-warning">
                    <div class="card-header bg-warning text-white rounded-top-3">
                        <h5 class="mb-0"><i class="fas fa-user-friends me-2"></i>Next of Kin</h5>
                    </div>
                    <div class="card-body">
            '''),
            Row(
                Column('next_of_kin_name', css_class='form-group col-md-12 mb-3'),
                Column('next_of_kin_relationship', css_class='form-group col-md-12 mb-3'),
                Column('next_of_kin_location', css_class='form-group col-md-12 mb-3'),
                Column('next_of_kin_contact', css_class='form-group col-md-12 mb-3'),
                css_class='row'
            ),
            HTML('</div></div>'), # Close card-body and card

            # Skills & Languages Section
            HTML('''
                <div class="card shadow-sm rounded-3 mb-4 border-danger">
                    <div class="card-header bg-danger text-white rounded-top-3">
                        <h5 class="mb-0"><i class="fas fa-lightbulb me-2"></i>Skills & Languages</h5>
                    </div>
                    <div class="card-body">
            '''),
            Row(
                Column('notable_skills', css_class='form-group col-md-12 mb-3'),
                Column('languages_spoken', css_class='form-group col-md-12 mb-3'),
                css_class='row'
            ),
            HTML('</div></div>'), # Close card-body and card

            # Note: Educational Qualifications (formset) will be rendered manually in the template,
            # as Crispy Forms doesn't handle inline formsets with custom layouts as elegantly.

            # Filter choices based on user role (if applicable, for station/regional HR)
            # This logic remains the same
        )

        if user:
            if user.is_station_level and user.prison_station:
                self.fields['prison_station'].queryset = PrisonStation.objects.filter(pk=user.prison_station.pk)
                self.fields['prison_station'].initial = user.prison_station
                self.fields['prison_station'].widget.attrs['readonly'] = True
                self.fields['region'].queryset = Region.objects.filter(pk=user.prison_station.region.pk)
                self.fields['region'].initial = user.prison_station.region
                self.fields['region'].widget.attrs['readonly'] = True
            elif user.is_regional_level and user.region:
                self.fields['region'].queryset = Region.objects.filter(pk=user.region.pk)
                self.fields['region'].initial = user.region
                self.fields['region'].widget.attrs['readonly'] = True
                self.fields['prison_station'].queryset = PrisonStation.objects.filter(region=user.region)
            # For national level, no filtering needed, they see all

    def clean(self):
        cleaned_data = super().clean()
        marital_status = cleaned_data.get('marital_status')
        spouse_name = cleaned_data.get('spouse_name')

        if marital_status == 'married' and not spouse_name:
            self.add_error('spouse_name', _("Spouse name is required if marital status is 'Married'."))
        return cleaned_data


class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = ['institution', 'qualification', 'year_obtained', 'supporting_document']
        widgets = {
            'year_obtained': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Column('institution', css_class='form-group col-md-12 mb-3'),
            Column('qualification', css_class='form-group col-md-12 mb-3'),
            Column('year_obtained', css_class='form-group col-md-12 mb-3'),
            Column('supporting_document', css_class='form-group col-md-12 mb-3'),
        )


# Inline formset for Education to allow adding multiple education records
EducationFormSet = inlineformset_factory(Officer, Education, form=EducationForm, extra=1, can_delete=True)

class PromotionHistoryForm(forms.ModelForm):
    class Meta:
        model = PromotionHistory
        fields = ['previous_rank', 'new_rank', 'promotion_date', 'notes']
        widgets = {
            'promotion_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Column('previous_rank', css_class='form-group col-md-12 mb-3'),
            Column('new_rank', css_class='form-group col-md-12 mb-3'),
            Column('promotion_date', css_class='form-group col-md-12 mb-3'),
            Column('notes', css_class='form-group col-md-12 mb-3'),
        )

class TransferHistoryForm(forms.ModelForm):
    class Meta:
        model = TransferHistory
        fields = ['previous_station', 'new_station', 'transfer_date', 'notes']
        widgets = {
            'transfer_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Column('previous_station', css_class='form-group col-md-12 mb-3'),
            Column('new_station', css_class='form-group col-md-12 mb-3'),
            Column('transfer_date', css_class='form-group col-md-12 mb-3'),
            Column('notes', css_class='form-group col-md-12 mb-3'),
        )

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'number_of_days', 'supporting_document']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Column('leave_type', css_class='form-group col-md-12 mb-3'),
            Column('start_date', css_class='form-group col-md-12 mb-3'),
            Column('number_of_days', css_class='form-group col-md-12 mb-3'),
            Column('supporting_document', css_class='form-group col-md-12 mb-3'),
        )
        # Add JavaScript to dynamically update default_days based on selected leave_type
        self.fields['leave_type'].widget.attrs.update({'onchange': 'updateLeaveDays(this)'})

class LeaveApprovalForm(forms.ModelForm):
    """
    Form for approving or rejecting a leave request.
    """
    class Meta:
        model = LeaveRequest
        fields = ['status', 'rejection_notes']
        widgets = {
            'rejection_notes': forms.Textarea(attrs={'rows': 3}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Column('status', css_class='form-group col-md-12 mb-3'),
            Column('rejection_notes', css_class='form-group col-md-12 mb-3'),
        )

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        rejection_notes = cleaned_data.get('rejection_notes')

        if status == 'rejected' and not rejection_notes:
            self.add_error('rejection_notes', _("Rejection notes are required if the request is rejected."))
        return cleaned_data


class OfficerDocumentForm(forms.ModelForm):
    class Meta:
        model = OfficerDocument
        fields = ['file_name', 'file_number', 'file_type', 'document', 'notes','action_to']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Column('file_name', 'file_number', 'file_type', css_class='form-row'),
            Column('document', 'notes', css_class='form-row'),
            Column('action_to', css_class='form-group col-md-12 mb-3'),

        )

class OfficerFileResponseForm(forms.ModelForm):
    """
    Form for responding to an officer file (approving/rejecting).
    """
    class Meta:
        model = OfficerDocument
        fields = ['status', 'response_notes']
        widgets = {
            'response_notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Column('status', css_class='form-group col-md-12 mb-3'),
            Column('response_notes', css_class='form-group col-md-12 mb-3'),
        )

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        notes = cleaned_data.get('notes')
        response_notes = cleaned_data.get('response_notes')


        return cleaned_data



class OfficerPerformanceForm(forms.ModelForm):
    class Meta:
        model = OfficerPerformance
        fields = ['metric', 'date', 'score', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Column('metric', css_class='form-group col-md-12 mb-3'),
            Column('date', css_class='form-group col-md-12 mb-3'),
            Column('score', css_class='form-group col-md-12 mb-3'),
            Column('notes', css_class='form-group col-md-12 mb-3'),
        )

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['date', 'status', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Column('date', css_class='form-group col-md-12 mb-3'),
            Column('status', css_class='form-group col-md-12 mb-3'),
            Column('notes', css_class='form-group col-md-12 mb-3'),
        )

class DisciplinaryCaseForm(forms.ModelForm):
    class Meta:
        model = DisciplinaryCase
        fields = ['case_date', 'offense', 'description', 'action_taken', 'action_date']
        widgets = {
            'case_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'action_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Column('case_date', css_class='form-group col-md-12 mb-3'),
            Column('offense', css_class='form-group col-md-12 mb-3'),
            Column('description', css_class='form-group col-md-12 mb-3'),
            Column('action_taken', css_class='form-group col-md-12 mb-3'),
            Column('action_date', css_class='form-group col-md-12 mb-3'),
        )

class OfficeAssignmentForm(forms.ModelForm):
    class Meta:
        model = Officer
        fields = ['current_office_assignment']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Column('current_office_assignment', css_class='form-group col-md-12 mb-3'),
        )

# New Forms for Region and PrisonStation
class RegionForm(forms.ModelForm):
    class Meta:
        model = Region
        fields = ['name', 'code', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Column('name', css_class='form-group col-md-12 mb-3'),
            Column('code', css_class='form-group col-md-12 mb-3'),
            Column('description', css_class='form-group col-md-12 mb-3'),
        )

class PrisonStationForm(forms.ModelForm):
    class Meta:
        model = PrisonStation
        fields = ['name', 'code', 'region', 'location', 'contact_number', 'capacity', 'date_established']
        widgets = {
            'date_established': forms.DateInput(attrs={'type': 'date'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-6 mb-3'),
                Column('code', css_class='form-group col-md-6 mb-3'),
            ),
            Row(
                Column('region', css_class='form-group col-md-6 mb-3'),
                Column('location', css_class='form-group col-md-6 mb-3'),
            ),
            Row(
                Column('contact_number', css_class='form-group col-md-4 mb-3'),
                Column('capacity', css_class='form-group col-md-4 mb-3'),
                Column('date_established', css_class='form-group col-md-4 mb-3'),
            ),
        )
