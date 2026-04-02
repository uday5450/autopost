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


class YouTubeAccount(models.Model):
    """Stores connected YouTube channel details and OAuth tokens."""
    
    name = models.CharField(max_length=255, help_text="YouTube Channel Name")
    channel_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="YouTube Channel ID"
    )
    access_token = models.TextField(
        blank=True,
        default='',
        help_text="Current OAuth2 access token"
    )
    refresh_token = models.TextField(
        blank=True,
        default='',
        help_text="OAuth2 refresh token (long-lived)"
    )
    token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the access token expires"
    )
    thumbnail_url = models.URLField(
        max_length=500,
        blank=True,
        default='',
        help_text="Channel thumbnail / avatar URL"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "YouTube Account"
        verbose_name_plural = "YouTube Accounts"

    def __str__(self):
        return f"{self.name} ({self.channel_id})"

    @property
    def token_status(self):
        """Returns the current token status.
        
        If a refresh_token is present, we can always auto-refresh,
        so the account is considered 'valid' even if the short-lived
        access_token has expired.
        """
        if not self.access_token and not self.refresh_token:
            return 'missing'
        # Has a refresh token → can always get a new access token
        if self.refresh_token:
            return 'valid'
        if not self.token_expires_at:
            return 'unknown'
        now = timezone.now()
        if self.token_expires_at <= now:
            return 'expired'
        return 'valid'


class ScheduledPost(models.Model):
    """Represents a scheduled post (Instagram Image/Reel or YouTube Video)."""
    
    PLATFORM_CHOICES = [
        ('INSTAGRAM', 'Instagram'),
        ('YOUTUBE', 'YouTube'),
    ]
    
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

    platform = models.CharField(
        max_length=15,
        choices=PLATFORM_CHOICES,
        default='INSTAGRAM',
        help_text="Target platform for this post"
    )

    # Instagram account — optional (only for Instagram posts)
    account = models.ForeignKey(
        InstagramAccount, 
        on_delete=models.CASCADE,
        related_name='posts',
        null=True,
        blank=True,
    )
    
    # YouTube account — optional (only for YouTube posts)
    youtube_account = models.ForeignKey(
        YouTubeAccount,
        on_delete=models.CASCADE,
        related_name='posts',
        null=True,
        blank=True,
    )

    # YouTube Advanced Settings
    YT_PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
        ('unlisted', 'Unlisted'),
    ]

    yt_privacy_status = models.CharField(
        max_length=10,
        choices=YT_PRIVACY_CHOICES,
        default='public',
        help_text="Privacy status for YouTube"
    )
    yt_tags = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text="Comma-separated tags for YouTube"
    )
    yt_category_id = models.CharField(
        max_length=10,
        default='22',
        help_text="YouTube Category ID (e.g. 22 for People & Blogs)"
    )
    yt_made_for_kids = models.BooleanField(
        default=False,
        help_text="Is this video made for kids?"
    )

    post_type = models.CharField(
        max_length=10, 
        choices=POST_TYPE_CHOICES, 
        default='IMAGE'
    )
    
    title = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Video title (required for YouTube)"
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
    yt_video_id = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Uploaded YouTube video ID"
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
        platform_str = self.get_platform_display()
        if self.platform == 'YOUTUBE':
            acct_name = self.youtube_account.name if self.youtube_account else 'No Account'
            return f"YouTube - {acct_name} - {self.scheduled_time}"
        acct_name = self.account.name if self.account else 'No Account'
        return f"{self.get_post_type_display()} - {acct_name} - {self.scheduled_time}"

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
