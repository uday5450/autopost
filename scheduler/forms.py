from django import forms
from django.utils import timezone

from .models import InstagramAccount, ScheduledPost, YouTubeAccount


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
