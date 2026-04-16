from django.core.cache import cache
from django.db.models import Q


def sidebar_context(request):
    """Provide sidebar stats available on all pages."""
    sidebar_data = cache.get('sidebar_stats')
    if sidebar_data is None:
        from .models import ManifestoPoint, Commitment, Petition, PoliticalParty, ElectedMember, Activity

        # Filter: only count manifestos/commitments linked to parties in government
        govt_filter = Q(party__in_government=True) | Q(elected_member__party__in_government=True)

        govt_manifesto_count = ManifestoPoint.objects.filter(govt_filter).count()
        govt_commitment_count = Commitment.objects.filter(govt_filter).count()
        total_manifesto_count = ManifestoPoint.objects.count()
        total_commitment_count = Commitment.objects.count()

        sidebar_data = {
            'sidebar_manifesto_count': govt_manifesto_count,
            'sidebar_manifesto_total': total_manifesto_count,
            'sidebar_commitment_count': govt_commitment_count,
            'sidebar_commitment_total': total_commitment_count,
            'sidebar_petition_count': Petition.objects.filter(status='active').count(),
            'sidebar_party_count': PoliticalParty.objects.count(),
            'sidebar_member_count': ElectedMember.objects.count(),
            'recent_activities': Activity.objects.select_related('created_by').order_by('-created_at')[:10],
            'all_recent_activities': Activity.objects.select_related('created_by').order_by('-created_at')[:30],
        }
        # Reduced cache time for more frequent updates of "Recent Activities"
        cache.set('sidebar_stats', sidebar_data, 60 * 5)  # 5 minutes
    return sidebar_data
