import json
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import InstagramAccountForm, ScheduledPostForm, TokenExchangeForm
from .models import InstagramAccount, ScheduledPost, YouTubeAccount
from .services import token_manager

logger = logging.getLogger(__name__)


def dashboard(request):
    """Main dashboard with overview stats."""
    accounts = InstagramAccount.objects.filter(is_active=True)
    youtube_accounts = YouTubeAccount.objects.filter(is_active=True)
    
    # Stats
    total_accounts = accounts.count() + youtube_accounts.count()
    total_pending = ScheduledPost.objects.filter(status='PENDING').count()
    total_processing = ScheduledPost.objects.filter(status='PROCESSING').count()
    total_published = ScheduledPost.objects.filter(status='PUBLISHED').count()
    total_failed = ScheduledPost.objects.filter(status='FAILED').count()
    
    # Recent posts
    recent_posts = ScheduledPost.objects.select_related('account', 'youtube_account').order_by('-created_at')[:10]
    
    # Upcoming posts
    upcoming_posts = ScheduledPost.objects.filter(
        status='PENDING',
        scheduled_time__gte=timezone.now(),
    ).select_related('account', 'youtube_account').order_by('scheduled_time')[:5]
    
    context = {
        'accounts': accounts,
        'youtube_accounts': youtube_accounts,
        'total_accounts': total_accounts,
        'total_pending': total_pending,
        'total_processing': total_processing,
        'total_published': total_published,
        'total_failed': total_failed,
        'recent_posts': recent_posts,
        'upcoming_posts': upcoming_posts,
    }
    return render(request, 'scheduler/dashboard.html', context)


def create_post(request):
    """Create scheduled posts — supports multi-account + multi-platform."""
    ig_accounts = InstagramAccount.objects.filter(is_active=True)
    yt_accounts = YouTubeAccount.objects.filter(is_active=True)

    if request.method == 'POST':
        # Collect selected accounts
        selected_ig_ids = request.POST.getlist('ig_accounts')  # list of PKs
        selected_yt_ids = request.POST.getlist('yt_accounts')  # list of PKs

        post_type = request.POST.get('post_type', 'IMAGE')
        title = request.POST.get('title', '').strip()
        caption = request.POST.get('caption', '')
        scheduled_time = request.POST.get('scheduled_time', '')
        media_url = request.POST.get('media_url', '').strip()

        # YouTube Advanced Settings
        yt_privacy_status = request.POST.get('yt_privacy_status', 'public')
        yt_tags = request.POST.get('yt_tags', '').strip()
        yt_category_id = request.POST.get('yt_category_id', '22').strip()
        yt_made_for_kids = request.POST.get('yt_made_for_kids') == 'on'

        # Validate basics
        errors = []
        if not selected_ig_ids and not selected_yt_ids:
            errors.append('Please select at least one account to post to.')

        media_file = request.FILES.get('media_file')
        thumbnail_file = request.FILES.get('thumbnail_file')
        thumbnail_url = request.POST.get('thumbnail_url', '').strip()

        if not media_file and not media_url:
            errors.append('Please provide a media file or URL.')

        if selected_yt_ids and not title:
            errors.append('Title is required for YouTube videos.')

        if not scheduled_time:
            errors.append('Please select a scheduled time.')
        else:
            from django.utils.dateparse import parse_datetime
            parsed_time = parse_datetime(scheduled_time)
            if not parsed_time:
                errors.append('Invalid date/time format.')
            else:
                from django.utils import timezone as tz
                if tz.is_naive(parsed_time):
                    import pytz
                    from django.conf import settings as s
                    try:
                        local_tz = pytz.timezone(s.TIME_ZONE)
                        parsed_time = local_tz.localize(parsed_time)
                    except Exception:
                        parsed_time = tz.make_aware(parsed_time)
                if parsed_time <= tz.now():
                    errors.append('Scheduled time must be in the future.')

        if errors:
            for err in errors:
                messages.error(request, err)
            context = {
                'accounts': ig_accounts,
                'youtube_accounts': yt_accounts,
                'form_data': request.POST,
            }
            return render(request, 'scheduler/create_post.html', context)

        # ── Save the uploaded file ONCE (shared across all posts) ───────
        saved_media_file_name = ''
        saved_thumb_file_name = ''

        if media_file:
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            import os
            folder = f'posts/media/{tz.now().strftime("%Y/%m")}/'
            saved_media_file_name = default_storage.save(
                os.path.join(folder, media_file.name),
                ContentFile(media_file.read()),
            )
            media_file.seek(0)  # reset for potential re-read

        if thumbnail_file:
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            import os
            folder = f'posts/thumbnails/{tz.now().strftime("%Y/%m")}/'
            saved_thumb_file_name = default_storage.save(
                os.path.join(folder, thumbnail_file.name),
                ContentFile(thumbnail_file.read()),
            )

        # Build absolute URLs
        built_media_url = media_url
        built_thumb_url = thumbnail_url
        if saved_media_file_name and not media_url:
            from django.conf import settings as s
            built_media_url = request.build_absolute_uri(s.MEDIA_URL + saved_media_file_name)
        if saved_thumb_file_name and not thumbnail_url:
            from django.conf import settings as s
            built_thumb_url = request.build_absolute_uri(s.MEDIA_URL + saved_thumb_file_name)

        created_count = 0

        # ── Create Instagram posts ─────────────────────────────────────
        for ig_id in selected_ig_ids:
            try:
                ig_acct = InstagramAccount.objects.get(pk=ig_id, is_active=True)
            except InstagramAccount.DoesNotExist:
                continue

            post = ScheduledPost(
                platform='INSTAGRAM',
                account=ig_acct,
                post_type=post_type,
                title=title,
                caption=caption,
                media_url=built_media_url,
                thumbnail_url=built_thumb_url,
                scheduled_time=parsed_time,
            )
            if saved_media_file_name:
                post.media_file.name = saved_media_file_name
            if saved_thumb_file_name:
                post.thumbnail_file.name = saved_thumb_file_name
            post.save()
            created_count += 1

        # ── Create YouTube posts ───────────────────────────────────────
        for yt_id in selected_yt_ids:
            try:
                yt_acct = YouTubeAccount.objects.get(pk=yt_id, is_active=True)
            except YouTubeAccount.DoesNotExist:
                continue

            post = ScheduledPost(
                platform='YOUTUBE',
                youtube_account=yt_acct,
                post_type='REEL',  # YouTube = video
                title=title or 'Untitled Video',
                caption=caption,
                media_url=built_media_url,
                thumbnail_url=built_thumb_url,
                scheduled_time=parsed_time,
                yt_privacy_status=yt_privacy_status,
                yt_tags=yt_tags,
                yt_category_id=yt_category_id,
                yt_made_for_kids=yt_made_for_kids,
            )
            if saved_media_file_name:
                post.media_file.name = saved_media_file_name
            if saved_thumb_file_name:
                post.thumbnail_file.name = saved_thumb_file_name
            post.save()
            created_count += 1

        time_str = parsed_time.strftime('%b %d, %Y %I:%M %p')
        messages.success(request, f'🚀 {created_count} post(s) scheduled for {time_str}!')
        return redirect('post_list')

    context = {
        'accounts': ig_accounts,
        'youtube_accounts': yt_accounts,
    }
    return render(request, 'scheduler/create_post.html', context)


