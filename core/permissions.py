from ninja.errors import HttpError

from .authentication import JwtAuth
from accounts.models import Role, SiteLinks
from accounts.models import Site


class RoleRequired(JwtAuth):
    allow_platform_admin = False
    site_roles = []

    def authenticate(self, request, token):
        user = super().authenticate(request, token)

        if user is None:
            return None

        if self.allow_platform_admin and user.is_platform_admin:
            return user

        if self.site_roles and SiteLinks.objects.filter(
            user=user,
            roles__in=self.site_roles,
            is_active=True,
            site__is_active=True,
        ).exists():
            return user

        raise HttpError(403, "You do not have permission to perform this action")


class platformAdminOnly(RoleRequired):
    allow_platform_admin = True


class siteadminOnly(RoleRequired):
    allow_platform_admin = True
    site_roles = [Role.SITEADMIN]


class SupervisorOnly(RoleRequired):
    allow_platform_admin = True
    site_roles = [Role.SITEADMIN, Role.SUPERVISORS]


class WorkerOnly(RoleRequired):
    allow_platform_admin = True
    site_roles = [Role.SITEADMIN, Role.SUPERVISORS, Role.WORKER]
    


def allowed_roles(admin):
    if admin.organisation is None:
        return []
    if admin.is_platform_admin:
        return [Role.PLATFORM_ADMIN, Role.SITEADMIN, Role.SUPERVISORS, Role.WORKER]
    is_site_admin = SiteLinks.objects.filter(
        user=admin, roles=Role.SITEADMIN, is_active=True
    ).exists()
    if is_site_admin:
        return [Role.SUPERVISORS, Role.WORKER]
    return []


def allowed_sites(admin):
    if admin.organisation is None:
        return Site.objects.none()
    sites = Site.objects.filter(organisation=admin.organisation, is_active=True)
    if admin.is_platform_admin:
        return sites
    site_ids = SiteLinks.objects.filter(
        user=admin, roles=Role.SITEADMIN, is_active=True
    ).values_list("site_id", flat=True)
    return sites.filter(id__in=site_ids)