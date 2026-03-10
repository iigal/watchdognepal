from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import models
from .models import Activity, ManifestoPoint, PoliticalParty

def home(request):
    # Fetch all parties that are in government
    government_parties = PoliticalParty.objects.filter(in_government=True).prefetch_related('manifesto_points__activities')
    
    # Optional: Still fetch upcoming deadlines for the top banner
    today = timezone.now().date()
    upcoming_deadlines = ManifestoPoint.objects.filter(
        models.Q(party__in_government=True) | models.Q(elected_member__party__in_government=True),
        deadline__gte=today
    ).order_by('deadline')[:5]

    context = {
        'government_parties': government_parties,
        'upcoming_deadlines': upcoming_deadlines,
    }
    return render(request, 'home.html', context)

def activities_list(request):
    level = request.GET.get('level')
    status = request.GET.get('status')
    sort = request.GET.get('sort', 'newest')

    activities = Activity.objects.all()

    if level and level != 'All':
        activities = activities.filter(level__iexact=level)
    if status and status != 'All':
        activities = activities.filter(status__iexact=status)

    if sort == 'Most Positive':
        activities = activities.order_by('-positive_votes')
    elif sort == 'Most Negative':
        activities = activities.order_by('-negative_votes')
    elif sort == 'Oldest':
        activities = activities.order_by('created_at')
    else:  # newest first
        activities = activities.order_by('-created_at')

    context = {
        'activities': activities,
    }
    return render(request, 'activities_list.html', context)

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from .forms import ActivityForm
from .models import Activity

@login_required
def submit_activity(request):
    if request.method == 'POST':
        form = ActivityForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.created_by = request.user
            activity.save()
            return redirect('home')
    else:
        form = ActivityForm()
    return render(request, 'submit_activity.html', {'form': form})

@require_POST
@login_required
def vote_activity(request, activity_id):
    from .models import Vote, Activity
    activity = Activity.objects.get(id=activity_id)
    vote_type = request.POST.get('vote_type')

    existing_vote = Vote.objects.filter(user=request.user, activity=activity).first()

    if existing_vote:
        # If same vote clicked again, remove it
        if existing_vote.vote_type == vote_type:
            existing_vote.delete()
        else:
            existing_vote.vote_type = vote_type
            existing_vote.save()
    else:
        Vote.objects.create(user=request.user, activity=activity, vote_type=vote_type)

    # Recalculate vote counts
    activity.positive_votes = Vote.objects.filter(activity=activity, vote_type='up').count()
    activity.negative_votes = Vote.objects.filter(activity=activity, vote_type='down').count()
    activity.save()

    return JsonResponse({
        'positive_votes': activity.positive_votes,
        'negative_votes': activity.negative_votes
    })


from django.shortcuts import render, get_object_or_404
from .models import PoliticalParty, ElectedMember

def party_list(request):
    parties = PoliticalParty.objects.all()
    return render(request, 'party_list.html', {'parties': parties})

def party_detail(request, party_id):
    party = get_object_or_404(PoliticalParty, id=party_id)
    # Get all manifesto points for this party
    manifesto_points = party.manifesto_points.all().prefetch_related('activities')
    return render(request, 'party_detail.html', {'party': party, 'manifesto_points': manifesto_points})

def elected_member_list(request):
    members = ElectedMember.objects.all().select_related('party')
    return render(request, 'member_list.html', {'members': members})

def elected_member_detail(request, member_id):
    member = get_object_or_404(ElectedMember, id=member_id)
    manifesto_points = member.manifesto_points.all().prefetch_related('activities')
    return render(request, 'member_detail.html', {'member': member, 'manifesto_points': manifesto_points})
