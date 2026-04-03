from django.core.cache import cache


def sidebar_context(request):
    """Provide sidebar stats available on all pages."""
    sidebar_data = cache.get('sidebar_stats')
    if sidebar_data is None:
        from .models import ManifestoPoint, Commitment, Petition, PoliticalParty, ElectedMember
        sidebar_data = {
            'sidebar_manifesto_count': ManifestoPoint.objects.count(),
            'sidebar_commitment_count': Commitment.objects.count(),
            'sidebar_petition_count': Petition.objects.filter(status='active').count(),
            'sidebar_party_count': PoliticalParty.objects.count(),
            'sidebar_member_count': ElectedMember.objects.count(),
        }
        cache.set('sidebar_stats', sidebar_data, 60 * 60)  # 1 hour
    return sidebar_data
