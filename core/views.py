from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST


def home(request):
    level = request.GET.get('level')
    status = request.GET.get('status')
    sort = request.GET.get('sort', 'newest')

    activities = Activity.objects.all()

    if level:
        activities = activities.filter(level=level)
    if status:
        activities = activities.filter(status=status)

    if sort == 'positive':
        activities = activities.order_by('-positive_votes')
    elif sort == 'negative':
        activities = activities.order_by('-negative_votes')
    else:  # newest first
        activities = activities.order_by('-created_at')

    context = {
        'activities': activities,
    }
    return render(request, 'home.html', context)



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
