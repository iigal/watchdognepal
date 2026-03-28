from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import models
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Activity, ManifestoPoint, SubManifesto, PoliticalParty, ElectedMember, Vote, Petition, PetitionSignature
from .forms import ActivityForm, PetitionForm


def home(request):
    # Fetch all parties that are in government
    government_parties = PoliticalParty.objects.filter(in_government=True).prefetch_related('manifesto_points__activities')
    
    today = timezone.now().date()
    
    # Priority 1: In Progress — manifesto points with at least one verified activity
    in_progress_points = ManifestoPoint.objects.filter(
        models.Q(party__in_government=True) | models.Q(elected_member__party__in_government=True),
        activities__status='verified'
    ).select_related('party', 'elected_member', 'elected_member__party').distinct()

    in_progress_ids = set(in_progress_points.values_list('id', flat=True))

    # Priority 2: Approaching Deadlines — exclude items already shown in In Progress
    manifesto_points = ManifestoPoint.objects.filter(
        models.Q(party__in_government=True) | models.Q(elected_member__party__in_government=True)
    ).exclude(
        id__in=in_progress_ids
    ).select_related('party', 'elected_member', 'elected_member__party')
    
    upcoming_deadlines = []
    for point in manifesto_points:
        calc_deadline = point.calculated_deadline
        if calc_deadline and calc_deadline >= today:
            upcoming_deadlines.append(point)
            
    upcoming_deadlines.sort(key=lambda p: p.calculated_deadline)
    upcoming_deadlines = upcoming_deadlines[:5]

    # IDs to exclude from the bottom manifesto list (already shown above)
    deadline_ids = set(p.id for p in upcoming_deadlines)
    shown_ids = in_progress_ids | deadline_ids

    context = {
        'government_parties': government_parties,
        'upcoming_deadlines': upcoming_deadlines,
        'in_progress_points': in_progress_points,
        'shown_manifesto_ids': shown_ids,
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


@login_required
def submit_activity(request):
    if request.method == 'POST':
        form = ActivityForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.created_by = request.user
            activity.level = 'federal'
            activity.save()
            return redirect('home')
    else:
        form = ActivityForm()
    return render(request, 'submit_activity.html', {'form': form})

from django.views.decorators.http import require_GET

@require_GET
def get_manifesto_options(request):
    party_id = request.GET.get('party_id')
    member_id = request.GET.get('member_id')
    
    if not party_id:
        return JsonResponse({'manifestos': [], 'members': []})
        
    members_qs = ElectedMember.objects.filter(party_id=party_id)
    members = [{'id': m.id, 'name': m.name} for m in members_qs]
        
    qs = ManifestoPoint.objects.all()
    if member_id:
        qs = qs.filter(elected_member_id=member_id)
    else:
        qs = qs.filter(party_id=party_id, elected_member__isnull=True)
        
    manifestos = [{'id': m.id, 'title': m.title} for m in qs]
    return JsonResponse({'manifestos': manifestos, 'members': members})


@require_POST
@login_required
def vote_activity(request, activity_id):
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


# ─── Petition Views ───────────────────────────────────────────

def petition_list(request):
    petitions = Petition.objects.filter(status='active')
    
    # Search
    q = request.GET.get('q', '').strip()
    if q:
        petitions = petitions.filter(
            models.Q(title__icontains=q) | models.Q(description__icontains=q)
        )
    
    # Category filter
    category = request.GET.get('category', '')
    if category:
        petitions = petitions.filter(category=category)
    
    context = {
        'petitions': petitions,
        'search_query': q,
        'selected_category': category,
        'categories': Petition.CATEGORY_CHOICES,
    }
    return render(request, 'petition_list.html', context)


def petition_detail(request, petition_id):
    petition = get_object_or_404(Petition, id=petition_id)
    signatures = petition.signatures.select_related('user').order_by('-signed_at')[:20]
    has_signed = False
    if request.user.is_authenticated:
        has_signed = petition.signatures.filter(user=request.user).exists()
    
    context = {
        'petition': petition,
        'signatures': signatures,
        'has_signed': has_signed,
        'total_signatures': petition.signature_count,
    }
    return render(request, 'petition_detail.html', context)


@login_required
def petition_create(request):
    if request.method == 'POST':
        form = PetitionForm(request.POST, request.FILES)
        if form.is_valid():
            petition = form.save(commit=False)
            petition.created_by = request.user
            petition.save()
            messages.success(request, 'Your petition has been created successfully!')
            return redirect('petition_detail', petition_id=petition.id)
    else:
        form = PetitionForm()
    return render(request, 'petition_create.html', {'form': form})


@require_POST
@login_required
def petition_sign(request, petition_id):
    petition = get_object_or_404(Petition, id=petition_id)
    
    if petition.status != 'active':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'This petition is no longer active.'}, status=400)
        messages.error(request, 'This petition is no longer active.')
        return redirect('petition_detail', petition_id=petition.id)
    
    if petition.created_by == request.user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'You cannot sign your own petition.'}, status=400)
        messages.error(request, 'You cannot sign your own petition.')
        return redirect('petition_detail', petition_id=petition.id)
    
    # Check if already signed
    if PetitionSignature.objects.filter(petition=petition, user=request.user).exists():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'You have already signed this petition.'}, status=400)
        messages.info(request, 'You have already signed this petition.')
        return redirect('petition_detail', petition_id=petition.id)
    
    comment = request.POST.get('comment', '').strip()
    PetitionSignature.objects.create(
        petition=petition,
        user=request.user,
        comment=comment if comment else None,
    )
    
    # Check if goal achieved
    if petition.signature_count >= petition.goal:
        petition.status = 'achieved'
        petition.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'signature_count': petition.signature_count,
            'progress': petition.progress_percentage,
            'status': petition.status,
        })
    
    messages.success(request, 'Thank you for signing this petition!')
    return redirect('petition_detail', petition_id=petition.id)


# ─── Dashboard View ───────────────────────────────────────────

@login_required
def dashboard(request):
    my_petitions = Petition.objects.filter(created_by=request.user)
    signed_petitions = Petition.objects.filter(signatures__user=request.user).distinct()
    my_activities = Activity.objects.filter(created_by=request.user)
    
    context = {
        'my_petitions': my_petitions,
        'signed_petitions': signed_petitions,
        'my_activities': my_activities,
    }
    return render(request, 'dashboard.html', context)

# ─── Manifesto Views ──────────────────────────────────────────

def manifesto_list(request):
    manifestos = ManifestoPoint.objects.prefetch_related('sub_manifestos').select_related('party', 'elected_member', 'elected_member__party')
    return render(request, 'manifesto_list.html', {'manifestos': manifestos})


@require_POST
@login_required
def toggle_submanifesto_completion(request, pk):
    submanifesto = get_object_or_404(SubManifesto, pk=pk)
    submanifesto.is_completed = not submanifesto.is_completed
    submanifesto.save()
    
    # Check if all submanifestos are completed to potentially auto-complete the parent
    parent = submanifesto.parent
    all_completed = parent.sub_manifestos.filter(is_completed=False).count() == 0
    if all_completed != parent.is_completed:
        parent.is_completed = all_completed
        parent.save()
        
    return JsonResponse({
        'success': True,
        'is_completed': submanifesto.is_completed,
        'parent_progress': parent.progress_fraction,
        'parent_completed': parent.is_completed,
        'parent_percentage': parent.completion_percentage
    })
