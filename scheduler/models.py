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


class LinkedInAccount(models.Model):
    """Stores connected LinkedIn profile or company page details and tokens."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='linkedin_accounts', null=True, blank=True)
    name = models.CharField(max_length=255, help_text="LinkedIn Name or Page Name")
    urn_id = models.CharField(max_length=100, unique=True, help_text="LinkedIn URN / ID (e.g. person:123 or organization:456)")
    access_token = models.TextField(blank=True, default='', help_text="LinkedIn access token")
    refresh_token = models.TextField(blank=True, default='', help_text="LinkedIn refresh token")
    token_expires_at = models.DateTimeField(null=True, blank=True)
    profile_picture_url = models.URLField(max_length=500, blank=True, default='', help_text="Profile picture URL")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "LinkedIn Account"
        verbose_name_plural = "LinkedIn Accounts"

    def __str__(self):
        return f"{self.name} ({self.urn_id})"

    @property
    def token_status(self):
        return 'valid' if self.access_token else 'missing'


class RedditAccount(models.Model):
    """Stores connected Reddit account details and tokens."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reddit_accounts', null=True, blank=True)
    name = models.CharField(max_length=255, help_text="Reddit Display Name")
    username = models.CharField(max_length=100, unique=True, help_text="Reddit u/username")
    default_subreddit = models.CharField(max_length=100, blank=True, default='u_me', help_text="Default target subreddit")
    access_token = models.TextField(blank=True, default='', help_text="Reddit access token")
    refresh_token = models.TextField(blank=True, default='', help_text="Reddit refresh token")
    token_expires_at = models.DateTimeField(null=True, blank=True)
    profile_picture_url = models.URLField(max_length=500, blank=True, default='', help_text="Avatar URL")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Reddit Account"
        verbose_name_plural = "Reddit Accounts"

    def __str__(self):
        return f"u/{self.username}"

    @property
    def token_status(self):
        return 'valid' if self.access_token else 'missing'


