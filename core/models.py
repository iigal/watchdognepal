from django.db import models
from django.contrib.auth.models import User

class Activity(models.Model):
    LEVEL_CHOICES = [
        ('federal', 'Federal'),
        ('provincial', 'Provincial'),
        ('local', 'Local'),
    ]

    STATUS_CHOICES = [
        ('unverified', 'Unverified'),
        ('verified', 'Verified'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    province = models.CharField(max_length=50, blank=True, null=True)
    source_link = models.URLField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='unverified')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    positive_votes = models.PositiveIntegerField(default=0)
    negative_votes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.title} ({self.get_level_display()})"

    class Meta:
        ordering = ['-created_at']

class Vote(models.Model):
    VOTE_TYPES = [
        ('up', 'Upvote'),
        ('down', 'Downvote'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='votes')
    vote_type = models.CharField(max_length=10, choices=VOTE_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'activity')  # prevents multiple votes per activity

    def __str__(self):
        return f"{self.user.username} voted {self.vote_type} on {self.activity.title}"
