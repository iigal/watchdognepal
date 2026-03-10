from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class PoliticalParty(models.Model):
    name = models.CharField(max_length=200)
    in_government = models.BooleanField(default=False, help_text="Is this party currently in government?")
    description = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='party_logos/', blank=True, null=True)

    def __str__(self):
        return self.name

class ElectedMember(models.Model):
    name = models.CharField(max_length=200)
    constituency = models.CharField(max_length=200, help_text="e.g., Kathmandu-1")
    party = models.ForeignKey(PoliticalParty, on_delete=models.CASCADE, related_name='members')
    image = models.ImageField(upload_to='member_images/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.constituency})"

class ManifestoPoint(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    party = models.ForeignKey(PoliticalParty, on_delete=models.CASCADE, blank=True, null=True, related_name='manifesto_points')
    elected_member = models.ForeignKey(ElectedMember, on_delete=models.CASCADE, blank=True, null=True, related_name='manifesto_points')
    deadline = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if not self.party and not self.elected_member:
            raise ValidationError("A manifesto point must be linked to either a party or an elected member.")

    def __str__(self):
        return self.title

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
    manifesto_point = models.ForeignKey(ManifestoPoint, on_delete=models.SET_NULL, blank=True, null=True, related_name='activities')
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