class SnapchatAccount(models.Model):
    """Stores connected Snapchat Public Profile details and tokens."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='snapchat_accounts', null=True, blank=True)
    name = models.CharField(max_length=255, help_text="Snapchat Display Name")
    profile_id = models.CharField(max_length=100, unique=True, help_text="Snapchat Public Profile ID")
    access_token = models.TextField(blank=True, default='', help_text="Snapchat access token")
    refresh_token = models.TextField(blank=True, default='', help_text="Snapchat refresh token")
    token_expires_at = models.DateTimeField(null=True, blank=True)
    profile_picture_url = models.URLField(max_length=500, blank=True, default='', help_text="Avatar URL")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Snapchat Account"
        verbose_name_plural = "Snapchat Accounts"

    def __str__(self):
        return f"{self.name} ({self.profile_id})"

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
        ('LINKEDIN', 'LinkedIn'),
        ('REDDIT', 'Reddit'),
        ('SNAPCHAT', 'Snapchat'),
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

    # LinkedIn account — optional
    linkedin_account = models.ForeignKey(
        LinkedInAccount,
        on_delete=models.CASCADE,
        related_name='posts',
        null=True,
        blank=True,
    )

    # Reddit account — optional
    reddit_account = models.ForeignKey(
        RedditAccount,
        on_delete=models.CASCADE,
        related_name='posts',
        null=True,
        blank=True,
    )

    # Snapchat account — optional
    snapchat_account = models.ForeignKey(
        SnapchatAccount,
        on_delete=models.CASCADE,
        related_name='posts',
        null=True,
        blank=True,
    )

    # Per-platform customizations (overrides)
    platform_customizations = models.JSONField(
        default=dict,
        blank=True,
        help_text="Customized per-platform overrides like custom caption, tags, titles"
    )

    # External live post URL
    external_post_url = models.URLField(
        max_length=1000,
        blank=True,
        default='',
        help_text="Direct public link to the published live post on the social network"
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
        elif self.platform == 'LINKEDIN':
            acct_name = self.linkedin_account.name if self.linkedin_account else 'No Account'
            return f"LinkedIn - {acct_name} - {self.scheduled_time}"
        elif self.platform == 'REDDIT':
            acct_name = self.reddit_account.name if self.reddit_account else 'No Account'
            return f"Reddit - {acct_name} - {self.scheduled_time}"
        elif self.platform == 'SNAPCHAT':
            acct_name = self.snapchat_account.name if self.snapchat_account else 'No Account'
            return f"Snapchat - {acct_name} - {self.scheduled_time}"
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


class PricingPlan(models.Model):
    """Dynamically manageable subscription plans configurable by superusers in Django Admin."""
    plan_code = models.CharField(max_length=50, unique=True, help_text="Unique code e.g. FREE, CREATOR, PRO, ENTERPRISE, CUSTOM")
    name = models.CharField(max_length=100, help_text="Display title e.g. Free Starter, Creator Pro, Agency & AI Scale")
    description = models.CharField(max_length=255, blank=True, help_text="Subtitle e.g. For active creators, influencers, and growing brands.")
    
    # Pricing & Discounts
    price_inr = models.PositiveIntegerField(default=0, help_text="Current price in Rupees (₹) e.g. 2499")
    original_price_inr = models.PositiveIntegerField(default=0, blank=True, null=True, help_text="Original price before discount for strike-through display e.g. 3499 (0 if no discount)")
    yearly_price_inr = models.PositiveIntegerField(default=0, blank=True, null=True, help_text="Total price for 1 full year in ₹. Leave 0 to auto-calculate with yearly discount percent.")
    yearly_discount_percent = models.PositiveIntegerField(default=20, help_text="Discount percentage for yearly billing (e.g. 20% OFF or 2 months free)")
    price_usd = models.CharField(max_length=50, blank=True, default="", help_text="Optional USD display string e.g. ($29)")
    billing_period = models.CharField(max_length=50, default="/ month", help_text="e.g. / month, / year")
    
    # Account & Post Limits
    max_connected_accounts = models.PositiveIntegerField(default=2, help_text="Maximum total social accounts user can connect (0 = unlimited)")
    price_per_additional_account = models.PositiveIntegerField(default=0, help_text="Price in ₹ per extra account connect beyond base limit (0 if disabled or unlimited)")
    max_posts_per_month = models.PositiveIntegerField(default=5, help_text="Maximum scheduled posts per month (0 = unlimited)")
    max_workspaces = models.PositiveIntegerField(default=1, help_text="Maximum workspaces user can create/own (0 = unlimited)")
    max_members_per_workspace = models.PositiveIntegerField(default=3, help_text="Maximum team members allowed per workspace (0 = unlimited)")
    
    # Badging & CTA
    is_featured = models.BooleanField(default=False, help_text="Highlight card with special border & purple glow")
    badge_text = models.CharField(max_length=50, blank=True, default="", help_text="Badge text e.g. MOST POPULAR, 30% OFF, LIMITED OFFER")
    cta_text = models.CharField(max_length=50, default="Choose Plan", help_text="Button text e.g. Upgrade to Creator")
    
    # Features List (newline separated: start with '!' for strong bold, '-' for strikethrough/disabled)
    features_list = models.TextField(
        help_text="One feature per line. Start with '!' for bold, or '-' for disabled. Example:\n!Unlimited Posts & Reels\nUp to 15 Connected Accounts\nPer-Platform Overrides & Previews\n-Visual Content Calendar"
    )
    
    # Custom plan builder flags
    is_custom_calculator = models.BooleanField(default=False, help_text="Enable dynamic accounts slider calculator for this plan")
    
    # Ordering & Visibility
    order = models.PositiveIntegerField(default=0, help_text="Display order on the pricing page (1, 2, 3...)")
    is_active = models.BooleanField(default=True, help_text="Only active plans are shown to users")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'price_inr']
        verbose_name = "Pricing Plan"
        verbose_name_plural = "Pricing Plans"

    def __str__(self):
        return f"{self.name} (₹{self.price_inr})"

    @property
    def discount_percent(self):
        if self.original_price_inr and self.original_price_inr > self.price_inr:
            return round(((self.original_price_inr - self.price_inr) / self.original_price_inr) * 100)
        return 0

    @property
    def amount_in_paise(self):
        return self.price_inr * 100

    @property
    def get_yearly_price_inr(self):
        """Returns total annual price in ₹. Auto-calculates with yearly_discount_percent if 0."""
        if self.price_inr == 0:
            return 0
        if self.yearly_price_inr and self.yearly_price_inr > 0:
            return self.yearly_price_inr
        full_annual = self.price_inr * 12
        discount = round((full_annual * self.yearly_discount_percent) / 100)
        return full_annual - discount

    @property
    def get_yearly_monthly_equivalent(self):
        """Returns the monthly cost when billed annually (e.g. ₹1,999/mo)."""
        if self.price_inr == 0:
            return 0
        return round(self.get_yearly_price_inr / 12)

    @property
    def get_yearly_amount_in_paise(self):
        return self.get_yearly_price_inr * 100

    @property
    def yearly_savings_inr(self):
        """Total ₹ saved per year compared to 12 months at regular price."""
        if self.price_inr == 0:
            return 0
        return (self.price_inr * 12) - self.get_yearly_price_inr

    def parsed_features(self):
        """Returns structured list of features: [{'text': str, 'is_bold': bool, 'is_disabled': bool}]"""
        features = []
        if not self.features_list:
            return features
        for line in self.features_list.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith('!'):
                features.append({'text': line[1:].strip(), 'is_bold': True, 'is_disabled': False})
            elif line.startswith('-'):
                features.append({'text': line[1:].strip(), 'is_bold': False, 'is_disabled': True})
            else:
                features.append({'text': line, 'is_bold': False, 'is_disabled': False})
        return features


class DiscountCoupon(models.Model):
    """Discount promo codes managed by superusers in Django Admin."""
    code = models.CharField(max_length=50, unique=True, help_text="Coupon code e.g. SAVE20, LAUNCH50, FLAT500")
    discount_percent = models.PositiveIntegerField(default=0, help_text="Percentage discount (0-100)%")
    discount_amount_inr = models.PositiveIntegerField(default=0, help_text="Flat rupee discount e.g. 500 (used if percent is 0)")
    max_uses = models.PositiveIntegerField(default=0, help_text="Maximum total redemptions (0 = unlimited)")
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    valid_until = models.DateTimeField(blank=True, null=True, help_text="Leave empty for never expiring")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Discount Coupon"
        verbose_name_plural = "Discount Coupons"

    def __str__(self):
        if self.discount_percent > 0:
            return f"{self.code} ({self.discount_percent}% OFF)"
        return f"{self.code} (₹{self.discount_amount_inr} OFF)"

    def is_valid(self):
        if not self.is_active:
            return False, "This coupon is no longer active."
        if self.valid_until and timezone.now() > self.valid_until:
            return False, "This coupon has expired."
        if self.max_uses > 0 and self.used_count >= self.max_uses:
            return False, "This coupon has reached its maximum redemptions."
        return True, "Coupon applied successfully!"

    def calculate_discount(self, original_price_inr):
        valid, _ = self.is_valid()
        if not valid or original_price_inr <= 0:
            return 0
        if self.discount_percent > 0:
            return round((original_price_inr * self.discount_percent) / 100)
        elif self.discount_amount_inr > 0:
            return min(self.discount_amount_inr, original_price_inr)
        return 0


class UserSubscription(models.Model):
    """User membership plan and billing details via Razorpay."""
    PLAN_CHOICES = [
        ('FREE', 'Free Starter (5 posts/mo)'),
        ('CREATOR', 'Creator ($29/mo - Unlimited)'),
        ('PRO', 'Pro / Agency ($99/mo - Unlimited + API)'),
        ('CUSTOM', 'Custom Plan'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=50, default='FREE')
    billing_cycle = models.CharField(max_length=20, default='MONTHLY', choices=[('MONTHLY', 'Monthly'), ('YEARLY', 'Yearly')])
    pricing_plan = models.ForeignKey(PricingPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions')
    connected_accounts_limit = models.PositiveIntegerField(default=2, help_text="0 = unlimited")
    posts_limit_per_month = models.PositiveIntegerField(default=5, help_text="0 = unlimited")
    workspaces_limit = models.PositiveIntegerField(default=1, help_text="Maximum workspaces user can create/own (0 = unlimited)")
    members_per_workspace_limit = models.PositiveIntegerField(default=3, help_text="Maximum members per workspace (0 = unlimited)")
    custom_accounts_purchased = models.PositiveIntegerField(default=0)
    discount_applied_inr = models.PositiveIntegerField(default=0)
    coupon_used = models.ForeignKey(DiscountCoupon, on_delete=models.SET_NULL, null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, default='')
    razorpay_payment_id = models.CharField(max_length=100, blank=True, default='')
    razorpay_signature = models.CharField(max_length=255, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_workspaces_limit(self):
        """Returns maximum workspaces user can create/own (0 = unlimited)."""
        if self.pricing_plan and self.pricing_plan.max_workspaces is not None:
            return self.pricing_plan.max_workspaces
        plan_code = (self.plan or 'FREE').upper()
        if plan_code in ('PRO', 'OPERATOR', 'CUSTOM', 'AGENCY'):
            return 10
        elif plan_code in ('CREATOR', 'MARKETER'):
            return 3
        return self.workspaces_limit or 1

    def get_members_limit(self):
        """Returns maximum team members allowed per workspace (0 = unlimited)."""
        if self.pricing_plan and self.pricing_plan.max_members_per_workspace is not None:
            return self.pricing_plan.max_members_per_workspace
        plan_code = (self.plan or 'FREE').upper()
        if plan_code in ('PRO', 'OPERATOR', 'CUSTOM', 'AGENCY'):
            return 25
        elif plan_code in ('CREATOR', 'MARKETER'):
            return 5
        return self.members_per_workspace_limit or 3

    def __str__(self):
        if self.pricing_plan:
            return f"{self.user.username} - {self.pricing_plan.name}"
        return f"{self.user.username} - {self.plan}"


class UserProfile(models.Model):
    """User profile storing details collected during signup/onboarding."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=255, blank=True, default='', help_text="User's full name")
    phone_number = models.CharField(max_length=35, blank=True, default='', help_text="Mobile / Phone number")
    country_code = models.CharField(max_length=15, blank=True, default='+91', help_text="Dialing code e.g. +91, +1")
    country_name = models.CharField(max_length=100, blank=True, default='India', help_text="Country name")
    onboarding_completed = models.BooleanField(default=False, help_text="Whether initial onboarding was completed")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name or self.user.username} ({self.country_code} {self.phone_number})"