def post_list(request):
    """List all scheduled posts with filtering."""
    status_filter = request.GET.get('status', 'all')
    type_filter = request.GET.get('type', 'all')
    
    posts = ScheduledPost.objects.select_related('account', 'youtube_account').all()
    
    if status_filter != 'all':
        posts = posts.filter(status=status_filter.upper())
    
    if type_filter != 'all':
        posts = posts.filter(post_type=type_filter.upper())
    
    # Stats for filter badges
    status_counts = ScheduledPost.objects.values('status').annotate(count=Count('id'))
    status_map = {item['status']: item['count'] for item in status_counts}
    
    context = {
        'posts': posts,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'status_counts': status_map,
        'total_count': ScheduledPost.objects.count(),
    }
    return render(request, 'scheduler/post_list.html', context)


def account_list(request):
    """Manage Instagram and YouTube accounts."""
    accounts = InstagramAccount.objects.all()
    youtube_accounts = YouTubeAccount.objects.all()
    context = {
        'accounts': accounts,
        'youtube_accounts': youtube_accounts,
    }
    return render(request, 'scheduler/account_list.html', context)


def account_add(request):
    """Add a new Instagram account."""
    if request.method == 'POST':
        form = InstagramAccountForm(request.POST)
        short_lived_token = request.POST.get('short_lived_token', '').strip()
        
        if form.is_valid():
            account = form.save(commit=False)
            # Save first to get a PK
            account.save()
            
            # Exchange token if provided
            if short_lived_token:
                result = token_manager.exchange_and_store(account, short_lived_token)
                if result['success']:
                    user_info = result.get('user_info')
                    extra_msg = ''
                    if user_info:
                        extra_msg = f' Instagram ID: {account.instagram_user_id}'
                        if user_info.get('username'):
                            extra_msg += f' (@{user_info["username"]})'
                    messages.success(
                        request, 
                        f'Account "{account.name}" added and token stored successfully!'
                        f'{extra_msg} '
                        f'Token valid until {account.token_expires_at.strftime("%b %d, %Y")}.'
                    )
                else:
                    messages.warning(
                        request, 
                        f'Account added but token failed: {result.get("error")}'
                    )
            else:
                messages.success(request, f'Account "{account.name}" added. Please add a token.')
            
            return redirect('account_list')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = InstagramAccountForm()
    
    context = {'form': form, 'is_edit': False}
    return render(request, 'scheduler/account_form.html', context)


