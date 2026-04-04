"""
Gamification Engine for Watchdog Nepal
=======================================
Handles XP awards, level-ups, and dynamic verification access calculations.
All access checks are done via @property methods on UserProfile so they
work without Celery or background tasks.
"""
from django.utils import timezone

# ── Level Titles ──────────────────────────────────────────────────────
LEVEL_TITLES = {
    1: "Starter",
    2: "Observer",
    3: "Reporter",
    4: "Investigator",
    5: "Contributor",
    6: "Analyst",
    7: "Advocate",
    8: "Strategist",
    9: "Influencer",
    10: "Watchdog",
    11: "Inspector",
    12: "Enforcer",
    13: "Champion",
    14: "Commander",
    15: "Guardian",
    16: "Protector",
    17: "Vanguard",
    18: "Architect",
    19: "Legend",
    20: "Sentinel",
}

def get_level_title(level):
    """Returns the title for a given level, defaulting to 'Sentinel' for 20+."""
    if level >= 20:
        return LEVEL_TITLES[20]
    return LEVEL_TITLES.get(level, "Starter")


# ── XP Constants ──────────────────────────────────────────────────────
XP_ACTIVITY_SUBMITTED = 5
XP_ACTIVITY_VERIFIED = 15
XP_SOCIAL_SUBMITTED = 5
XP_SOCIAL_APPROVED = 10
XP_VERIFIED_OTHERS_ACTIVITY = 10
XP_PETITION_CREATED = 5


def xp_for_level(level):
    """XP required to reach the next level from the current one."""
    return level * 50


# ── Core Functions ────────────────────────────────────────────────────
def award_xp(user, amount, reason=""):
    """
    Awards XP to a user, checks for level-ups, and logs the action.
    
    Args:
        user: Django User instance
        amount: Integer XP to award
        reason: String description for the activity log
    
    Returns:
        tuple: (new_xp, leveled_up: bool, new_level)
    """
    from accounts.models import UserProfile, UserActivityLog

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.xp += amount
    leveled_up = False
    
    # Check for level-up(s) — a user could gain multiple levels at once
    while profile.xp >= xp_for_level(profile.level):
        profile.xp -= xp_for_level(profile.level)
        profile.level += 1
        leveled_up = True
        
        # Log level-up
        UserActivityLog.objects.create(
            user=user,
            action='level_up',
            description=f"Reached Level {profile.level}: {get_level_title(profile.level)}",
            xp_change=0,
            metadata={'new_level': profile.level, 'title': get_level_title(profile.level)}
        )
    
    profile.save()
    
    # Log XP gain
    if reason:
        UserActivityLog.objects.create(
            user=user,
            action='xp_earned',
            description=reason,
            xp_change=amount,
            metadata={'total_xp': profile.xp, 'level': profile.level}
        )
    
    return profile.xp, leveled_up, profile.level


def check_verification_access(profile):
    """
    Determines if a user has dynamic verification access based on their
    level and recent activity count. Called by UserProfile.has_verification_access.
    
    Returns:
        bool: Whether the user currently has verification access
    """
    from core.models import Activity
    
    # Manual override takes precedence
    if profile.verification_access_override:
        return profile.can_verify_activities
    
    user = profile.user
    now = timezone.now()
    level = profile.level
    
    # Determine required activity count and rolling window based on level
    if level >= 15:
        required_count = 15
        window_days = 365  # 1 year
    elif level >= 10:
        required_count = 10
        window_days = 180  # 6 months
    elif level >= 5:
        required_count = 5
        window_days = 90   # 3 months
    else:
        required_count = 5
        window_days = 30   # 30 days
    
    cutoff = now - timezone.timedelta(days=window_days)
    
    # Count activities this user has:
    # 1. Submitted and got verified
    submitted_verified = Activity.objects.filter(
        created_by=user,
        status='verified',
        created_at__gte=cutoff
    ).count()
    
    # 2. Verified for others (tracked in UserActivityLog)
    from accounts.models import UserActivityLog
    verified_others = UserActivityLog.objects.filter(
        user=user,
        action='activity_approved_by',
        created_at__gte=cutoff
    ).count()
    
    total = submitted_verified + verified_others
    return total >= required_count
