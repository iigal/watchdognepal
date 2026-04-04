"""
Management command to publish approved social posts.
Designed to be run via cPanel cron job every 5 minutes:

    */5 * * * * cd /path/to/watchdognepal.com && python manage.py publish_approved_posts
"""
from django.core.management.base import BaseCommand
from social.models import SocialPost
from social.publishers import publish_post


class Command(BaseCommand):
    help = 'Publishes all approved social posts to Instagram, Facebook, and Twitter/X.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which posts would be published without actually publishing.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='Maximum number of posts to publish per run (default: 5).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        
        posts = SocialPost.objects.filter(status='approved').order_by('approved_at')[:limit]
        
        if not posts.exists():
            self.stdout.write(self.style.SUCCESS('No approved posts waiting to be published.'))
            return
        
        self.stdout.write(f"Found {posts.count()} approved post(s) to publish.")
        
        success_count = 0
        error_count = 0
        
        for post in posts:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Post #{post.pk}: {post.title}")
            self.stdout.write(f"Type: {post.get_post_type_display()}")
            self.stdout.write(f"Author: {post.created_by.username}")
            
            if not post.is_publishable:
                self.stdout.write(self.style.WARNING(f"  ⚠ Skipping — no publishable media."))
                error_count += 1
                continue
            
            if dry_run:
                self.stdout.write(self.style.WARNING(f"  [DRY RUN] Would publish this post."))
                continue
            
            success, error = publish_post(post)
            
            if success:
                platforms = ', '.join(post.publish_targets) or 'none'
                self.stdout.write(self.style.SUCCESS(f"  ✅ Published to: {platforms}"))
                success_count += 1
            else:
                self.stdout.write(self.style.ERROR(f"  ❌ Failed: {error}"))
                error_count += 1
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(
            self.style.SUCCESS(f"Done. {success_count} published, {error_count} failed.")
        )
