from django.core.cache import cache


def sidebar_context(request):
    """Provide sidebar stats available on all pages."""
    sidebar_data = cache.get('sidebar_stats')
    if sidebar_data is None:
        from .models import ManifestoPoint, Commitment, Petition, PoliticalParty, ElectedMember, Activity
        sidebar_data = {
            'sidebar_manifesto_count': ManifestoPoint.objects.count(),
            'sidebar_commitment_count': Commitment.objects.count(),
            'sidebar_petition_count': Petition.objects.filter(status='active').count(),
            'sidebar_party_count': PoliticalParty.objects.count(),
            'sidebar_member_count': ElectedMember.objects.count(),
            'recent_activities': Activity.objects.select_related('created_by').order_by('-created_at')[:10],
            'all_recent_activities': Activity.objects.select_related('created_by').order_by('-created_at')[:30],
        }
        # Reduced cache time for more frequent updates of "Recent Activities"
        cache.set('sidebar_stats', sidebar_data, 60 * 5)  # 5 minutes
    return sidebar_data
