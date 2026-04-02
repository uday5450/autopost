"""
Background tasks for the Post Scheduler.

Uses APScheduler to run periodic tasks:
1. Process scheduled posts (every minute) — Instagram + YouTube
2. Refresh expiring tokens (daily)
"""

import logging
import os

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
    Handles both Instagram and YouTube posts.
    Runs every minute.
    """
    from scheduler.models import ScheduledPost
    from scheduler.services import instagram_api
    
    now = timezone.now()

    # ── Instagram Posts ──────────────────────────────────────────
    ig_posts = ScheduledPost.objects.filter(
        platform='INSTAGRAM',
        status='PENDING',
        scheduled_time__lte=now,
        account__isnull=False,
        account__is_active=True,
    ).select_related('account')

    for post in ig_posts:
        logger.info(f"Processing IG post {post.id}: {post.post_type} for {post.account.name}")
        
        if post.account.token_status in ('expired', 'missing'):
            post.status = 'FAILED'
            post.error_message = 'Access token is expired or missing. Please refresh the token.'
            post.save(update_fields=['status', 'error_message'])
            continue

        media_url = post.media_url or ''
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
                result = instagram_api.publish_image(post.account, media_url, post.caption)
            elif post.post_type == 'REEL':
                post.status = 'PROCESSING'
                post.save(update_fields=['status'])
                cover_url = post.thumbnail_url or ''
                result = instagram_api.publish_reel(
                    post.account, media_url, post.caption,
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
                logger.info(f"Post {post.id} published! Media ID: {post.ig_media_id}")
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
            logger.exception(f"Unexpected error processing IG post {post.id}")

    # ── YouTube Posts ────────────────────────────────────────────
    yt_posts = ScheduledPost.objects.filter(
        platform='YOUTUBE',
        status='PENDING',
        scheduled_time__lte=now,
        youtube_account__isnull=False,
        youtube_account__is_active=True,
    ).select_related('youtube_account')

    for post in yt_posts:
        logger.info(f"Processing YouTube post {post.id} for {post.youtube_account.name}")

        if post.youtube_account.token_status in ('expired', 'missing'):
            post.status = 'FAILED'
            post.error_message = 'YouTube token is expired or missing. Please reconnect your channel.'
            post.save(update_fields=['status', 'error_message'])
            continue

        # YouTube uploads require a local file
        if not post.media_file:
            post.status = 'FAILED'
            post.error_message = 'No video file attached. YouTube uploads require a local file.'
            post.save(update_fields=['status', 'error_message'])
            continue

        video_file_path = post.media_file.path
        if not os.path.isfile(video_file_path):
            post.status = 'FAILED'
            post.error_message = f'Video file not found on disk: {video_file_path}'
            post.save(update_fields=['status', 'error_message'])
            continue

        try:
            from scheduler.services.youtube_api import upload_video_to_youtube

            post.status = 'PROCESSING'
            post.save(update_fields=['status'])

            result = upload_video_to_youtube(
                youtube_account=post.youtube_account,
                video_file_path=video_file_path,
                title=post.title or 'Untitled Video',
                description=post.caption or '',
                scheduled_time=post.scheduled_time,
                privacy_status=post.yt_privacy_status,
                tags=post.yt_tags,
                category_id=post.yt_category_id,
                made_for_kids=post.yt_made_for_kids,
            )

            if result['success']:
                post.status = 'PUBLISHED'
                post.yt_video_id = result.get('video_id', '')
                post.published_at = timezone.now()
                post.error_message = ''
                post.save(update_fields=['status', 'yt_video_id', 'published_at', 'error_message'])
                logger.info(f"YouTube post {post.id} uploaded! Video ID: {post.yt_video_id}")
            else:
                post.status = 'FAILED'
                post.error_message = result.get('error', 'Unknown YouTube upload error')
                post.save(update_fields=['status', 'error_message'])
                logger.error(f"YouTube post {post.id} failed: {post.error_message}")

        except Exception as e:
            post.status = 'FAILED'
            post.error_message = f'Unexpected error: {str(e)}'
            post.save(update_fields=['status', 'error_message'])
            logger.exception(f"Unexpected error processing YouTube post {post.id}")


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
