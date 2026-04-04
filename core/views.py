from django.shortcuts import render, redirect, get_object_or_404
from django.core.cache import cache
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import models
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Activity, ManifestoPoint, SubManifesto, Commitment, SubCommitment, PoliticalParty, ElectedMember, Vote, Petition, PetitionSignature
from .forms import ActivityForm, PetitionForm
from .og_image import generate_manifesto_og_image, generate_commitment_og_image


def home(request):
    # Fetch all parties that are in government
    government_parties = PoliticalParty.objects.filter(in_government=True).prefetch_related(
        'manifesto_points__activities', 'commitments__activities'
    )
    
    today = timezone.now().date()
    
    today = timezone.now().date()
    
    # Calculate dynamic stats for the hero section counters and donut chart
    all_points = list(ManifestoPoint.objects.filter(
        models.Q(party__in_government=True) | models.Q(elected_member__party__in_government=True)
    ).select_related('party', 'elected_member')) + list(Commitment.objects.filter(
        models.Q(party__in_government=True) | models.Q(elected_member__party__in_government=True)
    ).select_related('party', 'elected_member'))

    import datetime
    approaching_threshold = today + datetime.timedelta(days=90)
    
    total_manifesto_count = 0
    total_commitment_count = 0
    total_in_progress_count = 0
    total_completed_count = 0
    total_missed_count = 0
    total_approaching_count = 0

    from django.core.cache import cache

    # Fetch GitHub Commit Count via GitHub API to work in production without .git folder
    git_commit_count = cache.get('github_commit_count')
    if not git_commit_count:
        try:
            import urllib.request
            import re
            
            req = urllib.request.Request('https://api.github.com/repos/iigal/watchdognepal/commits?per_page=1')
            req.add_header('User-Agent', 'WatchdogNepal-Backend')
            with urllib.request.urlopen(req, timeout=3) as response:
                link_header = response.headers.get('Link')
                if link_header:
                    match = re.search(r'page=(\d+)>; rel="last"', link_header)
                    if match:
                        git_commit_count = match.group(1)
                else:
                    git_commit_count = "1"
                        
            if git_commit_count:
                cache.set('github_commit_count', git_commit_count, 3600)  # cache for 1 hour
        except Exception as e:
            print("Github API Error:", e)

    if not git_commit_count:
        # Fallback to local git if API fails (e.g. rate limit)
        import subprocess
        import os
        from django.conf import settings
        try:
            git_commit_count = subprocess.check_output(
                ['git', 'rev-list', '--count', 'HEAD'], 
                cwd=settings.BASE_DIR,
                stderr=subprocess.STDOUT
            ).decode('utf-8').strip()
        except Exception:
            git_commit_count = "N/A"
    from django.contrib.auth.models import User
    total_registered_users = User.objects.count()

    latest_dates = []
    latest_activity = Activity.objects.order_by('-created_at').first()
    if latest_activity:
        latest_dates.append(latest_activity.created_at)
        
    latest_commitment = Commitment.objects.order_by('-created_at').first()
    if latest_commitment:
        latest_dates.append(latest_commitment.created_at)
        
    last_updated_date = max(latest_dates) if latest_dates else None
    
    # Reload points with prefetch for activities to calculate unified stats
    all_gov_manifestos = ManifestoPoint.objects.filter(
        models.Q(party__in_government=True) | models.Q(elected_member__party__in_government=True)
    ).select_related('party', 'elected_member', 'elected_member__party').prefetch_related('activities', 'sub_manifestos')
    
    all_gov_commitments = Commitment.objects.filter(
        models.Q(party__in_government=True) | models.Q(elected_member__party__in_government=True)
    ).select_related('party', 'elected_member', 'elected_member__party').prefetch_related('activities', 'sub_commitments')
    
    all_points = list(all_gov_manifestos) + list(all_gov_commitments)
    
    in_progress_points = []
    in_progress_commitments = []
    
    upcoming_deadlines = []
    upcoming_commitment_deadlines = []

    for p in all_points:
        if isinstance(p, ManifestoPoint):
            total_manifesto_count += 1
        else:
            total_commitment_count += 1
            
        if p.is_completed:
            total_completed_count += 1
        else:
            has_verified_activity = any(a.status == 'verified' for a in p.activities.all())
            if has_verified_activity:
                total_in_progress_count += 1
                if isinstance(p, ManifestoPoint):
                    in_progress_points.append(p)
                else:
                    in_progress_commitments.append(p)
            elif p.is_overdue:
                total_missed_count += 1
            else:
                total_approaching_count += 1
                if isinstance(p, ManifestoPoint):
                    p.item_type = 'manifesto'
                    upcoming_deadlines.append(p)
                else:
                    p.item_type = 'commitment'
                    upcoming_commitment_deadlines.append(p)

    upcoming_deadlines.sort(key=lambda p: p.calculated_deadline if p.calculated_deadline else datetime.date.max)
    upcoming_commitment_deadlines.sort(key=lambda c: c.calculated_deadline if c.calculated_deadline else datetime.date.max)

    total_upcoming_manifesto = len(upcoming_deadlines)
    total_upcoming_commitment = len(upcoming_commitment_deadlines)

    mixed_upcoming_deadlines = upcoming_deadlines + upcoming_commitment_deadlines
    mixed_upcoming_deadlines.sort(key=lambda item: item.calculated_deadline if item.calculated_deadline else datetime.date.max)
    mixed_upcoming_deadlines = mixed_upcoming_deadlines[:10]

    # Calculate sets of IDs to exclude them from the party tabs (so we don't show duplicates)
    in_progress_ids = set(p.id for p in in_progress_points)
    deadline_ids = set(p.id for p in upcoming_deadlines[:5])
    shown_manifesto_ids = in_progress_ids | deadline_ids
    
    in_progress_commitment_ids = set(p.id for p in in_progress_commitments)
    commitment_deadline_ids = set(p.id for p in upcoming_commitment_deadlines[:5])
    shown_commitment_ids = in_progress_commitment_ids | commitment_deadline_ids
    
    total_upcoming_deadline_count = total_upcoming_manifesto + total_upcoming_commitment


    context = {
        'government_parties': government_parties,
        # Manifesto
        'upcoming_deadlines': upcoming_deadlines[:5],  # keeping for backwards comp or ID calculation
        'in_progress_points': in_progress_points,
        'shown_manifesto_ids': shown_manifesto_ids,
        # Commitment
        'upcoming_commitment_deadlines': upcoming_commitment_deadlines[:5],
        'in_progress_commitments': in_progress_commitments,
        'shown_commitment_ids': shown_commitment_ids,
        # Mixed Approach Array
        'mixed_upcoming_deadlines': mixed_upcoming_deadlines,
        # Counters
        'total_manifesto_count': total_manifesto_count,
        'total_commitment_count': total_commitment_count,
        'total_in_progress_count': total_in_progress_count,
        'total_completed_count': total_completed_count,
        'total_missed_count': total_missed_count,
        'total_approaching_count': total_approaching_count,
        'git_commit_count': git_commit_count,
        'total_registered_users': total_registered_users,
        'last_updated_date': last_updated_date,
        'total_upcoming_deadline_count': total_upcoming_deadline_count,
    }
    return render(request, 'home.html', context)


