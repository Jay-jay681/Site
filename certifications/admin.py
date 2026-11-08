from django.contrib import admin

from certifications.models import Certification , CertificationResponse

# Register your models here.
@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'organisation', 'created_at', 'created_by', 'is_active')
    list_filter = ('organisation', 'is_active')
    search_fields = ('name', 'description', 'organisation__name', 'created_by__username')
    ordering = ('-created_at',)
    
@admin.register(CertificationResponse)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'certification', 'expiration_date', 'created_at', 'type','certificate_number', 'is_active')
    list_filter = ('certification', 'is_active')
    search_fields = ('name', 'description', 'organisation__name', 'name__username')
    ordering = ('-created_at',)

        