def account_edit(request, pk):
    """Edit an existing Instagram account."""
    account = get_object_or_404(InstagramAccount, pk=pk)
    
    if request.method == 'POST':
        form = InstagramAccountForm(request.POST, instance=account)
        short_lived_token = request.POST.get('short_lived_token', '').strip()
        
        if form.is_valid():
            account = form.save()
            
            if short_lived_token:
                result = token_manager.exchange_and_store(account, short_lived_token)
                if result['success']:
                    messages.success(request, 'Account updated and token exchanged successfully!')
                else:
                    messages.warning(
                        request, 
                        f'Account updated but token exchange failed: {result.get("error")}'
                    )
            else:
                messages.success(request, 'Account updated successfully.')
            
            return redirect('account_list')
    else:
        form = InstagramAccountForm(instance=account)
    
    token_form = TokenExchangeForm()
    context = {
        'form': form,
        'token_form': token_form,
        'account': account,
        'is_edit': True,
    }
    return render(request, 'scheduler/account_form.html', context)


@require_POST
def account_exchange_token(request, pk):
    """Exchange a short-lived token for a long-lived token (AJAX)."""
    account = get_object_or_404(InstagramAccount, pk=pk)
    
    try:
        data = json.loads(request.body)
        short_lived_token = data.get('token', '').strip()
    except (json.JSONDecodeError, AttributeError):
        short_lived_token = request.POST.get('short_lived_token', '').strip()
    
    if not short_lived_token:
        return JsonResponse({'success': False, 'error': 'No token provided'})
    
    result = token_manager.exchange_and_store(account, short_lived_token)
    
    if result['success']:
        response_data = {
            'success': True,
            'message': 'Token stored successfully!',
            'expires_at': account.token_expires_at.strftime('%b %d, %Y %I:%M %p'),
            'days_remaining': account.token_days_remaining,
            'user_id': account.instagram_user_id,
        }
        user_info = result.get('user_info')
        if user_info:
            response_data['username'] = user_info.get('username', '')
            response_data['name'] = user_info.get('name', '')
            response_data['account_type'] = user_info.get('account_type', '')
        return JsonResponse(response_data)
    
    return JsonResponse({'success': False, 'error': result.get('error', 'Token failed')})


@require_POST
def account_refresh_token(request, pk):
    """Refresh the long-lived token for an account (AJAX)."""
    account = get_object_or_404(InstagramAccount, pk=pk)
    
    result = token_manager.refresh_and_store(account)
    
    if result['success']:
        return JsonResponse({
            'success': True,
            'message': 'Token refreshed successfully!',
            'expires_at': account.token_expires_at.strftime('%b %d, %Y %I:%M %p'),
            'days_remaining': account.token_days_remaining,
        })
    
    return JsonResponse({'success': False, 'error': result.get('error', 'Refresh failed')})


@require_POST
def account_delete(request, pk):
    """Delete an Instagram account."""
    account = get_object_or_404(InstagramAccount, pk=pk)
    name = account.name
    account.delete()
    messages.success(request, f'Account "{name}" deleted.')
    return redirect('account_list')


@require_POST
def post_cancel(request, pk):
    """Cancel a pending post."""
    post = get_object_or_404(ScheduledPost, pk=pk)
    if post.status == 'PENDING':
        post.status = 'CANCELLED'
        post.save(update_fields=['status'])
        messages.success(request, 'Post cancelled.')
    else:
        messages.error(request, f'Cannot cancel a post with status: {post.get_status_display()}')
    return redirect('post_list')


