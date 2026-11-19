from django import forms
from django.utils import timezone
from django.contrib.auth.models import User

from .models import (
    InstagramAccount, ScheduledPost, YouTubeAccount,
    Workspace, WorkspaceMember
)


class InstagramAccountForm(forms.ModelForm):
    """Form for creating/editing an Instagram account."""
    
    short_lived_token = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Paste your access token here...',
            'class': 'form-input',
        }),
        required=False,
        help_text="Provide your access token. The app will auto-exchange and auto-detect your Instagram User ID."
    )
    
    class Meta:
        model = InstagramAccount
        fields = ['name', 'instagram_user_id', 'app_id', 'client_secret']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'e.g., My Business Account',
                'class': 'form-input',
            }),
            'instagram_user_id': forms.TextInput(attrs={
                'placeholder': 'Auto-detected from token (or enter manually)',
                'class': 'form-input',
            }),
            'app_id': forms.TextInput(attrs={
                'placeholder': 'Meta App ID',
                'class': 'form-input',
            }),
            'client_secret': forms.TextInput(attrs={
                'placeholder': 'Meta App Secret',
                'class': 'form-input',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make instagram_user_id not required (auto-detected)
        self.fields['instagram_user_id'].required = False
        
        # Prepopulate app_id and client_secret if not already set (e.g. for new creation)
        from django.conf import settings
        if not self.instance.pk:
            if hasattr(settings, 'INSTAGRAM_CLIENT_ID') and settings.INSTAGRAM_CLIENT_ID:
                self.fields['app_id'].initial = settings.INSTAGRAM_CLIENT_ID
            if hasattr(settings, 'INSTAGRAM_CLIENT_SECRET') and settings.INSTAGRAM_CLIENT_SECRET:
                self.fields['client_secret'].initial = settings.INSTAGRAM_CLIENT_SECRET


class ScheduledPostForm(forms.ModelForm):
    """Form for creating a scheduled post (Instagram or YouTube)."""
    
    class Meta:
        model = ScheduledPost
        fields = [
            'platform', 'account', 'youtube_account',
            'post_type', 'title', 'caption',
            'media_file', 'media_url',
            'thumbnail_file', 'thumbnail_url',
            'scheduled_time',
        ]
        widgets = {
            'platform': forms.Select(attrs={
                'class': 'form-input',
                'id': 'id_platform',
            }),
            'account': forms.Select(attrs={'class': 'form-input'}),
            'youtube_account': forms.Select(attrs={'class': 'form-input'}),
            'post_type': forms.Select(attrs={
                'class': 'form-input',
                'id': 'id_post_type',
            }),
            'title': forms.TextInput(attrs={
                'placeholder': 'Enter the video title (required for YouTube)',
                'class': 'form-input',
                'maxlength': '100',
            }),
            'caption': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Write your post caption here...\n\nUse hashtags for reach #instagram #post',
                'class': 'form-input',
            }),
            'media_file': forms.ClearableFileInput(attrs={
                'class': 'form-input file-input',
                'accept': 'image/jpeg,video/mp4,video/quicktime',
            }),
            'media_url': forms.URLInput(attrs={
                'placeholder': 'https://example.com/media/photo.jpg',
                'class': 'form-input',
            }),
            'thumbnail_file': forms.ClearableFileInput(attrs={
                'class': 'form-input file-input',
                'accept': 'image/jpeg',
            }),
            'thumbnail_url': forms.URLInput(attrs={
                'placeholder': 'https://example.com/media/thumbnail.jpg',
                'class': 'form-input',
            }),
            'scheduled_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-input',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['account'].required = False
        self.fields['youtube_account'].required = False
        self.fields['account'].queryset = InstagramAccount.objects.filter(is_active=True)
        self.fields['youtube_account'].queryset = YouTubeAccount.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        platform = cleaned_data.get('platform', 'INSTAGRAM')
        media_file = cleaned_data.get('media_file')
        media_url = cleaned_data.get('media_url')
        post_type = cleaned_data.get('post_type')
        scheduled_time = cleaned_data.get('scheduled_time')
        title = cleaned_data.get('title', '').strip()
        account = cleaned_data.get('account')
        youtube_account = cleaned_data.get('youtube_account')

        if platform == 'INSTAGRAM':
            if not account:
                raise forms.ValidationError("Please select an Instagram account.")
            # Must have either file or URL
            if not media_file and not media_url:
                raise forms.ValidationError(
                    "You must provide either a media file or a media URL."
                )
        elif platform == 'YOUTUBE':
            if not youtube_account:
                raise forms.ValidationError("Please select a YouTube channel.")
            if not title:
                raise forms.ValidationError("Title is required for YouTube videos.")
            if not media_file and not media_url:
                raise forms.ValidationError(
                    "You must provide a video file for YouTube upload."
                )

        # Validate scheduled time is in the future
        if scheduled_time and scheduled_time <= timezone.now():
            raise forms.ValidationError(
                "Scheduled time must be in the future."
            )

        return cleaned_data


class TokenExchangeForm(forms.Form):
    """Form for exchanging a short-lived token."""
    
    short_lived_token = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Paste your access token here...',
            'class': 'form-input',
        }),
        help_text="Token will be exchanged for a long-lived token and your Instagram ID will be auto-detected."
    )


