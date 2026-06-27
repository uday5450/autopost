from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User



class InstagramAccount(models.Model):
    """Stores Instagram account credentials and token information."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='instagram_accounts', null=True, blank=True)
    name = models.CharField(max_length=255, help_text="Display name for this account")
    instagram_user_id = models.CharField(
        max_length=100, 
        blank=True,
        default='',
        help_text="Instagram User ID (auto-detected from token)"
    )
    app_id = models.CharField(max_length=255, help_text="Meta App ID")
    client_secret = models.CharField(max_length=255, help_text="Meta App Secret")
    profile_picture_url = models.URLField(
        max_length=500, 
        blank=True, 
        default='',
        help_text="Instagram Profile Picture URL"
    )
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
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='youtube_accounts', null=True, blank=True)
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


class FacebookAccount(models.Model):
    """Stores connected Facebook page details and tokens."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='facebook_accounts', null=True, blank=True)
    name = models.CharField(max_length=255, help_text="Facebook Page Name")
    page_id = models.CharField(max_length=100, unique=True, help_text="Facebook Page ID")
    access_token = models.TextField(blank=True, default='', help_text="Page access token")
    profile_picture_url = models.URLField(max_length=500, blank=True, default='', help_text="Page avatar URL")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Facebook Account"
        verbose_name_plural = "Facebook Accounts"

    def __str__(self):
        return f"{self.name} ({self.page_id})"

    @property
    def token_status(self):
        return 'valid' if self.access_token else 'missing'


class XAccount(models.Model):
    """Stores connected X (Twitter) account details and tokens."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='x_accounts', null=True, blank=True)
    name = models.CharField(max_length=255, help_text="X Account Name")
    screen_name = models.CharField(max_length=100, unique=True, help_text="X Handle / @username")
    access_token = models.TextField(blank=True, default='', help_text="OAuth2 access token")
    refresh_token = models.TextField(blank=True, default='', help_text="OAuth2 refresh token")
    token_expires_at = models.DateTimeField(null=True, blank=True)
    profile_picture_url = models.URLField(max_length=500, blank=True, default='', help_text="Avatar URL")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "X Account"
        verbose_name_plural = "X Accounts"

    def __str__(self):
        return f"{self.name} (@{self.screen_name})"

    @property
    def token_status(self):
        return 'valid' if self.access_token else 'missing'


class PinterestAccount(models.Model):
    """Stores connected Pinterest board details and tokens."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pinterest_accounts', null=True, blank=True)
    name = models.CharField(max_length=255, help_text="Pinterest Username")
    board_name = models.CharField(max_length=255, help_text="Pinterest Board Name")
    access_token = models.TextField(blank=True, default='', help_text="Pinterest access token")
    profile_picture_url = models.URLField(max_length=500, blank=True, default='', help_text="Profile picture URL")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Pinterest Account"
        verbose_name_plural = "Pinterest Accounts"

    def __str__(self):
        return f"{self.name} - {self.board_name}"

    @property
    def token_status(self):
        return 'valid' if self.access_token else 'missing'


class TikTokAccount(models.Model):
    """Stores connected TikTok account details and tokens."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tiktok_accounts', null=True, blank=True)
    name = models.CharField(max_length=255, help_text="TikTok Display Name")
    username = models.CharField(max_length=100, unique=True, help_text="TikTok @username")
    access_token = models.TextField(blank=True, default='', help_text="TikTok access token")
    refresh_token = models.TextField(blank=True, default='', help_text="TikTok refresh token")
    token_expires_at = models.DateTimeField(null=True, blank=True)
    profile_picture_url = models.URLField(max_length=500, blank=True, default='', help_text="Avatar URL")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "TikTok Account"
        verbose_name_plural = "TikTok Accounts"

    def __str__(self):
        return f"{self.name} (@{self.username})"

    @property
    def token_status(self):
        return 'valid' if self.access_token else 'missing'



class ScheduledPost(models.Model):
    """Represents a scheduled post (Instagram Image/Reel or YouTube Video)."""
    
    PLATFORM_CHOICES = [
        ('INSTAGRAM', 'Instagram'),
        ('YOUTUBE', 'YouTube'),
        ('X', 'X (Twitter)'),
        ('FACEBOOK', 'Facebook Page'),
        ('PINTEREST', 'Pinterest'),
        ('TIKTOK', 'TikTok'),
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scheduled_posts', null=True, blank=True)


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
    
    # Facebook Page account — optional
    facebook_account = models.ForeignKey(
        FacebookAccount,
        on_delete=models.CASCADE,
        related_name='posts',
        null=True,
        blank=True,
    )

    # X (Twitter) account — optional
    x_account = models.ForeignKey(
        XAccount,
        on_delete=models.CASCADE,
        related_name='posts',
        null=True,
        blank=True,
    )

    # Pinterest account — optional
    pinterest_account = models.ForeignKey(
        PinterestAccount,
        on_delete=models.CASCADE,
        related_name='posts',
        null=True,
        blank=True,
    )

    # TikTok account — optional
    tiktok_account = models.ForeignKey(
        TikTokAccount,
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
        elif self.platform == 'FACEBOOK':
            acct_name = self.facebook_account.name if self.facebook_account else 'No Account'
            return f"Facebook - {acct_name} - {self.scheduled_time}"
        elif self.platform == 'X':
            acct_name = self.x_account.name if self.x_account else 'No Account'
            return f"X - {acct_name} - {self.scheduled_time}"
        elif self.platform == 'PINTEREST':
            acct_name = self.pinterest_account.name if self.pinterest_account else 'No Account'
            return f"Pinterest - {acct_name} - {self.scheduled_time}"
        elif self.platform == 'TIKTOK':
            acct_name = self.tiktok_account.name if self.tiktok_account else 'No Account'
            return f"TikTok - {acct_name} - {self.scheduled_time}"
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