@require_POST
def post_retry(request, pk):
    """Retry a failed post."""
    post = get_object_or_404(ScheduledPost, pk=pk)
    if post.status in ('FAILED', 'CANCELLED'):
        post.status = 'PENDING'
        post.error_message = ''
        post.ig_container_id = ''
        post.ig_media_id = ''
        post.yt_video_id = ''
        post.scheduled_time = timezone.now()
        post.save(update_fields=[
            'status', 'error_message', 'ig_container_id', 
            'ig_media_id', 'yt_video_id', 'scheduled_time'
        ])
        messages.success(request, 'Post rescheduled for immediate publishing.')
    else:
        messages.error(request, f'Cannot retry a post with status: {post.get_status_display()}')
    return redirect('post_list')


@require_POST
def post_delete(request, pk):
    """Delete a post."""
    post = get_object_or_404(ScheduledPost, pk=pk)
    post.delete()
    messages.success(request, 'Post deleted.')
    return redirect('post_list')


# ──────────────────────────────────────────────────────────────────
# YouTube OAuth 2.0 Views
# ──────────────────────────────────────────────────────────────────

def youtube_login(request):
    """Redirect the user to Google's consent screen to authorize YouTube access."""
    from google_auth_oauthlib.flow import Flow
    import secrets, hashlib, base64

    # Allow HTTP for local dev and relax scope checking (remove in production)
    import os
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

    flow = Flow.from_client_config(
        {
            "installed": {
                "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
        ],
        redirect_uri=settings.GOOGLE_OAUTH2_REDIRECT_URI,
    )

    # Generate PKCE code verifier (required for Desktop/installed OAuth clients)
    code_verifier = secrets.token_urlsafe(64)
    flow.code_verifier = code_verifier

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    # Store state + code_verifier in the session
    request.session['youtube_oauth_state'] = state
    request.session['youtube_code_verifier'] = code_verifier
    request.session.modified = True
    return redirect(authorization_url)


def youtube_callback(request):
    """Handle the OAuth callback from Google — exchange code for tokens."""
    from google_auth_oauthlib.flow import Flow
    import os
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

    state = request.session.get('youtube_oauth_state')
    code_verifier = request.session.get('youtube_code_verifier')
    if not state:
        messages.error(request, 'OAuth state missing. Please try connecting again.')
        return redirect('account_list')

    flow = Flow.from_client_config(
        {
            "installed": {
                "client_id": settings.GOOGLE_OAUTH2_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH2_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=[
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
        ],
        redirect_uri=settings.GOOGLE_OAUTH2_REDIRECT_URI,
        state=state,
    )

    # Restore PKCE code verifier for the token exchange
    if code_verifier:
        flow.code_verifier = code_verifier

    try:
        flow.fetch_token(authorization_response=request.build_absolute_uri())
    except Exception as e:
        logger.exception(f"YouTube OAuth token exchange failed: {e}")
        messages.error(request, f'Failed to exchange token: {e}')
        return redirect('account_list')

    credentials = flow.credentials

    # Fetch channel info via YouTube API
    from googleapiclient.discovery import build
    service = build("youtube", "v3", credentials=credentials)

    try:
        resp = service.channels().list(part="snippet", mine=True).execute()
    except Exception as e:
        logger.exception(f"Failed to fetch YouTube channel info: {e}")
        messages.error(request, f'Connected but could not fetch channel info: {e}')
        return redirect('account_list')

    if not resp.get("items"):
        messages.error(request, 'No YouTube channel found for this Google account.')
        return redirect('account_list')

    channel = resp["items"][0]
    channel_id = channel["id"]
    channel_title = channel["snippet"]["title"]
    channel_thumb = channel["snippet"]["thumbnails"].get("default", {}).get("url", "")

    # Token expiry
    token_expiry = None
    if credentials.expiry:
        token_expiry = credentials.expiry
    else:
        token_expiry = timezone.now() + timedelta(hours=1)

    # Create or update the YouTubeAccount
    yt_account, created = YouTubeAccount.objects.update_or_create(
        channel_id=channel_id,
        defaults={
            'name': channel_title,
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token or '',
            'token_expires_at': token_expiry,
            'thumbnail_url': channel_thumb,
            'is_active': True,
        },
    )

    verb = "connected" if created else "reconnected"
    messages.success(request, f'YouTube channel "{channel_title}" {verb} successfully! 🎉')
    return redirect('account_list')


@require_POST
def youtube_disconnect(request, pk):
    """Disconnect (delete) a YouTube account."""
    yt_account = get_object_or_404(YouTubeAccount, pk=pk)
    name = yt_account.name
    yt_account.delete()
    messages.success(request, f'YouTube channel "{name}" disconnected.')
    return redirect('account_list')
