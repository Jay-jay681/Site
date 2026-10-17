from accounts.models import Site, SiteLinks, Role
 
 
def operator_site(operator, site_id):
    """
    Returns the site object if the operator is allowed to see it, otherwise returns None.
    """
    # 1. Is the operator allowed to see this site?
    if operator.is_platform_admin:
        site = Site.objects.filter(
            id=site_id, organisation=operator.organisation, is_active=True
        ).first()
    else:
        works_here = SiteLinks.objects.filter(
            user=operator,
            site_id=site_id,
            is_active=True,
            roles__in=[Role.SUPERVISORS, Role.SITEADMIN],
        ).exists()
        site = Site.objects.filter(id=site_id, is_active=True).first() if works_here else None

    return site
