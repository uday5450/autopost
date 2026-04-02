"""
Instagram API Service - Handles content publishing via the Instagram Graph API.

Publishing flow:
1. Create a media container (POST /{ig_user_id}/media)
2. For videos/reels: Wait for processing (poll status)
3. Publish the container (POST /{ig_user_id}/media_publish)
"""

import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

API_VERSION = 'v21.0'


def get_api_base(token):
    """
    Return the correct API base URL based on the token prefix.
    Tokens starting with 'IG' (Instagram Login) go to graph.instagram.com
    Tokens starting with 'EA' (Facebook Login) go to graph.facebook.com
    """
    if token and token.startswith('IG'):
        return f'https://graph.instagram.com/{API_VERSION}'
    return getattr(settings, 'INSTAGRAM_GRAPH_FB_API_BASE', f'https://graph.facebook.com/{API_VERSION}')


def _make_request(method, url, **kwargs):
    """Helper to make API requests with error handling."""
    kwargs.setdefault('timeout', 60)
    try:
        response = getattr(requests, method)(url, **kwargs)
        data = response.json()
        
        if 'error' in data:
            error = data['error']
            error_msg = error.get('message', 'Unknown Instagram API error')
            error_code = error.get('code', 'unknown')
            logger.error(f"Instagram API error [{error_code}]: {error_msg}")
            return {'success': False, 'error': error_msg, 'error_code': error_code}
        
        return {'success': True, 'data': data}
    except requests.exceptions.RequestException as e:
        logger.error(f"Instagram API request failed: {e}")
        return {'success': False, 'error': str(e)}


def create_image_container(account, image_url, caption=''):
    """
    Create a media container for an image post.
    
    POST /{ig_user_id}/media
        ?image_url={url}
        &caption={caption}
        &access_token={token}
    """
    url = f"{get_api_base(account.access_token)}/{account.instagram_user_id}/media"
    payload = {
        'image_url': image_url,
        'caption': caption,
        'access_token': account.access_token,
    }
    
    result = _make_request('post', url, data=payload)
    if result['success']:
        container_id = result['data'].get('id')
        logger.info(f"Image container created: {container_id}")
        return {'success': True, 'container_id': container_id}
    return result


def create_reel_container(account, video_url, caption='', cover_url=None):
    """
    Create a media container for a reel post.
    
    POST /{ig_user_id}/media
        ?media_type=REELS
        &video_url={url}
        &caption={caption}
        &cover_url={url}  (optional)
        &access_token={token}
    """
    url = f"{get_api_base(account.access_token)}/{account.instagram_user_id}/media"
    payload = {
        'media_type': 'REELS',
        'video_url': video_url,
        'caption': caption,
        'access_token': account.access_token,
    }
    
    if cover_url:
        payload['cover_url'] = cover_url
    
    result = _make_request('post', url, data=payload)
    if result['success']:
        container_id = result['data'].get('id')
        logger.info(f"Reel container created: {container_id}")
        return {'success': True, 'container_id': container_id}
    return result


def check_container_status(account, container_id):
    """
    Check the processing status of a media container.
    
    GET /{container_id}?fields=status_code&access_token={token}
    
    Possible status_code values:
    - EXPIRED: Not published within 24 hours
    - ERROR: Publishing failed
    - FINISHED: Ready to publish
    - IN_PROGRESS: Still processing
    - PUBLISHED: Already published
    """
    url = f"{get_api_base(account.access_token)}/{container_id}"
    params = {
        'fields': 'status_code',
        'access_token': account.access_token,
    }
    
    result = _make_request('get', url, params=params)
    if result['success']:
        status_code = result['data'].get('status_code', 'UNKNOWN')
        return {'success': True, 'status_code': status_code}
    return result


def publish_container(account, container_id):
    """
    Publish a media container.
    
    POST /{ig_user_id}/media_publish
        ?creation_id={container_id}
        &access_token={token}
    """
    url = f"{get_api_base(account.access_token)}/{account.instagram_user_id}/media_publish"
    payload = {
        'creation_id': container_id,
        'access_token': account.access_token,
    }
    
    result = _make_request('post', url, data=payload)
    if result['success']:
        media_id = result['data'].get('id')
        logger.info(f"Media published: {media_id}")
        return {'success': True, 'media_id': media_id}
    return result


def wait_for_container(account, container_id, max_attempts=30, interval=10):
    """
    Poll the container status until it's FINISHED or fails.
    
    Args:
        account: InstagramAccount instance
        container_id: The container ID to check
        max_attempts: Maximum number of polls (default 30 = 5 minutes)
        interval: Seconds between polls (default 10)
    
    Returns: dict with 'success', 'status_code'
    """
    for attempt in range(1, max_attempts + 1):
        result = check_container_status(account, container_id)
        
        if not result['success']:
            return result
        
        status = result['status_code']
        logger.info(
            f"Container {container_id} status: {status} (attempt {attempt}/{max_attempts})"
        )
        
        if status == 'FINISHED':
            return {'success': True, 'status_code': 'FINISHED'}
        elif status in ('ERROR', 'EXPIRED'):
            return {
                'success': False, 
                'error': f'Container status: {status}',
                'status_code': status
            }
        elif status == 'PUBLISHED':
            return {'success': True, 'status_code': 'PUBLISHED'}
        
        # Still IN_PROGRESS, wait and retry
        time.sleep(interval)
    
    return {
        'success': False, 
        'error': f'Container processing timed out after {max_attempts * interval}s',
        'status_code': 'TIMEOUT'
    }


def publish_image(account, image_url, caption=''):
    """
    Full flow to publish an image post.
    
    1. Create container
    2. Wait for processing (status = FINISHED)
    3. Publish container
    """
    # Step 1: Create container
    container_result = create_image_container(account, image_url, caption)
    if not container_result['success']:
        return container_result
    
    container_id = container_result['container_id']
    
    # Step 2: Wait for processing
    wait_result = wait_for_container(account, container_id)
    if not wait_result['success']:
        return {
            'success': False,
            'container_id': container_id,
            'error': wait_result.get('error', 'Processing failed'),
            'error_code': wait_result.get('status_code', 'UNKNOWN')
        }
    
    # Step 3: Publish
    publish_result = publish_container(account, container_id)
    if publish_result['success']:
        return {
            'success': True,
            'container_id': container_id,
            'media_id': publish_result['media_id'],
        }
    return publish_result


def publish_reel(account, video_url, caption='', cover_url=None):
    """
    Full flow to publish a reel.
    
    1. Create container with media_type=REELS
    2. Wait for video processing
    3. Publish container
    """
    # Step 1: Create container
    container_result = create_reel_container(account, video_url, caption, cover_url)
    if not container_result['success']:
        return container_result
    
    container_id = container_result['container_id']
    
    # Step 2: Wait for processing
    wait_result = wait_for_container(account, container_id)
    if not wait_result['success']:
        return {
            'success': False,
            'container_id': container_id,
            'error': wait_result.get('error', 'Processing failed'),
        }
    
    # Step 3: Publish
    publish_result = publish_container(account, container_id)
    if publish_result['success']:
        return {
            'success': True,
            'container_id': container_id,
            'media_id': publish_result['media_id'],
        }
    return {
        'success': False,
        'container_id': container_id,
        'error': publish_result.get('error', 'Publishing failed'),
    }