TIMEZONE_CHOICES = [
    ('Asia/Kolkata', 'India (IST - GMT+5:30)'),
    ('UTC', 'Universal Time (UTC)'),
    ('America/New_York', 'Eastern Time (US - EST/EDT)'),
    ('America/Los_Angeles', 'Pacific Time (US - PST/PDT)'),
    ('Europe/London', 'London (GMT / BST)'),
    ('Europe/Paris', 'Central Europe (CET / CEST)'),
    ('Asia/Dubai', 'Gulf Standard Time (GST - Dubai)'),
    ('Asia/Singapore', 'Singapore Time (SGT)'),
    ('Australia/Sydney', 'Sydney (AEST / AEDT)'),
]


class WorkspaceForm(forms.ModelForm):
    """Form to create or update a Workspace."""
    timezone = forms.ChoiceField(
        choices=TIMEZONE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-input'})
    )

    class Meta:
        model = Workspace
        fields = ['name', 'description', 'timezone']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g., Growth Marketing Team, Client Agency, Brand Studio',
                'required': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Optional description of this workspace and team purpose...',
            }),
        }


class WorkspaceMemberInviteForm(forms.Form):
    """Form to add or invite a team member to a workspace with an assigned role."""
    ROLE_CHOICES = [
        ('ADMIN', '🛡️ Admin — Full control (invite members, assign roles, manage channels & posts)'),
        ('EDITOR', '✏️ Editor — Create, edit, schedule & publish posts across channels'),
        ('VIEWER', '👁️ Viewer — Read-only access to view calendar, posts & channels'),
    ]

    username_or_email = forms.CharField(
        label="Username or Email Address",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. colleague@company.com or username',
            'required': True,
        }),
        help_text="Enter the username or email of the registered user to add to this workspace."
    )
    role = forms.ChoiceField(
        label="Assigned Role & Permissions",
        choices=ROLE_CHOICES,
        initial='EDITOR',
        widget=forms.Select(attrs={
            'class': 'form-input',
        }),
        help_text="Select permission level for this user in your workspace."
    )

    def __init__(self, *args, workspace=None, inviting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        self.inviting_user = inviting_user

    def clean_username_or_email(self):
        val = self.cleaned_data.get('username_or_email', '').strip()
        if not val:
            raise forms.ValidationError("Please provide a username or email.")

        target_user = User.objects.filter(username__iexact=val).first()
        if not target_user:
            target_user = User.objects.filter(email__iexact=val).first()

        if not target_user:
            raise forms.ValidationError(
                f"No registered user found with username or email '{val}'. They must register an account first."
            )

        if self.workspace:
            if target_user.id == self.workspace.owner_id:
                raise forms.ValidationError(f"{target_user.username} is already the Owner of this workspace.")
            if self.workspace.memberships.filter(user=target_user).exists():
                raise forms.ValidationError(
                    f"{target_user.username} is already a member of this workspace. You can change their role below."
                )

        self.target_user = target_user
        return val


class WorkspaceMemberRoleUpdateForm(forms.ModelForm):
    """Form to update an existing workspace member's role."""
    ROLE_CHOICES = [
        ('ADMIN', '🛡️ Admin'),
        ('EDITOR', '✏️ Editor'),
        ('VIEWER', '👁️ Viewer'),
    ]
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-input form-input-sm'})
    )

    class Meta:
        model = WorkspaceMember
        fields = ['role']

