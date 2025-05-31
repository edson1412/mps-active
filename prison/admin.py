from django.contrib import admin
from .models import *

class ConvictedPrisonerInline(admin.StackedInline):
    model = ConvictedPrisoner
    extra = 0

class RemandPrisonerInline(admin.StackedInline):
    model = RemandPrisoner
    extra = 0

class RiskAssessmentInline(admin.StackedInline):
    model = RiskAssessment
    extra = 0

class PrisonerParticularsInline(admin.StackedInline):
    model = PrisonerParticulars
    extra = 0

class PhysicalCharacteristicsInline(admin.StackedInline):
    model = PhysicalCharacteristics
    extra = 0

class RehabilitationProgramInline(admin.StackedInline):
    model = RehabilitationProgram
    extra = 0

class PrisonerTransferInline(admin.TabularInline):
    model = PrisonerTransfer
    extra = 0
    readonly_fields = ('transfer_date', 'transferred_by')
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Prisoner)
class PrisonerAdmin(admin.ModelAdmin):
    list_display = ('prisoner_number', 'full_name', 'prisoner_class', 'prison_station', 'date_admitted', 'is_active')
    list_filter = ('prisoner_class', 'prison_station', 'is_active', 'date_admitted')
    search_fields = ('prisoner_number', 'first_name', 'middle_name', 'surname')
    inlines = [
        ConvictedPrisonerInline,
        RemandPrisonerInline,
        RiskAssessmentInline,
        PrisonerParticularsInline,
        PhysicalCharacteristicsInline,
        RehabilitationProgramInline,
        PrisonerTransferInline,
    ]
    
    def get_inline_instances(self, request, obj=None):
        # Only show relevant inlines based on prisoner class
        inlines = []
        if obj is None:
            return inlines
        
        base_inlines = [
            PrisonerParticularsInline,
            PhysicalCharacteristicsInline,
        ]
        
        if obj.prisoner_class == 'convicted':
            base_inlines.extend([
                ConvictedPrisonerInline,
                RiskAssessmentInline,
                RehabilitationProgramInline,
            ])
        else:
            base_inlines.append(RemandPrisonerInline)
        
        base_inlines.append(PrisonerTransferInline)
        
        for inline_class in base_inlines:
            inline = inline_class(self.model, self.admin_site)
            inlines.append(inline)
        
        return inlines

@admin.register(PrisonStation)
class PrisonStationAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'location', 'capacity', 'date_established')
    search_fields = ('name', 'code', 'location')

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'model', 'object_id', 'timestamp')
    list_filter = ('action', 'model', 'timestamp')
    search_fields = ('user__username', 'details')
    readonly_fields = ('user', 'action', 'model', 'object_id', 'details', 'timestamp')
    
    def has_add_permission(self, request):
        return False

@admin.register(ReleaseOnRemission)
class ReleaseOnRemissionAdmin(admin.ModelAdmin):
    list_display = ('prisoner', 'release_date', 'original_sentence', 'remission_months', 'reduction_months')
    list_filter = ('release_date',)
    search_fields = ('prisoner__prisoner_number', 'prisoner__first_name', 'prisoner__surname')
    readonly_fields = ('processed_date',)