class Workspace(models.Model):
    """Collaborative multi-user workspace for managing social accounts and scheduled posts."""
    name = models.CharField(max_length=100, help_text="Workspace display name")
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_workspaces')
    description = models.TextField(blank=True, default='', help_text="Optional workspace description")
    timezone = models.CharField(max_length=60, default='Asia/Kolkata', help_text="Workspace primary timezone")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Workspace'
        verbose_name_plural = 'Workspaces'

    def __str__(self):
        return f"{self.name} (Owner: {self.owner.username})"

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            import uuid
            base_slug = slugify(self.name) or f"ws-{self.owner_id or 'team'}"
            unique_slug = base_slug
            counter = 1
            while Workspace.objects.filter(slug=unique_slug).exclude(pk=self.pk).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)

    def get_user_role(self, user):
        """Returns the role string ('OWNER', 'ADMIN', 'EDITOR', 'VIEWER') or None."""
        if not user or not user.is_authenticated:
            return None
        if self.owner_id == user.id:
            return 'OWNER'
        membership = self.memberships.filter(user=user).first()
        return membership.role if membership else None

    def is_admin_or_owner(self, user):
        """True if user has administrative rights (Owner or Admin)."""
        role = self.get_user_role(user)
        return role in ('OWNER', 'ADMIN')

    def can_manage_content(self, user):
        """True if user can create, schedule, edit, or delete posts."""
        role = self.get_user_role(user)
        return role in ('OWNER', 'ADMIN', 'EDITOR')

    def get_members_count(self):
        # 1 for owner + total memberships (excluding owner if duplicate)
        return 1 + self.memberships.exclude(user=self.owner).count()


class WorkspaceMember(models.Model):
    """Team members assigned to a workspace with granular role-based permissions."""
    ROLE_CHOICES = [
        ('OWNER', 'Owner (Full ownership, billing & workspace deletion)'),
        ('ADMIN', 'Admin (Manage team, assign roles & all social publishing)'),
        ('EDITOR', 'Editor (Create, schedule & edit posts)'),
        ('VIEWER', 'Viewer (Read-only view of calendar, accounts & analytics)'),
    ]

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workspace_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='EDITOR')
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_workspace_invitations')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('workspace', 'user')
        ordering = ['joined_at']
        verbose_name = 'Workspace Member'
        verbose_name_plural = 'Workspace Members'

    def __str__(self):
        return f"{self.user.username} ({self.role}) in {self.workspace.name}"


