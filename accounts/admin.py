from django.contrib import admin

from .models import CustomUser, Invitation, Organisation, Site, SiteLinks


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "organisation", "trade", "is_active", "is_platform_admin")
    list_filter = ("is_active", "is_platform_admin", "organisation")
    search_fields = ("name", "phone", "email", "employee_id")
    exclude = ("password", "pin_hash")
    readonly_fields = ("date_joined", "pin_failed_attempts", "pin_lockdown")


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_email", "is_active", "date_created")
    list_filter = ("is_active",)
    search_fields = ("name", "contact_email")


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "organisation", "hard_capacity", "timezone", "is_active")
    list_filter = ("is_active", "organisation")
    search_fields = ("name", "address")


@admin.register(SiteLinks)
class SiteLinksAdmin(admin.ModelAdmin):
    list_display = ("user", "site", "roles", "is_active", "date_created")
    list_filter = ("roles", "is_active", "site")
    search_fields = ("user__name", "user__phone", "site__name")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "role", "sites", "status", "tokens_exp", "invited_by")
    list_filter = ("status", "role", "organisation")
    search_fields = ("name", "phone")
    readonly_fields = ("status", "accepted_user", "accepted_at", "revoked_at", "date_created")

    def has_add_permission(self, request):
        return False