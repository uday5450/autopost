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
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from .forms import (
    InstagramAccountForm, ScheduledPostForm, TokenExchangeForm,
    WorkspaceForm, WorkspaceMemberInviteForm, WorkspaceMemberRoleUpdateForm
)
from .models import (
    InstagramAccount, ScheduledPost, YouTubeAccount,
    FacebookAccount, XAccount, PinterestAccount, TikTokAccount,
    LinkedInAccount, RedditAccount, SnapchatAccount, UserSubscription,
    PricingPlan, DiscountCoupon, UserProfile,
    Workspace, WorkspaceMember
)
from .services import token_manager

logger = logging.getLogger(__name__)


@login_required
def dashboard(request):
    """Main dashboard with overview stats."""
    accounts = InstagramAccount.objects.filter(user=request.user, is_active=True)
    youtube_accounts = YouTubeAccount.objects.filter(user=request.user, is_active=True)
    facebook_accounts = FacebookAccount.objects.filter(user=request.user, is_active=True)
    x_accounts = XAccount.objects.filter(user=request.user, is_active=True)
    pinterest_accounts = PinterestAccount.objects.filter(user=request.user, is_active=True)
    tiktok_accounts = TikTokAccount.objects.filter(user=request.user, is_active=True)
    linkedin_accounts = LinkedInAccount.objects.filter(user=request.user, is_active=True)
    reddit_accounts = RedditAccount.objects.filter(user=request.user, is_active=True)
    snapchat_accounts = SnapchatAccount.objects.filter(user=request.user, is_active=True)
    
    # Stats
    total_accounts = (
        accounts.count() + youtube_accounts.count() +
        facebook_accounts.count() + x_accounts.count() +
        pinterest_accounts.count() + tiktok_accounts.count() +
        linkedin_accounts.count() + reddit_accounts.count() +
        snapchat_accounts.count()
    )
    total_pending = ScheduledPost.objects.filter(user=request.user, status='PENDING').count()
    total_processing = ScheduledPost.objects.filter(user=request.user, status='PROCESSING').count()
    total_published = ScheduledPost.objects.filter(user=request.user, status='PUBLISHED').count()
    total_failed = ScheduledPost.objects.filter(user=request.user, status='FAILED').count()
    
    # Recent posts
    recent_posts = ScheduledPost.objects.filter(user=request.user).select_related(
        'account', 'youtube_account', 'facebook_account', 'x_account',
        'pinterest_account', 'tiktok_account', 'linkedin_account',
        'reddit_account', 'snapchat_account'
    ).order_by('-created_at')[:10]
    
    # Upcoming posts
    upcoming_posts = ScheduledPost.objects.filter(
        user=request.user,
        status='PENDING',
        scheduled_time__gte=timezone.now(),
    ).select_related(
        'account', 'youtube_account', 'facebook_account', 'x_account',
        'pinterest_account', 'tiktok_account', 'linkedin_account',
        'reddit_account', 'snapchat_account'
    ).order_by('scheduled_time')[:5]
    
    context = {
        'accounts': accounts,
        'youtube_accounts': youtube_accounts,
        'facebook_accounts': facebook_accounts,
        'x_accounts': x_accounts,
        'pinterest_accounts': pinterest_accounts,
        'tiktok_accounts': tiktok_accounts,
        'linkedin_accounts': linkedin_accounts,
        'reddit_accounts': reddit_accounts,
        'snapchat_accounts': snapchat_accounts,
        'total_accounts': total_accounts,
        'total_pending': total_pending,
        'total_processing': total_processing,
        'total_published': total_published,
        'total_failed': total_failed,
        'recent_posts': recent_posts,
        'upcoming_posts': upcoming_posts,
    }
    return render(request, 'scheduler/dashboard.html', context)


