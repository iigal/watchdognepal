from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse

class PoliticalParty(models.Model):
    name = models.CharField(max_length=200)
    in_government = models.BooleanField(default=False, help_text="Is this party currently in government?")
    description = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='party_logos/', blank=True, null=True)
    oath_date = models.DateField(blank=True, null=True, help_text="Date the party/government took oath")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('party_detail', kwargs={'party_id': self.id})

class ElectedMember(models.Model):
    name = models.CharField(max_length=200)
    constituency = models.CharField(max_length=200, help_text="e.g., Kathmandu-1")
    party = models.ForeignKey(PoliticalParty, on_delete=models.CASCADE, related_name='members')
    image = models.ImageField(upload_to='member_images/', blank=True, null=True)
    oath_date = models.DateField(blank=True, null=True, help_text="Date the member took oath")
    
    # Contact Information
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    alternate_phone_number = models.CharField(max_length=15, blank=True, null=True)
    secretary_phone_number = models.CharField(max_length=15, blank=True, null=True)
    personal_email = models.EmailField(blank=True, null=True)
    office_email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.constituency})"

    def get_absolute_url(self):
        return reverse('elected_member_detail', kwargs={'member_id': self.id})

class ManifestoPoint(models.Model):
    CATEGORY_CHOICES = [
        ('economy', 'Economy & Finance'),
        ('infrastructure', 'Infrastructure & Development'),
        ('education', 'Education'),
        ('health', 'Health & Social Welfare'),
        ('governance', 'Governance & Administration'),
        ('environment', 'Environment & Climate'),
        ('agriculture', 'Agriculture & Rural Development'),
        ('technology', 'Technology & Innovation'),
        ('defense', 'Defense & Security'),
        ('foreign', 'Foreign Affairs'),
        ('rights', 'Rights & Justice'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other', blank=True)
    party = models.ForeignKey(PoliticalParty, on_delete=models.CASCADE, blank=True, null=True, related_name='manifesto_points')
    elected_member = models.ForeignKey(ElectedMember, on_delete=models.CASCADE, blank=True, null=True, related_name='manifesto_points')
    deadline = models.DateField(blank=True, null=True)
    completion_days = models.PositiveIntegerField(blank=True, null=True, help_text="Deadline in days from oath")
    completion_months = models.PositiveIntegerField(blank=True, null=True, help_text="Deadline in months from oath")
    completion_years = models.PositiveIntegerField(blank=True, null=True, help_text="Deadline in years from oath")
    is_completed = models.BooleanField(null=True, blank=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if not self.party and not self.elected_member:
            raise ValidationError("A manifesto point must be linked to either a party or an elected member.")

    @property
    def static_deadline(self):
        if self.deadline:
            return self.deadline
            
        base_date = None
        if self.elected_member and self.elected_member.oath_date:
            base_date = self.elected_member.oath_date
        elif self.party and self.party.oath_date:
            base_date = self.party.oath_date
            
        if base_date:
            from dateutil.relativedelta import relativedelta
            
            years = self.completion_years or 0
            months = self.completion_months or 0
            days = self.completion_days or 0
            
            if years > 0 or months > 0 or days > 0:
                return base_date + relativedelta(years=years, months=months, days=days)
                
        return None

    @property
    def calculated_deadline(self):
        base_deadline = self.static_deadline
        subs = self.sub_manifestos.all()
        if not subs.exists():
            return base_deadline

        from django.utils import timezone
        today = timezone.now().date()

        future_deadlines = [
            (sub.deadline or base_deadline) for sub in subs
            if sub.is_completed is None and (sub.deadline or base_deadline) and (sub.deadline or base_deadline) >= today
        ]
        if future_deadlines:
            return min(future_deadlines)

        uncompleted_deadlines = [
            (sub.deadline or base_deadline) for sub in subs
            if sub.is_completed is None and (sub.deadline or base_deadline)
        ]
        if uncompleted_deadlines:
            return max(uncompleted_deadlines)

        return base_deadline

    @property
    def is_partly_crossed(self):
        subs = self.sub_manifestos.all()
        if not subs.exists():
            return False
            
        from django.utils import timezone
        today = timezone.now().date()
        base_deadline = self.static_deadline
        
        has_overdue_uncompleted = any(
            sub.is_completed is None and (sub.deadline or base_deadline) and (sub.deadline or base_deadline) < today for sub in subs
        )
        has_future_uncompleted = any(
            sub.is_completed is None and (sub.deadline or base_deadline) and (sub.deadline or base_deadline) >= today for sub in subs
        )
        
        return has_overdue_uncompleted and has_future_uncompleted

    @property
    def is_overdue(self):
        if self.is_completed is not None:
            return False
        deadline = self.calculated_deadline
        if deadline:
            from django.utils import timezone
            return deadline < timezone.now().date()
        return False

    @property
    def progress_fraction(self):
        total = self.sub_manifestos.count()
        if total == 0:
            return "1/1" if self.is_completed is not None else "0/1"
        completed = self.sub_manifestos.filter(is_completed__isnull=False).count()
        return f"{completed}/{total}"

    @property
    def completion_percentage(self):
        total = self.sub_manifestos.count()
        if total == 0:
            return 100 if self.is_completed is not None else 0
        completed = self.sub_manifestos.filter(is_completed__isnull=False).count()
        return int((completed / total) * 100)

    @property
    def is_in_progress(self):
        if self.is_completed is not None:
            return False
        return self.completion_percentage > 0 or self.activities.filter(status='verified').exists()

    @property
    def top_5_verified_activities(self):
        return self.activities.filter(status='verified').order_by('-created_at')[:5]

    def __str__(self):
        return self.title

class SubManifesto(models.Model):
    parent = models.ForeignKey(ManifestoPoint, on_delete=models.CASCADE, related_name='sub_manifestos')
    title = models.CharField(max_length=200)
    deadline = models.DateField(blank=True, null=True)
    is_completed = models.BooleanField(null=True, blank=True, default=None)

    @property
    def effective_deadline(self):
        return self.deadline or self.parent.static_deadline

    @property
    def is_inherited_deadline(self):
        return self.deadline is None

    @property
    def is_overdue(self):
        if self.is_completed is not None:
            return False
        deadline = self.effective_deadline
        if deadline:
            from django.utils import timezone
            return deadline < timezone.now().date()
        return False

    def __str__(self):
        return f"{self.parent.title} - {self.title}"

class Commitment(models.Model):
    CATEGORY_CHOICES = ManifestoPoint.CATEGORY_CHOICES

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other', blank=True)
    party = models.ForeignKey(PoliticalParty, on_delete=models.CASCADE, blank=True, null=True, related_name='commitments')
    elected_member = models.ForeignKey(ElectedMember, on_delete=models.CASCADE, blank=True, null=True, related_name='commitments')
    deadline = models.DateField(blank=True, null=True)
    completion_days = models.PositiveIntegerField(blank=True, null=True, help_text="Deadline in days from oath")
    completion_months = models.PositiveIntegerField(blank=True, null=True, help_text="Deadline in months from oath")
    completion_years = models.PositiveIntegerField(blank=True, null=True, help_text="Deadline in years from oath")
    is_completed = models.BooleanField(null=True, blank=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if not self.party and not self.elected_member:
            raise ValidationError("A commitment must be linked to either a party or an elected member.")

    @property
    def static_deadline(self):
        if self.deadline:
            return self.deadline

        base_date = None
        if self.elected_member and self.elected_member.oath_date:
            base_date = self.elected_member.oath_date
        elif self.party and self.party.oath_date:
            base_date = self.party.oath_date

        if base_date:
            from dateutil.relativedelta import relativedelta

            years = self.completion_years or 0
            months = self.completion_months or 0
            days = self.completion_days or 0

            if years > 0 or months > 0 or days > 0:
                return base_date + relativedelta(years=years, months=months, days=days)

        return None

    @property
    def calculated_deadline(self):
        base_deadline = self.static_deadline
        subs = self.sub_commitments.all()
        if not subs.exists():
            return base_deadline

        from django.utils import timezone
        today = timezone.now().date()

        future_deadlines = [
            (sub.deadline or base_deadline) for sub in subs
            if sub.is_completed is None and (sub.deadline or base_deadline) and (sub.deadline or base_deadline) >= today
        ]
        if future_deadlines:
            return min(future_deadlines)

        uncompleted_deadlines = [
            (sub.deadline or base_deadline) for sub in subs
            if sub.is_completed is None and (sub.deadline or base_deadline)
        ]
        if uncompleted_deadlines:
            return max(uncompleted_deadlines)

        return base_deadline

    @property
    def is_partly_crossed(self):
        subs = self.sub_commitments.all()
        if not subs.exists():
            return False
            
        from django.utils import timezone
        today = timezone.now().date()
        base_deadline = self.static_deadline
        
        has_overdue_uncompleted = any(
            sub.is_completed is None and (sub.deadline or base_deadline) and (sub.deadline or base_deadline) < today for sub in subs
        )
        has_future_uncompleted = any(
            sub.is_completed is None and (sub.deadline or base_deadline) and (sub.deadline or base_deadline) >= today for sub in subs
        )
        
        return has_overdue_uncompleted and has_future_uncompleted

    @property
    def is_overdue(self):
        if self.is_completed is not None:
            return False
        deadline = self.calculated_deadline
        if deadline:
            from django.utils import timezone
            return deadline < timezone.now().date()
        return False

    @property
    def progress_fraction(self):
        total = self.sub_commitments.count()
        if total == 0:
            return "1/1" if self.is_completed is not None else "0/1"
        completed = self.sub_commitments.filter(is_completed__isnull=False).count()
        return f"{completed}/{total}"

    @property
    def completion_percentage(self):
        total = self.sub_commitments.count()
        if total == 0:
            return 100 if self.is_completed is not None else 0
        completed = self.sub_commitments.filter(is_completed__isnull=False).count()
        return int((completed / total) * 100)

    @property
    def is_in_progress(self):
        if self.is_completed is not None:
            return False
        return self.completion_percentage > 0 or self.activities.filter(status='verified').exists()

    @property
    def top_5_verified_activities(self):
        return self.activities.filter(status='verified').order_by('-created_at')[:5]

    def __str__(self):
        return self.title

class SubCommitment(models.Model):
    parent = models.ForeignKey(Commitment, on_delete=models.CASCADE, related_name='sub_commitments')
    title = models.CharField(max_length=200)
    deadline = models.DateField(blank=True, null=True)
    is_completed = models.BooleanField(null=True, blank=True, default=None)

    @property
    def effective_deadline(self):
        return self.deadline or self.parent.static_deadline

    @property
    def is_inherited_deadline(self):
        return self.deadline is None

    @property
    def is_overdue(self):
        if self.is_completed is not None:
            return False
        deadline = self.effective_deadline
        if deadline:
            from django.utils import timezone
            return deadline < timezone.now().date()
        return False

    def __str__(self):
        return f"{self.parent.title} - {self.title}"

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
    commitment = models.ForeignKey(Commitment, on_delete=models.SET_NULL, blank=True, null=True, related_name='activities')
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


class Petition(models.Model):
    CATEGORY_CHOICES = [
        ('governance', 'Governance'),
        ('infrastructure', 'Infrastructure'),
        ('education', 'Education'),
        ('health', 'Health'),
        ('environment', 'Environment'),
        ('rights', 'Rights'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('achieved', 'Achieved'),
    ]

    title = models.CharField(max_length=300)
    description = models.TextField()
    target = models.CharField(max_length=300, help_text="Who is this petition addressed to? e.g., Ministry of Education")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    goal = models.PositiveIntegerField(help_text="Target number of signatures")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='petitions')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    image = models.ImageField(upload_to='petition_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def signature_count(self):
        return self.signatures.count()

    @property
    def progress_percentage(self):
        if self.goal <= 0:
            return 0
        return min(100, int((self.signature_count / self.goal) * 100))

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('petition_detail', kwargs={'petition_id': self.id})

    class Meta:
        ordering = ['-created_at']


class PetitionSignature(models.Model):
    petition = models.ForeignKey(Petition, on_delete=models.CASCADE, related_name='signatures')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='petition_signatures')
    comment = models.TextField(blank=True, null=True, help_text="Optional: Why do you support this petition?")
    signed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('petition', 'user')
        ordering = ['-signed_at']

    def __str__(self):
        return f"{self.user.username} signed {self.petition.title}"

class IPLocationCache(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ip_address} - {self.city}, {self.country}"

class VisitorLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True, null=True)
    ip_address = models.GenericIPAddressField()
    path = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    browser = models.CharField(max_length=50, blank=True, null=True)
    os_name = models.CharField(max_length=50, blank=True, null=True)
    device_type = models.CharField(max_length=20, blank=True, null=True)
    status_code = models.PositiveIntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    @property
    def visitor_type(self):
        if self.user:
            return "Registered"
        if self.device_type == "Bot":
            return "Bot"
        return "Guest"

    def __str__(self):
        return f"{self.ip_address} visited {self.path} at {self.timestamp}"

class BannedIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    reason = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Banned: {self.ip_address}"

    class Meta:
        verbose_name = "Banned IP"
        verbose_name_plural = "Banned IPs"
