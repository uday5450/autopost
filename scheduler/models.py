from django.db import models
from django.utils import timezone


class InstagramAccount(models.Model):
    """Stores Instagram account credentials and token information."""
    
    name = models.CharField(max_length=255, help_text="Display name for this account")
    instagram_user_id = models.CharField(
        max_length=100, 
        blank=True,
        default='',
        help_text="Instagram User ID (auto-detected from token)"
    )
    app_id = models.CharField(max_length=255, help_text="Meta App ID")
    client_secret = models.CharField(max_length=255, help_text="Meta App Secret")
    access_token = models.TextField(
        blank=True, 
        default='',
        help_text="Current long-lived access token"
    )
    token_expires_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When the token expires"
    )
    token_last_refreshed = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Last token refresh time"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Instagram Account"
        verbose_name_plural = "Instagram Accounts"

    def __str__(self):
        return f"{self.name} (@{self.instagram_user_id})"

    @property
    def token_status(self):
        """Returns the current token status."""
        if not self.access_token:
            return 'missing'
        if not self.token_expires_at:
            return 'unknown'
        now = timezone.now()
        if self.token_expires_at <= now:
            return 'expired'
        days_left = (self.token_expires_at - now).days
        if days_left <= 7:
            return 'expiring'
        return 'valid'

    @property
    def token_days_remaining(self):
        """Returns days until token expires."""
        if not self.token_expires_at:
            return None
        delta = self.token_expires_at - timezone.now()
        return max(0, delta.days)


class ScheduledPost(models.Model):
    """Represents a scheduled Instagram post (Image or Reel)."""
    
    POST_TYPE_CHOICES = [
        ('IMAGE', 'Image'),
        ('REEL', 'Reel'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('PUBLISHED', 'Published'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    account = models.ForeignKey(
        InstagramAccount, 
        on_delete=models.CASCADE,
        related_name='posts'
    )
    post_type = models.CharField(
        max_length=10, 
        choices=POST_TYPE_CHOICES, 
        default='IMAGE'
    )
    caption = models.TextField(
        blank=True, 
        default='',
        help_text="Post caption/description"
    )
    
    # Media - either file upload or URL
    media_file = models.FileField(
        upload_to='posts/media/%Y/%m/',
        blank=True,
        null=True,
        help_text="Upload image (JPEG) or video (MP4/MOV)"
    )
    media_url = models.URLField(
        max_length=2000,
        blank=True,
        default='',
        help_text="Or provide a public URL to the media"
    )
    
    # Thumbnail for Reels
    thumbnail_file = models.FileField(
        upload_to='posts/thumbnails/%Y/%m/',
        blank=True,
        null=True,
        help_text="Upload reel cover/thumbnail image (JPEG)"
    )
    thumbnail_url = models.URLField(
        max_length=2000,
        blank=True,
        default='',
        help_text="Or provide a public URL to the thumbnail"
    )
    
    # Scheduling
    scheduled_time = models.DateTimeField(
        help_text="When to publish this post"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=15, 
        choices=STATUS_CHOICES, 
        default='PENDING'
    )
    ig_container_id = models.CharField(
        max_length=100, 
        blank=True, 
        default='',
        help_text="Instagram container ID from API"
    )
    ig_media_id = models.CharField(
        max_length=100, 
        blank=True, 
        default='',
        help_text="Published Instagram media ID"
    )
    error_message = models.TextField(
        blank=True, 
        default='',
        help_text="Error details if publishing failed"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-scheduled_time']
        verbose_name = "Scheduled Post"
        verbose_name_plural = "Scheduled Posts"

    def __str__(self):
        return f"{self.get_post_type_display()} - {self.account.name} - {self.scheduled_time}"

    def get_effective_media_url(self, request=None):
        """Returns the media URL to use - either the provided URL or built from the file."""
        if self.media_url:
            return self.media_url
        if self.media_file and request:
            return request.build_absolute_uri(self.media_file.url)
        return None

    def get_effective_thumbnail_url(self, request=None):
        """Returns the thumbnail URL to use."""
        if self.thumbnail_url:
            return self.thumbnail_url
        if self.thumbnail_file and request:
            return request.build_absolute_uri(self.thumbnail_file.url)
        return None