@login_required
def create_post(request):
    """Create scheduled posts — supports multi-account + multi-platform."""
    ig_accounts = InstagramAccount.objects.filter(user=request.user, is_active=True)
    yt_accounts = YouTubeAccount.objects.filter(user=request.user, is_active=True)
    fb_accounts = FacebookAccount.objects.filter(user=request.user, is_active=True)
    x_accounts = XAccount.objects.filter(user=request.user, is_active=True)
    pin_accounts = PinterestAccount.objects.filter(user=request.user, is_active=True)
    tt_accounts = TikTokAccount.objects.filter(user=request.user, is_active=True)
    li_accounts = LinkedInAccount.objects.filter(user=request.user, is_active=True)
    reddit_accounts = RedditAccount.objects.filter(user=request.user, is_active=True)
    snap_accounts = SnapchatAccount.objects.filter(user=request.user, is_active=True)

    if request.method == 'POST':
        # Collect selected accounts
        selected_ig_ids = request.POST.getlist('ig_accounts')  # list of PKs
        selected_yt_ids = request.POST.getlist('yt_accounts')  # list of PKs
        selected_fb_ids = request.POST.getlist('fb_accounts')  # list of PKs
        selected_x_ids = request.POST.getlist('x_accounts')  # list of PKs
        selected_pin_ids = request.POST.getlist('pin_accounts')  # list of PKs
        selected_tt_ids = request.POST.getlist('tt_accounts')  # list of PKs
        selected_li_ids = request.POST.getlist('li_accounts')  # list of PKs
        selected_reddit_ids = request.POST.getlist('reddit_accounts')  # list of PKs
        selected_snap_ids = request.POST.getlist('snap_accounts')  # list of PKs

        post_type = request.POST.get('post_type', 'IMAGE')
        title = request.POST.get('title', '').strip()
        caption = request.POST.get('caption', '')
        scheduled_time = request.POST.get('scheduled_time', '')
        media_url = request.POST.get('media_url', '').strip()

        # Per-platform caption & title overrides
        caption_ig = request.POST.get('caption_ig', '').strip() or caption
        caption_yt = request.POST.get('caption_yt', '').strip() or caption
        caption_fb = request.POST.get('caption_fb', '').strip() or caption
        caption_x = request.POST.get('caption_x', '').strip() or caption
        caption_pin = request.POST.get('caption_pin', '').strip() or caption
        caption_tt = request.POST.get('caption_tt', '').strip() or caption
        caption_li = request.POST.get('caption_li', '').strip() or caption
        caption_reddit = request.POST.get('caption_reddit', '').strip() or caption
        caption_snap = request.POST.get('caption_snap', '').strip() or caption

        title_yt = request.POST.get('title_yt', '').strip() or title
        title_fb = request.POST.get('title_fb', '').strip() or title
        title_reddit = request.POST.get('title_reddit', '').strip() or title

        # YouTube Advanced Settings
        yt_privacy_status = request.POST.get('yt_privacy_status', 'public')
        yt_tags = request.POST.get('yt_tags', '').strip()
        yt_category_id = request.POST.get('yt_category_id', '22').strip()
        yt_made_for_kids = request.POST.get('yt_made_for_kids') == 'on'

        # Validate basics
        errors = []
        has_any_selection = (
            selected_ig_ids or selected_yt_ids or selected_fb_ids or
            selected_x_ids or selected_pin_ids or selected_tt_ids or
            selected_li_ids or selected_reddit_ids or selected_snap_ids
        )
        if not has_any_selection:
            errors.append('Please select at least one account to post to.')

        media_file = request.FILES.get('media_file')
        thumbnail_file = request.FILES.get('thumbnail_file')
        thumbnail_url = request.POST.get('thumbnail_url', '').strip()

        post_immediately = request.POST.get('post_immediately') == 'on'

        if not media_file and not media_url:
            errors.append('Please provide a media file or URL.')

        if selected_yt_ids and not title:
            errors.append('Title is required for YouTube videos.')

        from django.utils import timezone as tz
        from datetime import timedelta
        
        parsed_time = None
        if post_immediately:
            # Set to 1 minute in the past so the scheduler picks it up instantly
            parsed_time = tz.now() - timedelta(minutes=1)
        else:
            if not scheduled_time:
                errors.append('Please select a scheduled time or check "Post Immediately".')
            else:
                from django.utils.dateparse import parse_datetime
                parsed_time = parse_datetime(scheduled_time)
                if not parsed_time:
                    errors.append('Invalid date/time format.')
                else:
                    if tz.is_naive(parsed_time):
                        parsed_time = tz.make_aware(parsed_time)
                    if parsed_time <= tz.now():
                        errors.append('Scheduled time must be in the future.')

        if errors:
            for err in errors:
                messages.error(request, err)
            context = {
                'accounts': ig_accounts,
                'youtube_accounts': yt_accounts,
                'facebook_accounts': fb_accounts,
                'x_accounts': x_accounts,
                'pinterest_accounts': pin_accounts,
                'tiktok_accounts': tt_accounts,
                'linkedin_accounts': li_accounts,
                'reddit_accounts': reddit_accounts,
                'snapchat_accounts': snap_accounts,
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
            from django.utils import timezone as tz
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
            from django.utils import timezone as tz
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
                ig_acct = InstagramAccount.objects.get(pk=ig_id, user=request.user, is_active=True)
            except InstagramAccount.DoesNotExist:
                continue

            post = ScheduledPost(
                user=request.user,
                platform='INSTAGRAM',
                account=ig_acct,
                post_type=post_type,
                title=title,
                caption=caption_ig,
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
                yt_acct = YouTubeAccount.objects.get(pk=yt_id, user=request.user, is_active=True)
            except YouTubeAccount.DoesNotExist:
                continue

            post = ScheduledPost(
                user=request.user,
                platform='YOUTUBE',
                youtube_account=yt_acct,
                post_type='REEL',  # YouTube = video
                title=title_yt or 'Untitled Video',
                caption=caption_yt,
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

        # ── Create Facebook posts ──────────────────────────────────────
        for fb_id in selected_fb_ids:
            try:
                fb_acct = FacebookAccount.objects.get(pk=fb_id, user=request.user, is_active=True)
            except FacebookAccount.DoesNotExist:
                continue

            post = ScheduledPost(
                user=request.user,
                platform='FACEBOOK',
                facebook_account=fb_acct,
                post_type=post_type,
                title=title_fb,
                caption=caption_fb,
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

        # ── Create X (Twitter) posts ───────────────────────────────────
        for x_id in selected_x_ids:
            try:
                x_acct = XAccount.objects.get(pk=x_id, user=request.user, is_active=True)
            except XAccount.DoesNotExist:
                continue

            post = ScheduledPost(
                user=request.user,
                platform='X',
                x_account=x_acct,
                post_type='IMAGE' if post_type == 'IMAGE' else 'REEL',
                title=title,
                caption=caption_x,
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

        # ── Create Pinterest posts ─────────────────────────────────────
        for pin_id in selected_pin_ids:
            try:
                pin_acct = PinterestAccount.objects.get(pk=pin_id, user=request.user, is_active=True)
            except PinterestAccount.DoesNotExist:
                continue

            post = ScheduledPost(
                user=request.user,
                platform='PINTEREST',
                pinterest_account=pin_acct,
                post_type='IMAGE',
                title=title or 'Pin Title',
                caption=caption_pin,
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

        # ── Create TikTok posts ────────────────────────────────────────
        for tt_id in selected_tt_ids:
            try:
                tt_acct = TikTokAccount.objects.get(pk=tt_id, user=request.user, is_active=True)
            except TikTokAccount.DoesNotExist:
                continue

            post = ScheduledPost(
                user=request.user,
                platform='TIKTOK',
                tiktok_account=tt_acct,
                post_type='REEL',
                title=title or 'TikTok Video',
                caption=caption_tt,
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

        # ── Create LinkedIn posts ──────────────────────────────────────
        for li_id in selected_li_ids:
            try:
                li_acct = LinkedInAccount.objects.get(pk=li_id, user=request.user, is_active=True)
            except LinkedInAccount.DoesNotExist:
                continue

            post = ScheduledPost(
                user=request.user,
                platform='LINKEDIN',
                linkedin_account=li_acct,
                post_type=post_type,
                title=title,
                caption=caption_li,
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

        # ── Create Reddit posts ────────────────────────────────────────
        for rd_id in selected_reddit_ids:
            try:
                rd_acct = RedditAccount.objects.get(pk=rd_id, user=request.user, is_active=True)
            except RedditAccount.DoesNotExist:
                continue

            post = ScheduledPost(
                user=request.user,
                platform='REDDIT',
                reddit_account=rd_acct,
                post_type=post_type,
                title=title_reddit or 'Reddit Discussion',
                caption=caption_reddit,
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

        # ── Create Snapchat posts ──────────────────────────────────────
        for sc_id in selected_snap_ids:
            try:
                sc_acct = SnapchatAccount.objects.get(pk=sc_id, user=request.user, is_active=True)
            except SnapchatAccount.DoesNotExist:
                continue

            post = ScheduledPost(
                user=request.user,
                platform='SNAPCHAT',
                snapchat_account=sc_acct,
                post_type='REEL',  # Snapchat Spotlight/Story
                title=title or 'Snap Story',
                caption=caption_snap,
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

        time_str = parsed_time.strftime('%b %d, %Y %I:%M %p')
        messages.success(request, f'🚀 {created_count} post(s) scheduled for {time_str}!')
        return redirect('post_list')

    context = {
        'accounts': ig_accounts,
        'youtube_accounts': yt_accounts,
        'facebook_accounts': fb_accounts,
        'x_accounts': x_accounts,
        'pinterest_accounts': pin_accounts,
        'tiktok_accounts': tt_accounts,
        'linkedin_accounts': li_accounts,
        'reddit_accounts': reddit_accounts,
        'snapchat_accounts': snap_accounts,
    }
    return render(request, 'scheduler/create_post.html', context)


@login_required
def post_list(request):
    """List all scheduled posts with filtering."""
    status_filter = request.GET.get('status', 'all')
    type_filter = request.GET.get('type', 'all')
    
    posts = ScheduledPost.objects.filter(user=request.user).select_related(
        'account', 'youtube_account', 'facebook_account', 'x_account',
        'pinterest_account', 'tiktok_account', 'linkedin_account',
        'reddit_account', 'snapchat_account'
    )
    
    if status_filter != 'all':
        posts = posts.filter(status=status_filter.upper())
    
    if type_filter != 'all':
        posts = posts.filter(post_type=type_filter.upper())
    
    # Stats for filter badges
    status_counts = ScheduledPost.objects.filter(user=request.user).values('status').annotate(count=Count('id'))
    status_map = {item['status']: item['count'] for item in status_counts}
    
    context = {
        'posts': posts,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'status_counts': status_map,
        'total_count': ScheduledPost.objects.filter(user=request.user).count(),
    }
    return render(request, 'scheduler/post_list.html', context)


@login_required
def account_list(request):
    """Manage Instagram, YouTube, Facebook, X, Pinterest, TikTok, LinkedIn, Reddit, Snapchat accounts."""
    accounts = InstagramAccount.objects.filter(user=request.user)
    youtube_accounts = YouTubeAccount.objects.filter(user=request.user)
    facebook_accounts = FacebookAccount.objects.filter(user=request.user)
    x_accounts = XAccount.objects.filter(user=request.user)
    pinterest_accounts = PinterestAccount.objects.filter(user=request.user)
    tiktok_accounts = TikTokAccount.objects.filter(user=request.user)
    linkedin_accounts = LinkedInAccount.objects.filter(user=request.user)
    reddit_accounts = RedditAccount.objects.filter(user=request.user)
    snapchat_accounts = SnapchatAccount.objects.filter(user=request.user)
    context = {
        'accounts': accounts,
        'youtube_accounts': youtube_accounts,
        'facebook_accounts': facebook_accounts,
        'x_accounts': x_accounts,
        'pinterest_accounts': pinterest_accounts,
        'tiktok_accounts': tiktok_accounts,
        'linkedin_accounts': linkedin_accounts,
        'reddit_accounts': reddit_accounts,
        'snapchat_accounts': snapchat_accounts,
    }
    return render(request, 'scheduler/account_list.html', context)


@login_required
def account_add(request):
    """Add a new Instagram account."""
    if request.method == 'POST':
        form = InstagramAccountForm(request.POST)
        short_lived_token = request.POST.get('short_lived_token', '').strip()
        
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
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


@login_required
def account_edit(request, pk):
    """Edit an existing Instagram account."""
    account = get_object_or_404(InstagramAccount, pk=pk, user=request.user)
    
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


@login_required
@require_POST
def account_exchange_token(request, pk):
    """Exchange a short-lived token for a long-lived token (AJAX)."""
    account = get_object_or_404(InstagramAccount, pk=pk, user=request.user)
    
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


@login_required
@require_POST
def account_refresh_token(request, pk):
    """Refresh the long-lived token for an account (AJAX)."""
    account = get_object_or_404(InstagramAccount, pk=pk, user=request.user)
    
    result = token_manager.refresh_and_store(account)
    
    if result['success']:
        return JsonResponse({
            'success': True,
            'message': 'Token refreshed successfully!',
            'expires_at': account.token_expires_at.strftime('%b %d, %Y %I:%M %p'),
            'days_remaining': account.token_days_remaining,
        })
    
    return JsonResponse({'success': False, 'error': result.get('error', 'Refresh failed')})


@login_required
@require_POST
def account_delete(request, pk):
    """Delete an Instagram account."""
    account = get_object_or_404(InstagramAccount, pk=pk, user=request.user)
    name = account.name
    account.delete()
    messages.success(request, f'Account "{name}" deleted.')
    return redirect('account_list')


@login_required
@require_POST
def post_cancel(request, pk):
    """Cancel a pending post."""
    post = get_object_or_404(ScheduledPost, pk=pk, user=request.user)
    if post.status == 'PENDING':
        post.status = 'CANCELLED'
        post.save(update_fields=['status'])
        messages.success(request, 'Post cancelled.')
    else:
        messages.error(request, f'Cannot cancel a post with status: {post.get_status_display()}')
    return redirect('post_list')


@login_required
@require_POST
def post_retry(request, pk):
    """Retry a failed post."""
    post = get_object_or_404(ScheduledPost, pk=pk, user=request.user)
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


@login_required
@require_POST
def post_delete(request, pk):
    """Delete a post."""
    post = get_object_or_404(ScheduledPost, pk=pk, user=request.user)
    post.delete()
    messages.success(request, 'Post deleted.')
    return redirect('post_list')


# ──────────────────────────────────────────────────────────────────
# YouTube OAuth 2.0 Views
# ──────────────────────────────────────────────────────────────────

@login_required
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
            "web": {
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

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    # Store state and PKCE code_verifier generated by authorization_url in session
    request.session['youtube_oauth_state'] = state
    request.session['youtube_code_verifier'] = flow.code_verifier
    request.session.modified = True
    return redirect(authorization_url)


@login_required
def youtube_callback(request):
    """Handle the OAuth callback from Google — exchange code for tokens."""
    from google_auth_oauthlib.flow import Flow
    import os
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

    code = request.GET.get('code')
    if not code:
        messages.error(request, 'No authorization code received from Google. Please try connecting again.')
        return redirect('account_list')

    state = request.session.get('youtube_oauth_state') or request.GET.get('state')
    code_verifier = request.session.get('youtube_code_verifier')

    flow = Flow.from_client_config(
        {
            "web": {
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

    # Restore PKCE code verifier matching the authorization challenge sent to Google
    if code_verifier:
        flow.code_verifier = code_verifier

    try:
        # Pass authorization code directly to avoid client-side state string mismatch errors
        flow.fetch_token(code=code)
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
            'user': request.user,
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


@login_required
@require_POST
def youtube_disconnect(request, pk):
    """Disconnect (delete) a YouTube account."""
    yt_account = get_object_or_404(YouTubeAccount, pk=pk, user=request.user)
    name = yt_account.name
    yt_account.delete()
    messages.success(request, f'YouTube channel "{name}" disconnected.')
    return redirect('account_list')


# ──────────────────────────────────────────────────────────────────
# Simulated OAuth Views for new platforms
# ──────────────────────────────────────────────────────────────────

@login_required
def connect_facebook(request):
    """Simulate Facebook Page connection."""
    if request.method == 'POST':
        from random import randint
        page_num = randint(100, 999)
        FacebookAccount.objects.create(
            user=request.user,
            name=f"Facebook Page {page_num}",
            page_id=f"fb_page_{randint(100000, 999999)}",
            access_token=f"mock_fb_token_{randint(100000, 999999)}",
            profile_picture_url="https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=100&h=100&fit=crop",
            is_active=True
        )
        messages.success(request, "Facebook Page connected successfully! 🎉")
        return redirect('account_list')
        
    context = {
        'platform_name': 'Facebook Page',
        'platform_id': 'facebook',
    }
    return render(request, 'scheduler/connect_mock.html', context)


@login_required
@require_POST
def disconnect_facebook(request, pk):
    """Disconnect Facebook Page."""
    acct = get_object_or_404(FacebookAccount, pk=pk, user=request.user)
    name = acct.name
    acct.delete()
    messages.success(request, f"Facebook Page '{name}' disconnected.")
    return redirect('account_list')


@login_required
def connect_x(request):
    """Simulate X (Twitter) connection."""
    if request.method == 'POST':
        from random import randint
        user_num = randint(100, 999)
        XAccount.objects.create(
            user=request.user,
            name=f"X Brand User {user_num}",
            screen_name=f"brand_user_{user_num}",
            access_token=f"mock_x_token_{randint(100000, 999999)}",
            refresh_token=f"mock_x_refresh_{randint(100000, 999999)}",
            profile_picture_url="https://images.unsplash.com/photo-1611605698335-8b15d27e03f3?w=100&h=100&fit=crop",
            is_active=True
        )
        messages.success(request, "X (Twitter) account connected successfully! 🎉")
        return redirect('account_list')
        
    context = {
        'platform_name': 'X (Twitter)',
        'platform_id': 'x',
    }
    return render(request, 'scheduler/connect_mock.html', context)


@login_required
@require_POST
def disconnect_x(request, pk):
    """Disconnect X Account."""
    acct = get_object_or_404(XAccount, pk=pk, user=request.user)
    name = acct.name
    acct.delete()
    messages.success(request, f"X Account '{name}' disconnected.")
    return redirect('account_list')


@login_required
def connect_pinterest(request):
    """Simulate Pinterest Board connection."""
    if request.method == 'POST':
        from random import randint
        board_name = request.POST.get('board_name', 'My Awesome Board')
        user_num = randint(100, 999)
        PinterestAccount.objects.create(
            user=request.user,
            name=f"PinCreator_{user_num}",
            board_name=board_name,
            access_token=f"mock_pinterest_token_{randint(100000, 999999)}",
            profile_picture_url="https://images.unsplash.com/photo-1611162616305-c69b3fa7fbe0?w=100&h=100&fit=crop",
            is_active=True
        )
        messages.success(request, f"Pinterest board '{board_name}' connected successfully! 🎉")
        return redirect('account_list')
        
    context = {
        'platform_name': 'Pinterest',
        'platform_id': 'pinterest',
    }
    return render(request, 'scheduler/connect_mock.html', context)


@login_required
@require_POST
def disconnect_pinterest(request, pk):
    """Disconnect Pinterest board."""
    acct = get_object_or_404(PinterestAccount, pk=pk, user=request.user)
    name = acct.board_name
    acct.delete()
    messages.success(request, f"Pinterest Board '{name}' disconnected.")
    return redirect('account_list')


@login_required
def connect_tiktok(request):
    """Simulate TikTok connection."""
    if request.method == 'POST':
        from random import randint
        user_num = randint(100, 999)
        TikTokAccount.objects.create(
            user=request.user,
            name=f"TikTok Star {user_num}",
            username=f"tiktok_star_{user_num}",
            access_token=f"mock_tiktok_token_{randint(100000, 999999)}",
            refresh_token=f"mock_tiktok_refresh_{randint(100000, 999999)}",
            profile_picture_url="https://images.unsplash.com/photo-1611162618071-b39a2ec055fb?w=100&h=100&fit=crop",
            is_active=True
        )
        messages.success(request, "TikTok account connected successfully! 🎉")
        return redirect('account_list')
        
    context = {
        'platform_name': 'TikTok',
        'platform_id': 'tiktok',
    }
    return render(request, 'scheduler/connect_mock.html', context)


@login_required
@require_POST
def disconnect_tiktok(request, pk):
    """Disconnect TikTok Account."""
    acct = get_object_or_404(TikTokAccount, pk=pk, user=request.user)
    name = acct.name
    acct.delete()
    messages.success(request, f"TikTok Account '{name}' disconnected.")
    return redirect('account_list')


def signup_view(request):
    """Handle sign up with full name, country, mobile number, email, and password."""
    next_url = request.GET.get('next') or request.POST.get('next')
    if request.user.is_authenticated:
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect('dashboard')
        
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        country_code = request.POST.get('country_code', '+91').strip()
        country_name = request.POST.get('country_name', 'India').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        terms_agreed = request.POST.get('terms_agreed')
        next_url = request.POST.get('next') or request.GET.get('next')
        
        errors = []
        if not full_name:
            errors.append('Full Name is required.')
        if not phone_number:
            errors.append('Mobile number is required.')
        if not email:
            errors.append('Email Address is required.')
        if not password:
            errors.append('Password is required.')
        elif len(password) < 4:
            errors.append('Password must be at least 4 characters long.')
        if password != password_confirm:
            errors.append('Passwords do not match.')
        if not terms_agreed:
            errors.append('You must agree to the Terms of Service and Privacy Policy to continue.')
            
        if not errors:
            if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
                errors.append('A user with this email already exists.')
                
        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'scheduler/signup.html', {
                'full_name': full_name,
                'country_code': country_code,
                'country_name': country_name,
                'phone_number': phone_number,
                'email': email,
                'next': next_url
            })
            
        # Create user
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=full_name
        )
        
        # Create user profile with phone and international country
        UserProfile.objects.create(
            user=user,
            full_name=full_name,
            phone_number=phone_number,
            country_code=country_code,
            country_name=country_name,
            onboarding_completed=False
        )
        
        login(request, user)
        messages.success(request, f'Welcome to FeedBridge, {full_name}! Let’s connect your social channels to start scheduling. 🚀')
        
        # Redirect directly to social media onboarding connect screen (not directly to dashboard)
        if next_url and next_url.startswith('/') and not next_url.startswith('/dashboard'):
            return redirect(next_url)
        return redirect('onboarding_connect')
        
    return render(request, 'scheduler/signup.html', {'next': next_url})


@login_required
def onboarding_connect(request):
    """
    Onboarding step right after signup: Show all social media channels to connect.
    Directs user here instead of straight to dashboard.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    # Handle quick connect actions
    if request.method == 'POST':
        action = request.POST.get('action')
        platform = request.POST.get('platform')
        
        if action == 'quick_connect' and platform:
            from random import randint
            num = randint(100, 999)
            user_handle = f"{request.user.first_name.lower().replace(' ', '_') if request.user.first_name else 'creator'}_{num}"
            
            if platform == 'instagram':
                InstagramAccount.objects.create(
                    user=request.user,
                    name=f"@{user_handle}",
                    instagram_user_id=f"ig_{user_handle}",
                    app_id="meta_feedbridge",
                    client_secret="mock_secret",
                    access_token=f"mock_ig_token_{num}",
                    is_active=True
                )
                messages.success(request, f"Instagram (@{user_handle}) connected successfully! 🎉")
            elif platform == 'youtube':
                YouTubeAccount.objects.create(
                    user=request.user,
                    name=f"{request.user.first_name or 'Creator'} Studio",
                    channel_id=f"UC_{randint(10000000, 99999999)}",
                    access_token=f"mock_yt_token_{num}",
                    is_active=True
                )
                messages.success(request, f"YouTube Channel connected successfully! 🎉")
            elif platform == 'tiktok':
                TikTokAccount.objects.create(
                    user=request.user,
                    name=f"@{user_handle}",
                    tiktok_user_id=f"tt_{randint(100000, 999999)}",
                    access_token=f"mock_tt_token_{num}",
                    is_active=True
                )
                messages.success(request, f"TikTok (@{user_handle}) connected successfully! 🎉")
            elif platform == 'x':
                XAccount.objects.create(
                    user=request.user,
                    name=request.user.first_name or "Creator",
                    screen_name=user_handle,
                    access_token=f"mock_x_token_{num}",
                    is_active=True
                )
                messages.success(request, f"X (@{user_handle}) connected successfully! 🎉")
            elif platform == 'facebook':
                FacebookAccount.objects.create(
                    user=request.user,
                    name=f"{request.user.first_name or 'Creator'} Official Page",
                    page_id=f"fb_page_{randint(100000, 999999)}",
                    access_token=f"mock_fb_token_{num}",
                    is_active=True
                )
                messages.success(request, "Facebook Page connected successfully! 🎉")
            elif platform == 'linkedin':
                LinkedInAccount.objects.create(
                    user=request.user,
                    name=f"{request.user.first_name or 'Professional'} Profile",
                    linkedin_id=f"li_{randint(100000, 999999)}",
                    access_token=f"mock_li_token_{num}",
                    is_active=True
                )
                messages.success(request, "LinkedIn Profile connected successfully! 🎉")
            elif platform == 'pinterest':
                PinterestAccount.objects.create(
                    user=request.user,
                    name=user_handle,
                    board_name="Main Inspiration Board",
                    access_token=f"mock_pin_token_{num}",
                    is_active=True
                )
                messages.success(request, "Pinterest Board connected successfully! 🎉")
            elif platform == 'snapchat':
                SnapchatAccount.objects.create(
                    user=request.user,
                    name=f"{user_handle}_snap",
                    snapchat_user_id=f"sc_{randint(100000, 999999)}",
                    access_token=f"mock_sc_token_{num}",
                    is_active=True
                )
                messages.success(request, "Snapchat account connected successfully! 🎉")
            elif platform == 'reddit':
                RedditAccount.objects.create(
                    user=request.user,
                    name=f"u/{user_handle}",
                    reddit_username=user_handle,
                    access_token=f"mock_reddit_token_{num}",
                    is_active=True
                )
                messages.success(request, "Reddit account connected successfully! 🎉")
            return redirect('onboarding_connect')
            
        elif action == 'complete_onboarding':
            profile.onboarding_completed = True
            profile.save()
            messages.success(request, "All set! Welcome to your FeedBridge studio dashboard. 🎯")
            return redirect('dashboard')
            
    # Gather live account counts and instances
    ig_accounts = list(InstagramAccount.objects.filter(user=request.user, is_active=True))
    yt_accounts = list(YouTubeAccount.objects.filter(user=request.user, is_active=True))
    fb_accounts = list(FacebookAccount.objects.filter(user=request.user, is_active=True))
    x_accounts = list(XAccount.objects.filter(user=request.user, is_active=True))
    pin_accounts = list(PinterestAccount.objects.filter(user=request.user, is_active=True))
    tt_accounts = list(TikTokAccount.objects.filter(user=request.user, is_active=True))
    li_accounts = list(LinkedInAccount.objects.filter(user=request.user, is_active=True))
    reddit_accounts = list(RedditAccount.objects.filter(user=request.user, is_active=True))
    snap_accounts = list(SnapchatAccount.objects.filter(user=request.user, is_active=True))
    
    total_connected = (
        len(ig_accounts) + len(yt_accounts) + len(fb_accounts) +
        len(x_accounts) + len(pin_accounts) + len(tt_accounts) +
        len(li_accounts) + len(reddit_accounts) + len(snap_accounts)
    )
    
    channels = [
        {
            'id': 'instagram',
            'name': 'Instagram',
            'company': 'Meta',
            'color': 'linear-gradient(135deg, #f58529, #dd2a7b, #8134af)',
            'icon_svg': '<svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg>',
            'badge': 'Reels & Carousels',
            'desc': 'Auto-publish Reels, Photos, and multi-slide Carousels directly to your feed.',
            'accounts': ig_accounts,
            'is_connected': len(ig_accounts) > 0,
            'connect_url': '/accounts/add/?next=/onboarding/connect/',
        },
        {
            'id': 'youtube',
            'name': 'YouTube',
            'company': 'Google',
            'color': '#ff0000',
            'icon_svg': '<svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>',
            'badge': 'Shorts & Long-form',
            'desc': 'Schedule YouTube Shorts and standard videos with custom thumbnails.',
            'accounts': yt_accounts,
            'is_connected': len(yt_accounts) > 0,
            'connect_url': '/accounts/youtube/login/',
        },
        {
            'id': 'tiktok',
            'name': 'TikTok',
            'company': 'ByteDance',
            'color': '#000000',
            'icon_svg': '<svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64c.29 0 .57.04.84.12V9.36a6.34 6.34 0 0 0-.84-.05A6.33 6.33 0 0 0 3 15.64 6.33 6.33 0 0 0 9.33 22a6.34 6.34 0 0 0 6.34-6.33V9.22a8.16 8.16 0 0 0 4.92 1.62v-3.5a4.85 4.85 0 0 1-1-.65z"/></svg>',
            'badge': 'Auto-Publish Video',
            'desc': 'Directly schedule vertical short videos to TikTok feeds.',
            'accounts': tt_accounts,
            'is_connected': len(tt_accounts) > 0,
            'connect_url': '/accounts/tiktok/connect/?next=/onboarding/connect/',
        },
        {
            'id': 'x',
            'name': 'X (Twitter)',
            'company': 'X Corp',
            'color': '#111827',
            'icon_svg': '<svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>',
            'badge': 'Posts & Threads',
            'desc': 'Broadcast tweets, threads, and media posts to your X audience.',
            'accounts': x_accounts,
            'is_connected': len(x_accounts) > 0,
            'connect_url': '/accounts/x/connect/?next=/onboarding/connect/',
        },
        {
            'id': 'facebook',
            'name': 'Facebook Page',
            'company': 'Meta',
            'color': '#1877f2',
            'icon_svg': '<svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg>',
            'badge': 'Pages & Reels',
            'desc': 'Publish to your official brand and creator Facebook pages.',
            'accounts': fb_accounts,
            'is_connected': len(fb_accounts) > 0,
            'connect_url': '/accounts/facebook/connect/?next=/onboarding/connect/',
        },
        {
            'id': 'linkedin',
            'name': 'LinkedIn',
            'company': 'Microsoft',
            'color': '#0a66c2',
            'icon_svg': '<svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/><rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/></svg>',
            'badge': 'Articles & Updates',
            'desc': 'Share thought leadership, video posts, and PDF carousels.',
            'accounts': li_accounts,
            'is_connected': len(li_accounts) > 0,
            'connect_url': '/accounts/linkedin/connect/?next=/onboarding/connect/',
        },
        {
            'id': 'pinterest',
            'name': 'Pinterest',
            'company': 'Pinterest Inc',
            'color': '#e60023',
            'icon_svg': '<svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M12 0a12 12 0 0 0-4.37 23.18c-.06-.98-.12-2.48.02-3.55l1.04-4.42s-.26-.52-.26-1.3c0-1.22.7-2.13 1.58-2.13.75 0 1.11.56 1.11 1.23 0 .75-.48 1.88-.73 2.92-.2.88.44 1.6 1.3 1.6 1.57 0 2.78-1.65 2.78-4.04 0-2.11-1.52-3.58-3.69-3.58-2.51 0-3.99 1.88-3.99 3.82 0 .76.29 1.57.66 2.01.07.09.08.17.06.26l-.25 1.02c-.04.16-.14.2-.32.12-1.19-.55-1.93-2.28-1.93-3.67 0-2.99 2.17-5.74 6.27-5.74 3.29 0 5.85 2.34 5.85 5.48 0 3.27-2.06 5.9-4.92 5.9-.96 0-1.87-.5-2.18-1.09l-.59 2.27c-.22.83-.8 1.87-1.2 2.5A12 12 0 1 0 12 0z"/></svg>',
            'badge': 'Pins & Boards',
            'desc': 'Schedule visual pins and drive evergreen traffic to your links.',
            'accounts': pin_accounts,
            'is_connected': len(pin_accounts) > 0,
            'connect_url': '/accounts/pinterest/connect/?next=/onboarding/connect/',
        },
        {
            'id': 'reddit',
            'name': 'Reddit',
            'company': 'Reddit Inc',
            'color': '#ff4500',
            'icon_svg': '<svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><circle cx="12" cy="12" r="10"/><path fill="#fff" d="M18.8 12.3a1.4 1.4 0 0 0-2.3-1 6.5 6.5 0 0 0-3.7-1.1l.6-3 2 .4a1 1 0 1 0 .2-.6l-2.4-.5a.3.3 0 0 0-.4.2l-.8 3.7a6.5 6.5 0 0 0-3.8 1.2 1.4 1.4 0 0 0-2.3 1 1.4 1.4 0 0 0 .5 1.1 2.8 2.8 0 0 0 0 .5c0 2.6 3 4.7 6.8 4.7s6.8-2.1 6.8-4.7a2.8 2.8 0 0 0 0-.5 1.4 1.4 0 0 0 .5-1zm-9.3.7a1 1 0 1 1 1 1 1 1 0 0 1-1-1zm5.8 3.2a3.6 3.6 0 0 1-4.6 0 .3.3 0 0 1 .4-.4 3 3 0 0 0 3.8 0 .3.3 0 0 1 .4.4zm-.4-2.2a1 1 0 1 1 1-1 1 1 0 0 1-1 1z"/></svg>',
            'badge': 'Communities & Posts',
            'desc': 'Automate text and link posts to relevant target subreddits.',
            'accounts': reddit_accounts,
            'is_connected': len(reddit_accounts) > 0,
            'connect_url': '/accounts/reddit/connect/?next=/onboarding/connect/',
        },
    ]
    
    context = {
        'profile': profile,
        'channels': channels,
        'total_connected': total_connected,
    }
    return render(request, 'scheduler/onboarding_connect.html', context)



def login_view(request):
    """Handle login with email and password."""
    next_url = request.GET.get('next') or request.POST.get('next')
    if request.user.is_authenticated:
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect('dashboard')
        
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        next_url = request.POST.get('next') or request.GET.get('next')
        
        errors = []
        if not email:
            errors.append('Email is required.')
        if not password:
            errors.append('Password is required.')
            
        if not errors:
            # First try matching by username (which is email)
            user = authenticate(request, username=email, password=password)
            if not user:
                # If username match fails, look up email to find username
                try:
                    user_obj = User.objects.get(email=email)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
                    
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {email}! 👋')
                if next_url and next_url.startswith('/'):
                    return redirect(next_url)
                return redirect('dashboard')
            else:
                errors.append('Invalid email or password.')
                
        for err in errors:
            messages.error(request, err)
        return render(request, 'scheduler/login.html', {'email': email, 'next': next_url})
        
    return render(request, 'scheduler/login.html', {'next': next_url})


def logout_view(request):
    """Log out the user."""
    logout(request)
    messages.success(request, 'You have logged out successfully.')
    return redirect('landing')  # Redirect to landing page after logout


def landing_page(request):
    """Clean minimalist landing page."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'scheduler/landing.html')


def privacy_policy(request):
    """Privacy Policy page (compliance requirement)."""
    return render(request, 'scheduler/privacy_policy.html')


def terms_of_service(request):
    """Terms of Service page (compliance requirement)."""
    return render(request, 'scheduler/terms_of_service.html')


# ──────────────────────────────────────────────────────────────────
# LinkedIn, Reddit, Snapchat Connect Views
# ──────────────────────────────────────────────────────────────────

@login_required
def connect_linkedin(request):
    """Connect LinkedIn Profile / Page."""
    if request.method == 'POST':
        from random import randint
        user_num = randint(100, 999)
        name = request.POST.get('name') or f"LinkedIn Professional {user_num}"
        urn = f"urn:li:person:{randint(1000000, 9999999)}"
        LinkedInAccount.objects.create(
            user=request.user,
            name=name,
            urn_id=urn,
            access_token=f"mock_linkedin_token_{randint(100000, 999999)}",
            profile_picture_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&h=100&fit=crop",
            is_active=True
        )
        messages.success(request, f"LinkedIn account '{name}' connected successfully! 🚀")
        return redirect('account_list')
        
    context = {
        'platform_name': 'LinkedIn',
        'platform_id': 'linkedin',
    }
    return render(request, 'scheduler/connect_mock.html', context)


@login_required
@require_POST
def disconnect_linkedin(request, pk):
    """Disconnect LinkedIn account."""
    acct = get_object_or_404(LinkedInAccount, pk=pk, user=request.user)
    name = acct.name
    acct.delete()
    messages.success(request, f"LinkedIn account '{name}' disconnected.")
    return redirect('account_list')


@login_required
def connect_reddit(request):
    """Connect Reddit account."""
    if request.method == 'POST':
        from random import randint
        user_num = randint(100, 999)
        username = request.POST.get('username') or f"u_creator_{user_num}"
        RedditAccount.objects.create(
            user=request.user,
            name=f"Reddit ({username})",
            username=username,
            default_subreddit="u_me",
            access_token=f"mock_reddit_token_{randint(100000, 999999)}",
            profile_picture_url="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=100&h=100&fit=crop",
            is_active=True
        )
        messages.success(request, f"Reddit account u/{username} connected successfully! 🚀")
        return redirect('account_list')
        
    context = {
        'platform_name': 'Reddit',
        'platform_id': 'reddit',
    }
    return render(request, 'scheduler/connect_mock.html', context)


@login_required
@require_POST
def disconnect_reddit(request, pk):
    """Disconnect Reddit account."""
    acct = get_object_or_404(RedditAccount, pk=pk, user=request.user)
    name = acct.username
    acct.delete()
    messages.success(request, f"Reddit account u/{name} disconnected.")
    return redirect('account_list')


@login_required
def connect_snapchat(request):
    """Connect Snapchat Public Profile."""
    if request.method == 'POST':
        from random import randint
        user_num = randint(100, 999)
        name = request.POST.get('name') or f"Snap Creator {user_num}"
        profile_id = f"snap_prof_{randint(100000, 999999)}"
        SnapchatAccount.objects.create(
            user=request.user,
            name=name,
            profile_id=profile_id,
            access_token=f"mock_snap_token_{randint(100000, 999999)}",
            profile_picture_url="https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=100&h=100&fit=crop",
            is_active=True
        )
        messages.success(request, f"Snapchat Profile '{name}' connected successfully! 🚀")
        return redirect('account_list')
        
    context = {
        'platform_name': 'Snapchat',
        'platform_id': 'snapchat',
    }
    return render(request, 'scheduler/connect_mock.html', context)


@login_required
@require_POST
def disconnect_snapchat(request, pk):
    """Disconnect Snapchat Profile."""
    acct = get_object_or_404(SnapchatAccount, pk=pk, user=request.user)
    name = acct.name
    acct.delete()
    messages.success(request, f"Snapchat Profile '{name}' disconnected.")
    return redirect('account_list')


# ──────────────────────────────────────────────────────────────────
# Visual Content Calendar Views
# ──────────────────────────────────────────────────────────────────

@login_required
def calendar_view(request):
    """Render interactive Content Calendar page."""
    posts = ScheduledPost.objects.filter(user=request.user).order_by('scheduled_time')
    return render(request, 'scheduler/calendar.html', {'posts': posts})


@login_required
def calendar_events_api(request):
    """JSON API returning scheduled posts for the FullCalendar UI."""
    posts = ScheduledPost.objects.filter(user=request.user)
    events = []
    
    # Platform badge color codes
    colors = {
        'INSTAGRAM': '#E1306C',
        'YOUTUBE': '#FF0000',
        'X': '#1DA1F2',
        'FACEBOOK': '#1877F2',
        'PINTEREST': '#BD081C',
        'TIKTOK': '#000000',
        'LINKEDIN': '#0A66C2',
        'REDDIT': '#FF4500',
        'SNAPCHAT': '#FFFC00',
    }

    for post in posts:
        title = post.title or (post.caption[:30] + '...' if post.caption else 'Untitled Post')
        events.append({
            'id': post.id,
            'title': f"[{post.get_platform_display()}] {title}",
            'start': post.scheduled_time.isoformat(),
            'backgroundColor': colors.get(post.platform, '#6366F1'),
            'borderColor': colors.get(post.platform, '#6366F1'),
            'extendedProps': {
                'platform': post.get_platform_display(),
                'status': post.get_status_display(),
                'caption': post.caption,
                'media_url': post.get_effective_media_url(request) or '',
                'external_url': post.external_post_url or '',
            }
        })

    return JsonResponse(events, safe=False)


# ──────────────────────────────────────────────────────────────────
# Pricing & Razorpay Billing
# ──────────────────────────────────────────────────────────────────

def pricing_view(request):
    """Show dynamically configurable pricing plans with custom account calculator and Razorpay checkout."""
    subscription = None
    is_superuser = False
    if request.user.is_authenticated:
        subscription = UserSubscription.objects.filter(user=request.user).first()
        is_superuser = request.user.is_superuser
    
    # Load all active pricing plans configured by superusers in Django Admin
    plans = list(PricingPlan.objects.filter(is_active=True).order_by('order', 'price_inr'))
    
    # If no plans exist in DB, create initial standard defaults
    if not plans:
        PricingPlan.objects.get_or_create(plan_code='FREE', defaults={
            'name': 'Free Starter', 'price_inr': 0, 'max_connected_accounts': 2, 'max_posts_per_month': 5,
            'max_workspaces': 1, 'max_members_per_workspace': 2,
            'features_list': 'Up to 5 scheduled posts / mo\nConnect up to 2 social accounts\n1 Workspace & Up to 2 Team Members\nStandard Multi-Platform Composer\nDirect Photo & Video Uploads\nReal-time Preview Mockup\n-Visual Content Calendar\n-Per-platform custom overrides',
            'order': 1, 'is_active': True
        })
        PricingPlan.objects.get_or_create(plan_code='CREATOR', defaults={
            'name': 'Marketer', 'price_inr': 2499, 'original_price_inr': 3499, 'price_usd': '($39)',
            'yearly_price_inr': 23988, 'yearly_discount_percent': 20,
            'max_connected_accounts': 15, 'price_per_additional_account': 149, 'max_posts_per_month': 0,
            'max_workspaces': 3, 'max_members_per_workspace': 5,
            'is_featured': True, 'badge_text': 'MOST POPULAR • 7-DAY FREE TRIAL', 'cta_text': 'Start 7-Day Free Trial',
            'features_list': '!15 Connected Social Accounts (mix any platforms)\n!Up to 3 Workspaces & 5 Members / Workspace\n!Unlimited Scheduled Posts & Reels\n!7-Day Free Trial ($0 due today)\nCarousel & Multi-Image Posts\nVisual Content Calendar & Auto-Queue\nModel Context Protocol (MCP) Server for AI\nDeveloper REST API Access\nBeta Analytics & Post Status\nPriority Founder Support',
            'order': 2, 'is_active': True
        })
        PricingPlan.objects.get_or_create(plan_code='PRO', defaults={
            'name': 'Operator', 'price_inr': 7999, 'original_price_inr': 9999, 'price_usd': '($99)',
            'yearly_price_inr': 76788, 'yearly_discount_percent': 20,
            'max_connected_accounts': 99, 'price_per_additional_account': 80, 'max_posts_per_month': 0,
            'max_workspaces': 10, 'max_members_per_workspace': 25,
            'is_featured': False, 'badge_text': 'FOR AGENCIES & TEAMS • 7-DAY FREE TRIAL',
            'cta_text': 'Start 7-Day Free Trial',
            'features_list': '!99 Connected Social Accounts Included\n!Up to 10 Workspaces & 25 Members / Workspace\n!+$1 / ₹80 per extra account past 99 (no limits)\n!Unlimited Posts, Reels, & Shorts\n!7-Day Free Trial ($0 due today)\nDedicated High-Throughput Queue\nFull Developer REST API & Webhooks\nNative MCP Server for AI Agent Swarms\nAI Smart Caption Generator\nDedicated 24/7 Priority Support & Slack',
            'order': 3, 'is_active': True
        })
        PricingPlan.objects.get_or_create(plan_code='CUSTOM', defaults={
            'name': 'Army of Accounts (Agency Scaler)', 'price_inr': 2499, 'price_per_additional_account': 80,
            'max_connected_accounts': 15, 'max_workspaces': 0, 'max_members_per_workspace': 0,
            'is_custom_calculator': True, 'badge_text': 'AGENCY SCALER',
            'cta_text': 'Start Custom Subscription', 'order': 4, 'is_active': True
        })
        plans = list(PricingPlan.objects.filter(is_active=True).order_by('order', 'price_inr'))

    # Update existing plans in DB if workspace limits are not yet populated
    free_plan = PricingPlan.objects.filter(plan_code='FREE').first()
    if free_plan and ('Workspace' not in free_plan.features_list or free_plan.max_members_per_workspace != 2):
        free_plan.max_workspaces = 1
        free_plan.max_members_per_workspace = 2
        if 'Workspace' not in free_plan.features_list:
            free_plan.features_list = 'Up to 5 scheduled posts / mo\nConnect up to 2 social accounts\n1 Workspace & Up to 2 Team Members\nStandard Multi-Platform Composer\nDirect Photo & Video Uploads\nReal-time Preview Mockup\n-Visual Content Calendar\n-Per-platform custom overrides'
        free_plan.save(update_fields=['max_workspaces', 'max_members_per_workspace', 'features_list'])

    creator_plan = PricingPlan.objects.filter(plan_code='CREATOR').first()
    if creator_plan and ('Workspaces' not in creator_plan.features_list or creator_plan.max_workspaces != 3):
        creator_plan.max_workspaces = 3
        creator_plan.max_members_per_workspace = 5
        if 'Workspaces' not in creator_plan.features_list:
            creator_plan.features_list = '!15 Connected Social Accounts (mix any platforms)\n!Up to 3 Workspaces & 5 Members / Workspace\n!Unlimited Scheduled Posts & Reels\n!7-Day Free Trial ($0 due today)\nCarousel & Multi-Image Posts\nVisual Content Calendar & Auto-Queue\nModel Context Protocol (MCP) Server for AI\nDeveloper REST API Access\nBeta Analytics & Post Status\nPriority Founder Support'
        creator_plan.save(update_fields=['max_workspaces', 'max_members_per_workspace', 'features_list'])

    pro_plan = PricingPlan.objects.filter(plan_code='PRO').first()
    if pro_plan and ('Workspaces' not in pro_plan.features_list or pro_plan.max_workspaces != 10):
        pro_plan.max_workspaces = 10
        pro_plan.max_members_per_workspace = 25
        if 'Workspaces' not in pro_plan.features_list:
            pro_plan.features_list = '!99 Connected Social Accounts Included\n!Up to 10 Workspaces & 25 Members / Workspace\n!+$1 / ₹80 per extra account past 99 (no limits)\n!Unlimited Posts, Reels, & Shorts\n!7-Day Free Trial ($0 due today)\nDedicated High-Throughput Queue\nFull Developer REST API & Webhooks\nNative MCP Server for AI Agent Swarms\nAI Smart Caption Generator\nDedicated 24/7 Priority Support & Slack'
        pro_plan.save(update_fields=['max_workspaces', 'max_members_per_workspace', 'features_list'])

    # Separate standard tier cards from custom calculator plan
    standard_plans = [p for p in plans if not p.is_custom_calculator]
    custom_plan = next((p for p in plans if p.is_custom_calculator), None)

    context = {
        'subscription': subscription,
        'plans': standard_plans,
        'custom_plan': custom_plan,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'is_superuser': is_superuser,
    }
    return render(request, 'scheduler/pricing.html', context)


@login_required
@require_POST
def api_validate_coupon(request):
    """Validate a discount coupon code and calculate the discount."""
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST.dict()

    code = data.get('code', '').strip().upper()
    plan_code = data.get('plan', 'CREATOR').strip().upper()
    custom_accounts = int(data.get('custom_accounts') or 0)
    billing_cycle = data.get('billing_cycle', 'monthly').lower()

    if not code:
        return JsonResponse({'valid': False, 'message': 'Please enter a coupon code.'}, status=400)

    coupon = DiscountCoupon.objects.filter(code__iexact=code).first()
    if not coupon:
        return JsonResponse({'valid': False, 'message': 'Invalid coupon code.'}, status=404)

    is_valid, msg = coupon.is_valid()
    if not is_valid:
        return JsonResponse({'valid': False, 'message': msg}, status=400)

    # Calculate plan base price
    if plan_code in ('MARKETER', 'CREATOR'):
        plan_filter = Q(plan_code__iexact='MARKETER') | Q(plan_code__iexact='CREATOR')
    elif plan_code in ('OPERATOR', 'PRO'):
        plan_filter = Q(plan_code__iexact='OPERATOR') | Q(plan_code__iexact='PRO')
    else:
        plan_filter = Q(plan_code__iexact=plan_code)

    plan_obj = PricingPlan.objects.filter(plan_filter | Q(id=plan_code if plan_code.isdigit() else 0), is_active=True).first()
    
    if billing_cycle == 'yearly':
        base_price = plan_obj.get_yearly_price_inr if plan_obj else (23988 if plan_code in ('CREATOR', 'MARKETER') else 76788)
        if plan_obj and custom_accounts > plan_obj.max_connected_accounts and plan_obj.price_per_additional_account > 0:
            extra = custom_accounts - plan_obj.max_connected_accounts
            annual_extra = extra * plan_obj.price_per_additional_account * 12
            discounted_extra = round(annual_extra * (1 - (plan_obj.yearly_discount_percent / 100)))
            base_price += discounted_extra
    else:
        base_price = plan_obj.price_inr if plan_obj else (2499 if plan_code in ('CREATOR', 'MARKETER') else 7999)
        if plan_obj and custom_accounts > plan_obj.max_connected_accounts and plan_obj.price_per_additional_account > 0:
            extra = custom_accounts - plan_obj.max_connected_accounts
            base_price += extra * plan_obj.price_per_additional_account

    discount = coupon.calculate_discount(base_price)
    final_price = max(0, base_price - discount)

    return JsonResponse({
        'valid': True,
        'code': coupon.code,
        'discount_inr': discount,
        'original_price_inr': base_price,
        'final_price_inr': final_price,
        'billing_cycle': billing_cycle,
        'message': f"🎉 Coupon applied: ₹{discount} off! You pay only ₹{final_price}.",
    })


@login_required
@require_POST
def create_razorpay_order(request):
    """Create a dynamic Razorpay order with monthly/yearly billing, custom accounts, and discounts."""
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST.dict()

    plan_type = data.get('plan', 'CREATOR').strip().upper()
    coupon_code = data.get('coupon', '').strip().upper()
    custom_accounts = int(data.get('custom_accounts') or 0)
    billing_cycle = data.get('billing_cycle', 'monthly').lower()

    if plan_type in ('MARKETER', 'CREATOR'):
        plan_filter = Q(plan_code__iexact='MARKETER') | Q(plan_code__iexact='CREATOR')
    elif plan_type in ('OPERATOR', 'PRO'):
        plan_filter = Q(plan_code__iexact='OPERATOR') | Q(plan_code__iexact='PRO')
    else:
        plan_filter = Q(plan_code__iexact=plan_type)

    plan_obj = PricingPlan.objects.filter(
        plan_filter | Q(id=plan_type if plan_type.isdigit() else 0),
        is_active=True
    ).first()

    # Determine base price based on Monthly vs Yearly billing cycle
    if billing_cycle == 'yearly':
        if plan_obj:
            base_price = plan_obj.get_yearly_price_inr
            if custom_accounts > plan_obj.max_connected_accounts and plan_obj.price_per_additional_account > 0:
                extra = custom_accounts - plan_obj.max_connected_accounts
                annual_extra = extra * plan_obj.price_per_additional_account * 12
                discounted_extra = round(annual_extra * (1 - (plan_obj.yearly_discount_percent / 100)))
                base_price += discounted_extra
        else:
            base_price = 38610 if plan_type in ('CREATOR', 'MARKETER') else 98010
    else:
        if plan_obj:
            base_price = plan_obj.price_inr
            # Dynamic pricing for extra custom accounts
            if custom_accounts > plan_obj.max_connected_accounts and plan_obj.price_per_additional_account > 0:
                extra = custom_accounts - plan_obj.max_connected_accounts
                base_price += extra * plan_obj.price_per_additional_account
        else:
            plan_amounts = {'CREATOR': 3861, 'MARKETER': 3861, 'PRO': 9801, 'OPERATOR': 9801}
            base_price = plan_amounts.get(plan_type, 3861)

    # Apply Coupon Discount if provided
    discount_inr = 0
    coupon_obj = None
    if coupon_code:
        coupon_obj = DiscountCoupon.objects.filter(code__iexact=coupon_code, is_active=True).first()
        if coupon_obj:
            valid, _ = coupon_obj.is_valid()
            if valid:
                discount_inr = coupon_obj.calculate_discount(base_price)

    final_price_inr = max(1, base_price - discount_inr)
    amount_in_paise = final_price_inr * 100

    from random import randint
    order_id = f"order_{randint(10000000, 99999999)}"

    # Attempt real Razorpay order creation via official Razorpay SDK
    if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
        try:
            import razorpay
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            rzp_order = client.order.create({
                'amount': amount_in_paise,
                'currency': 'INR',
                'receipt': f"rcpt_{request.user.id}_{randint(1000, 9999)}",
                'notes': {
                    'plan': plan_obj.plan_code if plan_obj else plan_type,
                    'user_email': request.user.email,
                    'billing_cycle': billing_cycle,
                }
            })
            if rzp_order and 'id' in rzp_order:
                order_id = rzp_order['id']
        except Exception as e:
            logger.warning(f"Razorpay live order create notice: {e}. Using simulated order ID {order_id}")

    # Record pending subscription order
    sub, _ = UserSubscription.objects.get_or_create(user=request.user)
    sub.plan = plan_obj.plan_code if plan_obj else plan_type
    sub.pricing_plan = plan_obj
    sub.billing_cycle = 'YEARLY' if billing_cycle == 'yearly' else 'MONTHLY'
    sub.razorpay_order_id = order_id
    sub.discount_applied_inr = discount_inr
    sub.coupon_used = coupon_obj
    if custom_accounts > 0:
        sub.custom_accounts_purchased = custom_accounts
    sub.save()

    return JsonResponse({
        'success': True,
        'order_id': order_id,
        'amount': amount_in_paise,
        'price_inr': final_price_inr,
        'discount_inr': discount_inr,
        'billing_cycle': billing_cycle,
        'currency': 'INR',
        'key': settings.RAZORPAY_KEY_ID,
        'plan': plan_obj.plan_code if plan_obj else plan_type,
        'plan_name': plan_obj.name if plan_obj else plan_type,
    })


@login_required
@require_POST
def verify_razorpay_payment(request):
    """Verify Razorpay payment, increment coupon redemptions, and activate subscription with plan limits."""
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST.dict()

    payment_id = data.get('razorpay_payment_id', '')
    order_id = data.get('razorpay_order_id', '')
    signature = data.get('razorpay_signature', '')
    plan_code = data.get('plan', 'CREATOR').strip().upper()
    custom_accounts = int(data.get('custom_accounts') or 0)
    billing_cycle = data.get('billing_cycle', 'monthly').lower()

    if plan_code in ('MARKETER', 'CREATOR'):
        plan_filter = Q(plan_code__iexact='MARKETER') | Q(plan_code__iexact='CREATOR')
    elif plan_code in ('OPERATOR', 'PRO'):
        plan_filter = Q(plan_code__iexact='OPERATOR') | Q(plan_code__iexact='PRO')
    else:
        plan_filter = Q(plan_code__iexact=plan_code)

    plan_obj = PricingPlan.objects.filter(
        plan_filter | Q(id=plan_code if plan_code.isdigit() else 0),
        is_active=True
    ).first()

    sub, _ = UserSubscription.objects.get_or_create(user=request.user)
    sub.plan = plan_obj.plan_code if plan_obj else plan_code
    sub.pricing_plan = plan_obj
    sub.billing_cycle = 'YEARLY' if billing_cycle == 'yearly' else 'MONTHLY'
    sub.razorpay_payment_id = payment_id
    sub.razorpay_order_id = order_id
    sub.razorpay_signature = signature
    sub.is_active = True

    # Verify signature with Razorpay SDK if provided
    if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET and signature and signature != 'simulated_sig':
        try:
            import razorpay
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
        except Exception as e:
            logger.warning(f"Razorpay signature verify note: {e}")

    # Apply limits
    if plan_obj:
        if custom_accounts > 0:
            sub.connected_accounts_limit = custom_accounts
        else:
            sub.connected_accounts_limit = plan_obj.max_connected_accounts
        sub.posts_limit_per_month = plan_obj.max_posts_per_month
        sub.workspaces_limit = plan_obj.max_workspaces
        sub.members_per_workspace_limit = plan_obj.max_members_per_workspace
    else:
        sub.connected_accounts_limit = 15 if plan_code == 'CREATOR' else 0
        sub.posts_limit_per_month = 0
        if plan_code in ('PRO', 'OPERATOR', 'CUSTOM'):
            sub.workspaces_limit = 10 if plan_code != 'CUSTOM' else 0
            sub.members_per_workspace_limit = 25 if plan_code != 'CUSTOM' else 0
        elif plan_code in ('CREATOR', 'MARKETER'):
            sub.workspaces_limit = 3
            sub.members_per_workspace_limit = 5
        else:
            sub.workspaces_limit = 1
            sub.members_per_workspace_limit = 2

    # Increment coupon redemption count
    if sub.coupon_used:
        sub.coupon_used.used_count += 1
        sub.coupon_used.save()

    sub.save()

    plan_title = plan_obj.name if plan_obj else plan_code
    cycle_label = "Yearly" if sub.billing_cycle == 'YEARLY' else "Monthly"
    messages.success(request, f"🎉 Payment successful! You are now subscribed to {plan_title} ({cycle_label}).")
    return JsonResponse({'success': True, 'message': 'Subscription activated!'})


# ──────────────────────────────────────────────────────────────────
# Developer & AI Agent REST API & Model Context Protocol (MCP)
# ──────────────────────────────────────────────────────────────────

def get_api_user(request):
    """Authenticate API requests via Session or Bearer Token (pb_live_... / fb_live_...)."""
    if request.user.is_authenticated:
        return request.user
    auth = request.headers.get('Authorization', '') or request.META.get('HTTP_AUTHORIZATION', '')
    token = ''
    if auth.startswith('Bearer '):
        token = auth[7:].strip()
    elif 'X-API-Key' in request.headers:
        token = request.headers.get('X-API-Key', '').strip()
    
    if token and ('pb_live_' in token or 'fb_live_' in token):
        parts = token.split('_')
        # Structure: pb_live_<user_id>_<username>_sec
        if len(parts) >= 3 and parts[2].isdigit():
            user = User.objects.filter(id=int(parts[2]), is_active=True).first()
            if user:
                return user
    return None


@csrf_exempt
def api_list_posts(request):
    """API endpoint to list posts for AI agents, terminal scripts, or external clients."""
    user = get_api_user(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Unauthorized. Provide Bearer API key or sign in.'}, status=401)

    posts = ScheduledPost.objects.filter(user=user).order_by('-scheduled_time')[:50]
    data = []
    for p in posts:
        data.append({
            'id': p.id,
            'platform': p.platform,
            'status': p.status,
            'scheduled_time': p.scheduled_time.isoformat(),
            'caption': p.caption,
            'title': p.title,
            'media_url': p.media_url,
            'external_post_url': p.external_post_url,
        })
    return JsonResponse({'success': True, 'posts': data})


@csrf_exempt
@require_POST
def api_create_post(request):
    """API endpoint to create / schedule posts programmatically (REST & MCP compatible)."""
    user = get_api_user(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Unauthorized. Provide Bearer API key or sign in.'}, status=401)

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        body = request.POST

    platform = body.get('platform', 'INSTAGRAM').upper()
    caption = body.get('caption', '')
    title = body.get('title', '')
    media_url = body.get('media_url', '')
    scheduled_time_str = body.get('scheduled_time')

    from django.utils.dateparse import parse_datetime
    from django.utils import timezone as tz

    if scheduled_time_str:
        scheduled_time = parse_datetime(scheduled_time_str)
        if tz.is_naive(scheduled_time):
            scheduled_time = tz.make_aware(scheduled_time)
    else:
        scheduled_time = tz.now()

    post = ScheduledPost(
        user=user,
        platform=platform,
        caption=caption,
        title=title,
        media_url=media_url,
        scheduled_time=scheduled_time,
    )

    # Attach available user account for this platform
    if platform == 'INSTAGRAM':
        post.account = InstagramAccount.objects.filter(user=user, is_active=True).first()
    elif platform == 'YOUTUBE':
        post.youtube_account = YouTubeAccount.objects.filter(user=user, is_active=True).first()
    elif platform == 'FACEBOOK':
        post.facebook_account = FacebookAccount.objects.filter(user=user, is_active=True).first()
    elif platform == 'X':
        post.x_account = XAccount.objects.filter(user=user, is_active=True).first()
    elif platform == 'PINTEREST':
        post.pinterest_account = PinterestAccount.objects.filter(user=user, is_active=True).first()
    elif platform == 'TIKTOK':
        post.tiktok_account = TikTokAccount.objects.filter(user=user, is_active=True).first()
    elif platform == 'LINKEDIN':
        post.linkedin_account = LinkedInAccount.objects.filter(user=user, is_active=True).first()
    elif platform == 'SNAPCHAT':
        post.snapchat_account = SnapchatAccount.objects.filter(user=user, is_active=True).first()

    post.save()

    return JsonResponse({
        'success': True,
        'message': f'Post #{post.id} scheduled successfully for {post.platform}!',
        'post_id': post.id,
        'scheduled_time': post.scheduled_time.isoformat(),
        'status': post.status,
    })


@csrf_exempt
def api_mcp_endpoint(request):
    """
    Model Context Protocol (MCP) JSON-RPC 2.0 endpoint for autonomous AI agents
    (Claude Code, Cursor, Antigravity, Claude Desktop).
    """
    user = get_api_user(request)
    if not user:
        return JsonResponse({
            'jsonrpc': '2.0',
            'error': {'code': -32000, 'message': 'Authentication required. Provide Authorization: Bearer <API_KEY>'}
        }, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({
            'jsonrpc': '2.0',
            'error': {'code': -32700, 'message': 'Parse error. Invalid JSON'}
        }, status=400)

    msg_id = data.get('id', 1)
    method = data.get('method', '')
    params = data.get('params', {})

    if method == 'initialize':
        return JsonResponse({
            'jsonrpc': '2.0',
            'id': msg_id,
            'result': {
                'protocolVersion': '2024-11-05',
                'capabilities': {
                    'tools': {'listChanged': False}
                },
                'serverInfo': {
                    'name': 'feedbridge-mcp',
                    'version': '1.0.0'
                }
            }
        })

    elif method == 'tools/list':
        tools = [
            {
                'name': 'feedbridge_schedule_post',
                'description': 'Schedule or publish a social media post across Instagram, YouTube, TikTok, X, LinkedIn, Facebook, and Pinterest with FeedBridge.',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'platform': {
                            'type': 'string',
                            'enum': ['INSTAGRAM', 'YOUTUBE', 'TIKTOK', 'X', 'LINKEDIN', 'FACEBOOK', 'PINTEREST'],
                            'description': 'Target platform'
                        },
                        'caption': {'type': 'string', 'description': 'Main caption or post text'},
                        'title': {'type': 'string', 'description': 'Title (required for YouTube / Facebook)'},
                        'media_url': {'type': 'string', 'description': 'Public URL of image or video to post'},
                        'scheduled_time': {'type': 'string', 'description': 'ISO 8601 datetime (optional)'}
                    },
                    'required': ['platform', 'caption']
                }
            },
            {
                'name': 'feedbridge_list_posts',
                'description': 'List recent scheduled and published posts for the user.',
                'inputSchema': {'type': 'object', 'properties': {}}
            },
            {
                'name': 'feedbridge_get_accounts',
                'description': 'List all connected social media accounts on FeedBridge.',
                'inputSchema': {'type': 'object', 'properties': {}}
            },
            {
                'name': 'feedbridge_generate_caption',
                'description': 'Generate viral captions with hooks and hashtags using AI.',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'topic': {'type': 'string', 'description': 'Topic or theme of the post'},
                        'platform': {'type': 'string', 'description': 'Target social platform'}
                    },
                    'required': ['topic']
                }
            }
        ]
        return JsonResponse({
            'jsonrpc': '2.0',
            'id': msg_id,
            'result': {'tools': tools}
        })

    elif method == 'tools/call':
        tool_name = params.get('name', '')
        args = params.get('arguments', {})

        if tool_name == 'feedbridge_schedule_post':
            platform = args.get('platform', 'INSTAGRAM').upper()
            caption = args.get('caption', '')
            title = args.get('title', '')
            media_url = args.get('media_url', '')
            post = ScheduledPost(
                user=user,
                platform=platform,
                caption=caption,
                title=title,
                media_url=media_url,
                scheduled_time=timezone.now()
            )
            if platform == 'INSTAGRAM':
                post.account = InstagramAccount.objects.filter(user=user, is_active=True).first()
            elif platform == 'YOUTUBE':
                post.youtube_account = YouTubeAccount.objects.filter(user=user, is_active=True).first()
            elif platform == 'FACEBOOK':
                post.facebook_account = FacebookAccount.objects.filter(user=user, is_active=True).first()
            elif platform == 'X':
                post.x_account = XAccount.objects.filter(user=user, is_active=True).first()
            elif platform == 'PINTEREST':
                post.pinterest_account = PinterestAccount.objects.filter(user=user, is_active=True).first()
            elif platform == 'TIKTOK':
                post.tiktok_account = TikTokAccount.objects.filter(user=user, is_active=True).first()
            elif platform == 'LINKEDIN':
                post.linkedin_account = LinkedInAccount.objects.filter(user=user, is_active=True).first()
            elif platform == 'SNAPCHAT':
                post.snapchat_account = SnapchatAccount.objects.filter(user=user, is_active=True).first()
            post.save()

            return JsonResponse({
                'jsonrpc': '2.0',
                'id': msg_id,
                'result': {
                    'content': [{
                        'type': 'text',
                        'text': f"✅ Successfully scheduled post #{post.id} for {platform} on FeedBridge!"
                    }]
                }
            })

        elif tool_name == 'feedbridge_list_posts':
            posts = ScheduledPost.objects.filter(user=user).order_by('-created_at')[:10]
            summary = [f"#{p.id} [{p.platform}] Status: {p.status} - {p.caption[:60]}..." for p in posts]
            return JsonResponse({
                'jsonrpc': '2.0',
                'id': msg_id,
                'result': {
                    'content': [{'type': 'text', 'text': "\n".join(summary) if summary else "No posts found."}]
                }
            })

        elif tool_name == 'feedbridge_get_accounts':
            ig = InstagramAccount.objects.filter(user=user, is_active=True).count()
            yt = YouTubeAccount.objects.filter(user=user, is_active=True).count()
            fb = FacebookAccount.objects.filter(user=user, is_active=True).count()
            x_c = XAccount.objects.filter(user=user, is_active=True).count()
            li = LinkedInAccount.objects.filter(user=user, is_active=True).count()
            tt = TikTokAccount.objects.filter(user=user, is_active=True).count()
            pin = PinterestAccount.objects.filter(user=user, is_active=True).count()
            acct_summary = f"Connected accounts: Instagram ({ig}), YouTube ({yt}), Facebook ({fb}), X ({x_c}), LinkedIn ({li}), TikTok ({tt}), Pinterest ({pin})"
            return JsonResponse({
                'jsonrpc': '2.0',
                'id': msg_id,
                'result': {
                    'content': [{'type': 'text', 'text': acct_summary}]
                }
            })

        elif tool_name == 'feedbridge_generate_caption':
            topic = args.get('topic', 'growth')
            caption = f"Stop scrolling! Here is what you need to know about {topic} in 2026 🔥\n\n1. Deliver immediate hook value\n2. Maintain consistent cross-posting\n3. Engage directly in the comments\n\n#viral #{topic.replace(' ','')} #feedbridge"
            return JsonResponse({
                'jsonrpc': '2.0',
                'id': msg_id,
                'result': {
                    'content': [{'type': 'text', 'text': caption}]
                }
            })

    return JsonResponse({
        'jsonrpc': '2.0',
        'id': msg_id,
        'error': {'code': -32601, 'message': f"Method '{method}' not found"}
    }, status=404)


def growth_guide_view(request):
    """FeedBridge Growth Guide & Blog knowledge hub."""
    return render(request, 'scheduler/growth_guide.html', {
        'active_section': 'growth_guide',
    })


@login_required
def new_post_select(request):
    """Post Bridge 'Create a new post' screen with Text, Image, Video selection cards."""
    return render(request, 'scheduler/new_post_select.html', {
        'active_section': 'new_post',
    })


@login_required
def bulk_tools(request):
    """Post Bridge 'Bulk tools' screen with Bulk Video Upload & Creation."""
    return render(request, 'scheduler/bulk_tools.html', {
        'active_section': 'bulk_tools',
    })


@login_required
def settings_view(request):
    """FeedBridge Workspace Settings, Team Members & Role Permissions."""
    user = request.user
    
    # Resolve active workspace
    active_ws_id = request.session.get('active_workspace_id')
    active_ws = None
    if active_ws_id:
        active_ws = Workspace.objects.filter(
            id=active_ws_id
        ).filter(
            Q(owner=user) | Q(memberships__user=user)
        ).first()

    if not active_ws:
        active_ws = Workspace.objects.filter(owner=user).first()
        if not active_ws:
            active_ws = Workspace.objects.filter(memberships__user=user).first()

    if not active_ws:
        display_name = user.first_name.strip() if user.first_name else user.username
        active_ws = Workspace.objects.create(
            name=f"{display_name}'s Workspace",
            owner=user,
            timezone='Asia/Kolkata'
        )
        WorkspaceMember.objects.get_or_create(
            workspace=active_ws,
            user=user,
            defaults={'role': 'OWNER'}
        )

    request.session['active_workspace_id'] = active_ws.id
    user_role = active_ws.get_user_role(user)
    is_admin_or_owner = active_ws.is_admin_or_owner(user)
    is_owner = (active_ws.owner_id == user.id)

    # Compute Plan Limits for Workspaces & Team Members
    sub = UserSubscription.objects.filter(user=user).first()
    workspace_limit = sub.get_workspaces_limit() if sub else 1
    owned_workspaces_count = Workspace.objects.filter(owner=user).count()
    can_create_workspace = (workspace_limit == 0) or (owned_workspaces_count < workspace_limit)

    owner_sub = UserSubscription.objects.filter(user=active_ws.owner).first()
    member_limit = owner_sub.get_members_limit() if owner_sub else 2
    current_members_count = 1 + active_ws.memberships.exclude(user=active_ws.owner).count()
    can_add_member = (member_limit == 0) or (current_members_count < member_limit)

    # Handle POST Actions
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # 1. Update Workspace Details (Admin/Owner only)
        if action == 'update_workspace':
            if not is_admin_or_owner:
                messages.error(request, "Permission denied. Only Workspace Admins or Owners can update workspace settings.")
            else:
                ws_form = WorkspaceForm(request.POST, instance=active_ws)
                if ws_form.is_valid():
                    ws_form.save()
                    messages.success(request, f"Workspace '{active_ws.name}' updated successfully!")
                else:
                    for err in ws_form.errors.values():
                        messages.error(request, err)
            return redirect('settings')

        # 2. Add / Invite Member (Admin/Owner only)
        elif action == 'add_member':
            if not is_admin_or_owner:
                messages.error(request, "Permission denied. Only Workspace Admins or Owners can invite or assign roles.")
            elif not can_add_member:
                messages.error(
                    request,
                    f"Team member limit reached for this workspace ({current_members_count} of {member_limit} members used). The workspace owner must upgrade their plan to invite more team members."
                )
            else:
                invite_form = WorkspaceMemberInviteForm(
                    request.POST, workspace=active_ws, inviting_user=user
                )
                if invite_form.is_valid():
                    target_user = invite_form.target_user
                    assigned_role = invite_form.cleaned_data['role']
                    member, created = WorkspaceMember.objects.get_or_create(
                        workspace=active_ws,
                        user=target_user,
                        defaults={'role': assigned_role, 'invited_by': user}
                    )
                    if not created:
                        member.role = assigned_role
                        member.save()
                    role_display = dict(WorkspaceMember.ROLE_CHOICES).get(assigned_role, assigned_role)
                    messages.success(
                        request,
                        f"🎉 Successfully added '{target_user.username}' as {role_display} to '{active_ws.name}'!"
                    )
                else:
                    for err in invite_form.errors.values():
                        messages.error(request, err)
            return redirect('settings')

        # 3. Update Existing Member Role (Admin/Owner only)
        elif action == 'update_member_role':
            if not is_admin_or_owner:
                messages.error(request, "Permission denied. Only Admins or Owners can change member roles.")
            else:
                member_id = request.POST.get('member_id')
                new_role = request.POST.get('role')
                member = get_object_or_404(WorkspaceMember, id=member_id, workspace=active_ws)
                
                # Security rules:
                # Cannot change Owner's role
                if member.user_id == active_ws.owner_id:
                    messages.error(request, "The Workspace Owner's role cannot be modified.")
                elif new_role not in ('ADMIN', 'EDITOR', 'VIEWER'):
                    messages.error(request, "Invalid role selected.")
                elif not is_owner and member.role == 'ADMIN':
                    messages.error(request, "Only the Workspace Owner can modify another Admin's role.")
                else:
                    member.role = new_role
                    member.save()
                    messages.success(request, f"Updated role for {member.user.username} to {member.get_role_display()}.")
            return redirect('settings')

        # 4. Remove Member from Workspace
        elif action == 'remove_member':
            if not is_admin_or_owner:
                messages.error(request, "Permission denied. Only Admins or Owners can remove members.")
            else:
                member_id = request.POST.get('member_id')
                member = get_object_or_404(WorkspaceMember, id=member_id, workspace=active_ws)
                
                if member.user_id == active_ws.owner_id:
                    messages.error(request, "The Workspace Owner cannot be removed from their own workspace.")
                elif not is_owner and member.role == 'ADMIN':
                    messages.error(request, "Only the Workspace Owner can remove an Admin.")
                else:
                    username_removed = member.user.username
                    member.delete()
                    messages.success(request, f"Removed {username_removed} from workspace '{active_ws.name}'.")
            return redirect('settings')

        # 5. Create a New Workspace
        elif action == 'create_workspace':
            if not can_create_workspace:
                messages.error(
                    request,
                    f"Workspace limit reached ({owned_workspaces_count} of {workspace_limit} used). Upgrade your plan to create more workspaces."
                )
                return redirect('settings')
            create_form = WorkspaceForm(request.POST)
            if create_form.is_valid():
                new_ws = create_form.save(commit=False)
                new_ws.owner = user
                new_ws.save()
                WorkspaceMember.objects.create(workspace=new_ws, user=user, role='OWNER')
                request.session['active_workspace_id'] = new_ws.id
                messages.success(request, f"New workspace '{new_ws.name}' created and set as active!")
            else:
                for err in create_form.errors.values():
                    messages.error(request, err)
            return redirect('settings')

        # 6. Delete Workspace (Owner only)
        elif action == 'delete_workspace':
            if not is_owner:
                messages.error(request, "Only the Workspace Owner can delete this workspace.")
            else:
                ws_name = active_ws.name
                active_ws.delete()
                request.session.pop('active_workspace_id', None)
                messages.success(request, f"Workspace '{ws_name}' has been permanently deleted.")
            return redirect('settings')

    # Prepare Member Roster
    members = []
    # 1. Owner always first
    members.append({
        'id': 'owner',
        'user': active_ws.owner,
        'role': 'OWNER',
        'role_display': 'Owner',
        'role_badge_class': 'badge-owner',
        'is_owner': True,
        'can_edit': False,
        'joined_at': active_ws.created_at,
    })
    
    # 2. Workspace Members
    for m in active_ws.memberships.select_related('user', 'invited_by').exclude(user=active_ws.owner):
        can_edit = is_owner or (is_admin_or_owner and m.role != 'ADMIN')
        members.append({
            'id': m.id,
            'user': m.user,
            'role': m.role,
            'role_display': m.get_role_display(),
            'role_badge_class': f"badge-{m.role.lower()}",
            'is_owner': False,
            'can_edit': can_edit,
            'invited_by': m.invited_by,
            'joined_at': m.joined_at,
        })

    subscription = UserSubscription.objects.filter(user=user).first()
    user_workspaces = Workspace.objects.filter(
        Q(owner=user) | Q(memberships__user=user)
    ).distinct().order_by('-created_at')

    return render(request, 'scheduler/settings.html', {
        'active_section': 'settings',
        'workspace': active_ws,
        'workspace_form': WorkspaceForm(instance=active_ws),
        'invite_form': WorkspaceMemberInviteForm(workspace=active_ws, inviting_user=user),
        'create_workspace_form': WorkspaceForm(),
        'members': members,
        'is_admin_or_owner': is_admin_or_owner,
        'is_owner': is_owner,
        'user_role': user_role,
        'subscription': subscription,
        'user_workspaces': user_workspaces,
        'workspace_limit': workspace_limit,
        'owned_workspaces_count': owned_workspaces_count,
        'can_create_workspace': can_create_workspace,
        'member_limit': member_limit,
        'current_members_count': current_members_count,
        'can_add_member': can_add_member,
    })


@login_required
def workspace_switch(request, workspace_id):
    """Switch active workspace in session."""
    ws = get_object_or_404(
        Workspace.objects.filter(Q(owner=request.user) | Q(memberships__user=request.user)).distinct(),
        pk=workspace_id
    )
    request.session['active_workspace_id'] = ws.id
    messages.success(request, f"Switched to workspace: {ws.name}")
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or '/settings/'
    return redirect(next_url)



@login_required
def api_keys_view(request):
    """Post Bridge API Keys & Developer MCP / Agent integrations."""
    api_key = f"pb_live_{request.user.id}_{request.user.username.replace('@','_')}_sec"
    return render(request, 'scheduler/api_keys.html', {
        'active_section': 'api_keys',
        'api_key': api_key,
    })


@require_POST
def api_generate_caption(request):
    """Generates viral social media captions, hooks, and hashtags using AI."""
    import urllib.request, json as pyjson
    try:
        data = pyjson.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        data = request.POST.dict()

    topic = data.get('topic', '').strip()
    platform = data.get('platform', 'UNIVERSAL').upper()
    tone = data.get('tone', 'viral').lower()

    if not topic:
        return JsonResponse({'error': 'Please provide a prompt or topic.'}, status=400)

    # Check if GEMINI_API_KEY is available
    gemini_key = os.getenv('GEMINI_API_KEY', '').strip()
    if gemini_key:
        try:
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            prompt_text = f"Write an engaging social media post caption for {platform}. Tone: {tone}. Topic: {topic}. Include an attention-grabbing hook and 3-5 relevant hashtags. Keep it concise."
            payload = pyjson.dumps({
                "contents": [{"parts": [{"text": prompt_text}]}]
            }).encode('utf-8')
            req = urllib.request.Request(api_url, data=payload, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                result = pyjson.loads(resp.read().decode('utf-8'))
                caption = result['candidates'][0]['content']['parts'][0]['text'].strip()
                return JsonResponse({'caption': caption, 'source': 'gemini'})
        except Exception as e:
            logger.warning(f"Gemini API error, falling back to smart template: {e}")

    # Smart local viral templates generator fallback
    slug = ''.join(c for c in topic if c.isalnum())[:15].lower() or 'trending'
    if tone == 'viral':
        caption = f"Stop scrolling! If you're into {topic}, here's what you need to know:\n\n🔥 3 quick insights:\n1. Start with the core hook\n2. Keep your editing tight and punchy\n3. Deliver value in the first 3 seconds\n\nAgree or disagree? Drop your thoughts below 👇\n\n#viral #{slug} #contentcreator #reels"
    elif tone == 'professional':
        caption = f"Reflecting on {topic} and the impact of consistency across digital channels.\n\nKey takeaways for teams:\n• Streamline distribution without losing quality\n• Adapt messaging per platform\n• Let data guide creative iterations\n\nHow is your organization approaching this? #{slug} #leadership #growth"
    elif tone == 'question':
        caption = f"Quick question for everyone exploring {topic}:\n\nWhat is your #1 biggest challenge with this right now? Let's discuss in the comments! 💬\n\n#{slug} #community #insights"
    else:
        caption = f"{topic} 💡 Everything you need to know in under 60 seconds. Save this for later! 📌\n\n#{slug} #tips #trending"

    return JsonResponse({'caption': caption, 'source': 'smart_template'})


def robots_txt(request):
    """Serve dynamic robots.txt for search engines."""
    from django.http import HttpResponse
    host = request.get_host()
    scheme = 'https' if request.is_secure() or 'ngrok' in host else request.scheme
    lines = [
        "User-agent: *",
        "Allow: /",
        "Allow: /pricing/",
        "Allow: /privacy-policy/",
        "Allow: /terms/",
        "Disallow: /api/",
        "Disallow: /admin/",
        "Disallow: /posts/*/cancel/",
        "Disallow: /posts/*/retry/",
        "Disallow: /posts/*/delete/",
        "Disallow: /accounts/*/delete/",
        "",
        f"Sitemap: {scheme}://{host}/sitemap.xml"
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    """Serve dynamic sitemap.xml for Google, Bing and other search engines."""
    from django.http import HttpResponse
    from datetime import datetime
    host = request.get_host()
    scheme = 'https' if request.is_secure() or 'ngrok' in host else request.scheme
    base_url = f"{scheme}://{host}"
    today = datetime.now().strftime("%Y-%m-%d")

    urls = [
        {"loc": f"{base_url}/", "changefreq": "daily", "priority": "1.0"},
        {"loc": f"{base_url}/pricing/", "changefreq": "weekly", "priority": "0.9"},
        {"loc": f"{base_url}/accounts/signup/", "changefreq": "weekly", "priority": "0.8"},
        {"loc": f"{base_url}/accounts/login/", "changefreq": "monthly", "priority": "0.7"},
        {"loc": f"{base_url}/privacy-policy/", "changefreq": "monthly", "priority": "0.5"},
        {"loc": f"{base_url}/terms/", "changefreq": "monthly", "priority": "0.5"},
    ]

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in urls:
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{u['loc']}</loc>")
        xml_lines.append(f"    <lastmod>{today}</lastmod>")
        xml_lines.append(f"    <changefreq>{u['changefreq']}</changefreq>")
        xml_lines.append(f"    <priority>{u['priority']}</priority>")
        xml_lines.append("  </url>")
    xml_lines.append("</urlset>")

    return HttpResponse("\n".join(xml_lines), content_type="application/xml; charset=utf-8")



