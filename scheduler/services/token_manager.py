"""
Token Manager - Handles Instagram access token exchange and refresh.

Token Flow:
1. User provides a short-lived token (1 hour validity)
2. Exchange it for a long-lived token (60 days validity)
3. Auto-refresh long-lived tokens before they expire

Also handles:
- Auto-detecting Instagram User ID from access token
- Fallback to direct token use if exchange fails (token may already be long-lived)
"""

import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

GRAPH_API_BASE = 'https://graph.instagram.com'
GRAPH_FB_API_BASE = getattr(settings, 'INSTAGRAM_GRAPH_FB_API_BASE', 'https://graph.facebook.com/v21.0')


def get_user_info(access_token):
    """
    Auto-detect the Instagram User ID and username from an access token.
    
    Tries multiple endpoints:
    1. Instagram Graph API /me (for Instagram Login tokens)
    2. Facebook Graph API /me/accounts → instagram_business_account (for FB Login tokens)
    
    Returns: dict with 'success', 'user_id', 'username', 'name'
    """
    # Try 1: Instagram Graph API /me
    try:
        url = f"{GRAPH_API_BASE}/me"
        params = {
            'fields': 'user_id,username,name,account_type,profile_picture_url',
            'access_token': access_token,
        }
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        if response.status_code == 200 and 'user_id' in data:
            return {
                'success': True,
                'user_id': str(data['user_id']),
                'username': data.get('username', ''),
                'name': data.get('name', ''),
                'account_type': data.get('account_type', ''),
                'profile_picture_url': data.get('profile_picture_url', ''),
            }
        
        # Some tokens return 'id' instead of 'user_id'
        if response.status_code == 200 and 'id' in data:
            return {
                'success': True,
                'user_id': str(data['id']),
                'username': data.get('username', ''),
                'name': data.get('name', ''),
                'account_type': data.get('account_type', ''),
                'profile_picture_url': data.get('profile_picture_url', ''),
            }
    except Exception as e:
        logger.debug(f"Instagram /me endpoint failed: {e}")
    
    # Try 2: Facebook Graph API - get pages then instagram business account
    try:
        # Get pages the user manages
        url = f"{GRAPH_FB_API_BASE}/me/accounts"
        params = {'access_token': access_token}
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        if response.status_code == 200 and 'data' in data and len(data['data']) > 0:
            for page in data['data']:
                page_id = page.get('id')
                page_token = page.get('access_token', access_token)
                
                # Get Instagram business account linked to this page
                ig_url = f"{GRAPH_FB_API_BASE}/{page_id}"
                ig_params = {
                    'fields': 'instagram_business_account',
                    'access_token': page_token,
                }
                ig_response = requests.get(ig_url, params=ig_params, timeout=15)
                ig_data = ig_response.json()
                
                if 'instagram_business_account' in ig_data:
                    ig_account_id = ig_data['instagram_business_account']['id']
                    
                    # Get username and profile picture
                    username_url = f"{GRAPH_FB_API_BASE}/{ig_account_id}"
                    username_params = {
                        'fields': 'username,name,profile_picture_url',
                        'access_token': access_token,
                    }
                    username_response = requests.get(username_url, params=username_params, timeout=15)
                    username_data = username_response.json()
                    
                    return {
                        'success': True,
                        'user_id': str(ig_account_id),
                        'username': username_data.get('username', ''),
                        'name': username_data.get('name', ''),
                        'account_type': 'BUSINESS',
                        'profile_picture_url': username_data.get('profile_picture_url', ''),
                    }
    except Exception as e:
        logger.debug(f"Facebook Graph API failed: {e}")
    
    return {'success': False, 'error': 'Could not detect Instagram User ID from this token.'}