def activities_list(request):
    level = request.GET.get('level')
    status = request.GET.get('status')
    sort = request.GET.get('sort', 'newest')

    activities = Activity.objects.select_related(
        'manifesto_point__party', 'manifesto_point__elected_member',
        'commitment__party', 'commitment__elected_member',
        'created_by'
    )

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

    paginator = Paginator(activities, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    all_activities = Activity.objects.all()
    context = {
        'activities': page_obj,
        'page_obj': page_obj,
        'total_count': all_activities.count(),
        'verified_count': all_activities.filter(status='verified').count(),
        'unverified_count': all_activities.filter(status='unverified').count(),
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
        return JsonResponse({'manifestos': [], 'commitments': [], 'members': []})
        
    members_qs = ElectedMember.objects.filter(party_id=party_id)
    members = [{'id': m.id, 'name': m.name} for m in members_qs]
        
    # Manifesto points
    m_qs = ManifestoPoint.objects.all()
    if member_id:
        m_qs = m_qs.filter(elected_member_id=member_id)
    else:
        m_qs = m_qs.filter(party_id=party_id, elected_member__isnull=True)
        
    manifestos = [{'id': m.id, 'title': m.title} for m in m_qs]

    # Commitments
    c_qs = Commitment.objects.all()
    if member_id:
        c_qs = c_qs.filter(elected_member_id=member_id)
    else:
        c_qs = c_qs.filter(party_id=party_id, elected_member__isnull=True)

    commitments = [{'id': c.id, 'title': c.title} for c in c_qs]

    return JsonResponse({'manifestos': manifestos, 'commitments': commitments, 'members': members})


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
    parties = PoliticalParty.objects.all().order_by('name')
    q = request.GET.get('q', '').strip()
    if q:
        parties = parties.filter(
            models.Q(name__icontains=q) | models.Q(description__icontains=q)
        )
    paginator = Paginator(parties, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'party_list.html', {'parties': page_obj, 'page_obj': page_obj, 'search_query': q})


def party_detail(request, party_id):
    party = get_object_or_404(PoliticalParty, id=party_id)
    manifesto_points = party.manifesto_points.all().prefetch_related('activities')
    commitments = party.commitments.all().prefetch_related('activities')
    return render(request, 'party_detail.html', {
        'party': party,
        'manifesto_points': manifesto_points,
        'commitments': commitments,
    })


def elected_member_list(request):
    members = ElectedMember.objects.all().select_related('party').order_by('name')
    q = request.GET.get('q', '').strip()
    if q:
        members = members.filter(
            models.Q(name__icontains=q) | models.Q(constituency__icontains=q) | models.Q(party__name__icontains=q)
        )
    paginator = Paginator(members, 16)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Parliament composition stats
    party_stats = PoliticalParty.objects.annotate(
        member_count=models.Count('members')
    ).filter(member_count__gt=0).order_by('-member_count')

    total_members = ElectedMember.objects.count()
    party_stat_list = []
    colors = ['#b1002c', '#335ab4', '#705d00', '#15803d', '#7c3aed', '#ea580c', '#0891b2', '#be185d', '#4f46e5', '#059669']
    for i, party in enumerate(party_stats):
        party_stat_list.append({
            'party': party,
            'count': party.member_count,
            'percentage': round((party.member_count / total_members) * 100, 1) if total_members else 0,
            'color': colors[i % len(colors)],
        })

    return render(request, 'member_list.html', {
        'members': page_obj,
        'page_obj': page_obj,
        'search_query': q,
        'party_stats': party_stat_list,
        'total_member_count': total_members,
    })


def elected_member_detail(request, member_id):
    member = get_object_or_404(ElectedMember, id=member_id)
    manifesto_points = member.manifesto_points.all().prefetch_related('activities')
    commitments = member.commitments.all().prefetch_related('activities')
    return render(request, 'member_detail.html', {
        'member': member,
        'manifesto_points': manifesto_points,
        'commitments': commitments,
    })


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
    
    paginator = Paginator(petitions, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'petitions': page_obj,
        'page_obj': page_obj,
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
    manifestos = ManifestoPoint.objects.filter(
        models.Q(party__in_government=True) | models.Q(elected_member__party__in_government=True)
    ).prefetch_related('sub_manifestos').select_related('party', 'elected_member', 'elected_member__party').order_by('-created_at')

    q = request.GET.get('q', '').strip()
    if q:
        manifestos = manifestos.filter(
            models.Q(title__icontains=q) | models.Q(description__icontains=q)
        )

    category = request.GET.get('category', '')
    if category:
        manifestos = manifestos.filter(category=category)

    status_filter = request.GET.get('status', '')
    if status_filter == 'completed':
        manifestos = manifestos.filter(is_completed=True)
    elif status_filter == 'overdue':
        manifestos = [m for m in manifestos if m.is_overdue]
    elif status_filter == 'in_progress':
        manifestos = [m for m in manifestos if not m.is_completed and not m.is_overdue]

    paginator = Paginator(manifestos, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Stats for the page
    all_manifestos = ManifestoPoint.objects.filter(
        models.Q(party__in_government=True) | models.Q(elected_member__party__in_government=True)
    )
    total_count = all_manifestos.count()
    completed_count = all_manifestos.filter(is_completed=True).count()

    return render(request, 'manifesto_list.html', {
        'manifestos': page_obj,
        'page_obj': page_obj,
        'search_query': q,
        'selected_category': category,
        'selected_status': status_filter,
        'categories': ManifestoPoint.CATEGORY_CHOICES,
        'total_count': total_count,
        'completed_count': completed_count,
        'in_progress_count': total_count - completed_count,
    })


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

def manifesto_detail(request, pk):
    manifesto = get_object_or_404(
        ManifestoPoint.objects.select_related('party', 'elected_member', 'elected_member__party')
        .prefetch_related('sub_manifestos', 'activities'),
        pk=pk
    )
    context = {
        'manifesto': manifesto,
        'sub_manifestos': manifesto.sub_manifestos.all(),
        'activities': manifesto.activities.filter(status='verified').order_by('-created_at')[:10],
    }
    return render(request, 'manifesto_detail.html', context)

def manifesto_og_image(request, pk):
    point = get_object_or_404(ManifestoPoint, pk=pk)
    img = generate_manifesto_og_image(point)
    
    response = HttpResponse(content_type="image/png")
    # Add simple cache control to prevent excessive generation
    response['Cache-Control'] = 'public, max-age=3600'
    img.save(response, "PNG")
    return response

# ─── Commitment Views ─────────────────────────────────────────

def commitment_list(request):
    commitments = Commitment.objects.filter(
        models.Q(party__in_government=True) | models.Q(elected_member__party__in_government=True)
    ).prefetch_related('sub_commitments').select_related('party', 'elected_member', 'elected_member__party').order_by('-created_at')

    q = request.GET.get('q', '').strip()
    if q:
        commitments = commitments.filter(
            models.Q(title__icontains=q) | models.Q(description__icontains=q)
        )

    category = request.GET.get('category', '')
    if category:
        commitments = commitments.filter(category=category)

    paginator = Paginator(commitments, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    all_commitments = Commitment.objects.filter(
        models.Q(party__in_government=True) | models.Q(elected_member__party__in_government=True)
    )
    total_count = all_commitments.count()
    completed_count = all_commitments.filter(is_completed=True).count()

    return render(request, 'commitment_list.html', {
        'commitments': page_obj,
        'page_obj': page_obj,
        'search_query': q,
        'selected_category': category,
        'categories': Commitment.CATEGORY_CHOICES,
        'total_count': total_count,
        'completed_count': completed_count,
        'in_progress_count': total_count - completed_count,
    })


@require_POST
@login_required
def toggle_subcommitment_completion(request, pk):
    subcommitment = get_object_or_404(SubCommitment, pk=pk)
    subcommitment.is_completed = not subcommitment.is_completed
    subcommitment.save()
    
    parent = subcommitment.parent
    all_completed = parent.sub_commitments.filter(is_completed=False).count() == 0
    if all_completed != parent.is_completed:
        parent.is_completed = all_completed
        parent.save()
        
    return JsonResponse({
        'success': True,
        'is_completed': subcommitment.is_completed,
        'parent_progress': parent.progress_fraction,
        'parent_completed': parent.is_completed,
        'parent_percentage': parent.completion_percentage
    })

def commitment_detail(request, pk):
    commitment = get_object_or_404(
        Commitment.objects.select_related('party', 'elected_member', 'elected_member__party')
        .prefetch_related('sub_commitments', 'activities'),
        pk=pk
    )
    context = {
        'commitment': commitment,
        'sub_commitments': commitment.sub_commitments.all(),
        'activities': commitment.activities.filter(status='verified').order_by('-created_at')[:10],
    }
    return render(request, 'commitment_detail.html', context)

def commitment_og_image(request, pk):
    commitment = get_object_or_404(Commitment, pk=pk)
    img = generate_commitment_og_image(commitment)
    
    response = HttpResponse(content_type="image/png")
    response['Cache-Control'] = 'public, max-age=3600'
    img.save(response, "PNG")
    return response
