import json
import logging

from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import InstagramAccountForm, ScheduledPostForm, TokenExchangeForm
from .models import InstagramAccount, ScheduledPost
from .services import token_manager

logger = logging.getLogger(__name__)


def dashboard(request):
    """Main dashboard with overview stats."""
    accounts = InstagramAccount.objects.filter(is_active=True)
    
    # Stats
    total_accounts = accounts.count()
    total_pending = ScheduledPost.objects.filter(status='PENDING').count()
    total_processing = ScheduledPost.objects.filter(status='PROCESSING').count()
    total_published = ScheduledPost.objects.filter(status='PUBLISHED').count()
    total_failed = ScheduledPost.objects.filter(status='FAILED').count()
    
    # Recent posts
    recent_posts = ScheduledPost.objects.select_related('account').order_by('-created_at')[:10]
    
    # Upcoming posts
    upcoming_posts = ScheduledPost.objects.filter(
        status='PENDING',
        scheduled_time__gte=timezone.now(),
    ).select_related('account').order_by('scheduled_time')[:5]
    
    context = {
        'accounts': accounts,
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
    """Create a new scheduled post."""
    if request.method == 'POST':
        form = ScheduledPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.save()
            
            # If files were uploaded, generate the absolute URLs for them 
            # so the background task has a fully-qualified URL to send to Instagram.
            updated = False
            if post.media_file and not post.media_url:
                post.media_url = request.build_absolute_uri(post.media_file.url)
                updated = True
                
            if post.thumbnail_file and not post.thumbnail_url:
                post.thumbnail_url = request.build_absolute_uri(post.thumbnail_file.url)
                updated = True
                
            if updated:
                post.save(update_fields=['media_url', 'thumbnail_url'])
                
            messages.success(request, f'Post scheduled for {post.scheduled_time.strftime("%b %d, %Y %I:%M %p")}')
            return redirect('post_list')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = ScheduledPostForm()
    
    accounts = InstagramAccount.objects.filter(is_active=True)
    context = {
        'form': form,
        'accounts': accounts,
    }
    return render(request, 'scheduler/create_post.html', context)


def post_list(request):
    """List all scheduled posts with filtering."""
    status_filter = request.GET.get('status', 'all')
    type_filter = request.GET.get('type', 'all')
    
    posts = ScheduledPost.objects.select_related('account').all()
    
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
    """Manage Instagram accounts."""
    accounts = InstagramAccount.objects.all()
    context = {
        'accounts': accounts,
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
        post.scheduled_time = timezone.now()
        post.save(update_fields=[
            'status', 'error_message', 'ig_container_id', 
            'ig_media_id', 'scheduled_time'
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
