"""
Background tasks for the Instagram Post Scheduler.

Uses APScheduler to run periodic tasks:
1. Process scheduled posts (every minute)
2. Refresh expiring tokens (daily)
3. Check processing posts (every 2 minutes)
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from django.utils import timezone
from django_apscheduler.jobstores import DjangoJobStore

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), "default")


def process_scheduled_posts():
    """
    Check for posts that are due to be published and process them.
    Runs every minute.
    """
    from scheduler.models import ScheduledPost
    from scheduler.services import instagram_api
    
    now = timezone.now()
    pending_posts = ScheduledPost.objects.filter(
        status='PENDING',
        scheduled_time__lte=now,
        account__is_active=True,
    ).select_related('account')
    
    for post in pending_posts:
        logger.info(f"Processing post {post.id}: {post.post_type} for {post.account.name}")
        
        # Check token validity
        if post.account.token_status in ('expired', 'missing'):
            post.status = 'FAILED'
            post.error_message = 'Access token is expired or missing. Please refresh the token.'
            post.save(update_fields=['status', 'error_message'])
            continue
        
        # Get media URL
        media_url = post.media_url or ''
        # For local URLs, Instagram API cannot reach them
        if '127.0.0.1' in media_url or 'localhost' in media_url:
            post.status = 'FAILED'
            post.error_message = (
                'Instagram cannot download files from localhost. '
                'Please use a public URL (e.g. via ngrok or hosted image).'
            )
            post.save(update_fields=['status', 'error_message'])
            continue
        
        if not media_url:
            post.status = 'FAILED'
            post.error_message = 'No media URL provided.'
            post.save(update_fields=['status', 'error_message'])
            continue
        
        try:
            if post.post_type == 'IMAGE':
                post.status = 'PROCESSING'
                post.save(update_fields=['status'])
                
                result = instagram_api.publish_image(
                    post.account, 
                    media_url, 
                    post.caption
                )
            elif post.post_type == 'REEL':
                post.status = 'PROCESSING'
                post.save(update_fields=['status'])
                
                cover_url = post.thumbnail_url or ''
                result = instagram_api.publish_reel(
                    post.account,
                    media_url,
                    post.caption,
                    cover_url=cover_url if cover_url else None,
                )
            else:
                post.status = 'FAILED'
                post.error_message = f'Unknown post type: {post.post_type}'
                post.save(update_fields=['status', 'error_message'])
                continue
            
            if result['success']:
                post.status = 'PUBLISHED'
                post.ig_container_id = result.get('container_id', '')
                post.ig_media_id = result.get('media_id', '')
                post.published_at = timezone.now()
                post.error_message = ''
                post.save(update_fields=[
                    'status', 'ig_container_id', 'ig_media_id', 
                    'published_at', 'error_message'
                ])
                logger.info(f"Post {post.id} published successfully! Media ID: {post.ig_media_id}")
            else:
                post.status = 'FAILED'
                post.ig_container_id = result.get('container_id', '')
                post.error_message = result.get('error', 'Unknown publishing error')
                post.save(update_fields=['status', 'ig_container_id', 'error_message'])
                logger.error(f"Post {post.id} failed: {post.error_message}")
                
        except Exception as e:
            post.status = 'FAILED'
            post.error_message = f'Unexpected error: {str(e)}'
            post.save(update_fields=['status', 'error_message'])
            logger.exception(f"Unexpected error processing post {post.id}")


def refresh_expiring_tokens():
    """
    Check all accounts and refresh tokens approaching expiry.
    Runs daily.
    """
    from scheduler.services.token_manager import auto_refresh_all_tokens
    
    logger.info("Running token refresh check...")
    results = auto_refresh_all_tokens()
    for r in results:
        if r['result']['success']:
            logger.info(f"Token refreshed for: {r['account']}")
        else:
            logger.error(f"Token refresh failed for {r['account']}: {r['result'].get('error')}")


def start_scheduler():
    """Start the APScheduler with all jobs."""
    try:
        # Process scheduled posts EXACTLY on the minute mark (at second 0)
        scheduler.add_job(
            process_scheduled_posts,
            trigger=CronTrigger(second=0),
            id="process_scheduled_posts",
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Added job: process_scheduled_posts (every minute exactly at 0s)")
        
        # Refresh tokens daily
        scheduler.add_job(
            refresh_expiring_tokens,
            trigger=IntervalTrigger(hours=24),
            id="refresh_expiring_tokens",
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Added job: refresh_expiring_tokens (every 24h)")
        
        scheduler.start()
        logger.info("APScheduler started successfully!")
        
    except Exception as e:
        logger.exception(f"Failed to start scheduler: {e}")