def exchange_token(short_lived_token, client_secret):
    """
    Exchange a short-lived token for a long-lived token.
    
    GET https://graph.instagram.com/access_token
        ?grant_type=ig_exchange_token
        &client_secret={client_secret}
        &access_token={short_lived_token}
    
    Returns: dict with 'access_token', 'token_type', 'expires_in' (seconds)
    """
    url = f"{GRAPH_API_BASE}/access_token"
    params = {
        'grant_type': 'ig_exchange_token',
        'client_secret': client_secret,
        'access_token': short_lived_token,
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if response.status_code == 200 and 'access_token' in data:
            expires_in = data.get('expires_in', 5184000)  # Default 60 days
            expires_at = timezone.now() + timedelta(seconds=expires_in)
            
            return {
                'success': True,
                'access_token': data['access_token'],
                'token_type': data.get('token_type', 'bearer'),
                'expires_in': expires_in,
                'expires_at': expires_at,
            }
        
        error_msg = data.get('error', {}).get('message', 'Unknown error')
        logger.warning(f"Token exchange failed: {error_msg}")
        return {'success': False, 'error': error_msg}
    except requests.exceptions.RequestException as e:
        logger.error(f"Token exchange request failed: {e}")
        return {'success': False, 'error': str(e)}


def try_token_directly(access_token):
    """
    Try to use the token directly (it may already be long-lived).
    Validates by calling /me and checks if it works.
    
    Returns: dict with 'success', 'expires_at' (estimated)
    """
    user_info = get_user_info(access_token)
    if user_info['success']:
        # Token works - assume it's long-lived (60 days from now)
        expires_at = timezone.now() + timedelta(days=60)
        return {
            'success': True,
            'access_token': access_token,
            'expires_at': expires_at,
            'user_info': user_info,
        }
    return {'success': False, 'error': 'Token is not valid or has expired.'}


def exchange_and_store(account, short_lived_token):
    """
    Smart token handling:
    1. Try to exchange the token for a long-lived one
    2. If exchange fails, try to use the token directly (it may already be long-lived)
    3. Auto-detect Instagram User ID if not already set
    
    Args:
        account: InstagramAccount model instance
        short_lived_token: The access token to store
    
    Returns: dict with 'success', 'user_info', and optionally 'error'
    """
    token_to_store = None
    expires_at = None
    exchange_error = None
    
    # Step 1: Try token exchange
    result = exchange_token(short_lived_token, account.client_secret)
    
    if result['success']:
        token_to_store = result['access_token']
        expires_at = result['expires_at']
        logger.info(f"Token exchanged successfully for account: {account.name}")
    else:
        exchange_error = result.get('error', '')
        logger.warning(f"Token exchange failed: {exchange_error}. Trying direct use...")
        
        # Step 2: Try using token directly (it may already be long-lived)
        direct_result = try_token_directly(short_lived_token)
        if direct_result['success']:
            token_to_store = short_lived_token
            expires_at = direct_result['expires_at']
            logger.info(f"Token used directly (already valid) for account: {account.name}")
        else:
            return {
                'success': False, 
                'error': f"Token exchange failed: {exchange_error}. "
                         f"Direct use also failed. Please provide a valid token."
            }
    
    # Step 3: Store the token
    account.access_token = token_to_store
    account.token_expires_at = expires_at
    account.token_last_refreshed = timezone.now()
    
    # Step 4: Auto-detect Instagram User ID if not set
    user_info = get_user_info(token_to_store)
    if user_info['success']:
        if not account.instagram_user_id:
            account.instagram_user_id = user_info['user_id']
        # Auto-fill name if empty
        if not account.name and user_info.get('username'):
            account.name = user_info['username']
        # Extract profile picture URL
        if user_info.get('profile_picture_url'):
            account.profile_picture_url = user_info['profile_picture_url']
    
    account.save()
    
    return {
        'success': True, 
        'expires_at': expires_at,
        'user_info': user_info if user_info['success'] else None,
    }


def refresh_token(long_lived_token):
    """
    Refresh a long-lived token to extend it for another 60 days.
    Token must be at least 24 hours old and not yet expired.
    
    GET https://graph.instagram.com/refresh_access_token
        ?grant_type=ig_refresh_token
        &access_token={long_lived_token}
    """
    url = f"{GRAPH_API_BASE}/refresh_access_token"
    params = {
        'grant_type': 'ig_refresh_token',
        'access_token': long_lived_token,
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if response.status_code == 200 and 'access_token' in data:
            expires_in = data.get('expires_in', 5184000)
            expires_at = timezone.now() + timedelta(seconds=expires_in)
            
            return {
                'success': True,
                'access_token': data['access_token'],
                'token_type': data.get('token_type', 'bearer'),
                'expires_in': expires_in,
                'expires_at': expires_at,
            }
        
        error_msg = data.get('error', {}).get('message', 'Unknown error')
        logger.error(f"Token refresh failed: {error_msg}")
        return {'success': False, 'error': error_msg}
    except requests.exceptions.RequestException as e:
        logger.error(f"Token refresh request failed: {e}")
        return {'success': False, 'error': str(e)}


def refresh_and_store(account):
    """
    Refresh the long-lived token for an account and store it.
    """
    if not account.access_token:
        return {'success': False, 'error': 'No access token to refresh'}
    
    result = refresh_token(account.access_token)
    
    if result['success']:
        account.access_token = result['access_token']
        account.token_expires_at = result['expires_at']
        account.token_last_refreshed = timezone.now()
        account.save(update_fields=[
            'access_token', 'token_expires_at', 'token_last_refreshed', 'updated_at'
        ])
        logger.info(f"Token refreshed successfully for account: {account.name}")
        return {'success': True, 'expires_at': result['expires_at']}
    
    return result


def auto_refresh_all_tokens():
    """
    Check all active accounts and refresh tokens that are approaching expiry.
    Refreshes tokens that have less than 10 days remaining.
    """
    from scheduler.models import InstagramAccount
    
    accounts = InstagramAccount.objects.filter(is_active=True)
    results = []
    
    for account in accounts:
        if not account.access_token or not account.token_expires_at:
            continue
        
        days_remaining = account.token_days_remaining
        if days_remaining is not None and days_remaining <= 10:
            logger.info(
                f"Token for {account.name} expires in {days_remaining} days. Refreshing..."
            )
            result = refresh_and_store(account)
            results.append({
                'account': account.name,
                'result': result,
            })
    
    return results
