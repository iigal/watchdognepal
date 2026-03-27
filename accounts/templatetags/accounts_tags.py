from django import template
from accounts.models import UserProfile

register = template.Library()

@register.filter
def get_profile(user):
    """Safely get the UserProfile object for a user, or None if it doesn't exist."""
    if not user or user.is_anonymous:
        return None
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        # If the OneToOne relationship is broken or missing
        return None
    except AttributeError:
        # If user is None
        return None
