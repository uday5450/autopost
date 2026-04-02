"""
YouTube API Service — handles video uploads using the YouTube Data API v3.

Uses Resumable Media Upload to push a local video file to a connected
YouTube channel and optionally schedule it for future publication via
YouTube's native scheduler (privacyStatus=private + publishAt).
"""

import logging
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


def _get_youtube_service(youtube_account):
    """Build an authorized YouTube API client from a YouTubeAccount instance.
    
    Automatically refreshes the access_token if it has expired
    and persists the new token back to the database.
    """
    from django.conf import settings
    from django.utils import timezone
    from datetime import timedelta
    import google.auth.transport.requests

    credentials = Credentials(
        token=youtube_account.access_token,
        refresh_token=youtube_account.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_OAUTH2_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH2_CLIENT_SECRET,
    )

    # Auto-refresh if the token is expired or about to expire
    if not credentials.valid:
        try:
            credentials.refresh(google.auth.transport.requests.Request())
            # Save the refreshed token back to the database
            youtube_account.access_token = credentials.token
            youtube_account.token_expires_at = credentials.expiry or (timezone.now() + timedelta(hours=1))
            youtube_account.save(update_fields=["access_token", "token_expires_at"])
            logger.info(f"Auto-refreshed YouTube token for {youtube_account.name}")
        except Exception as e:
            logger.error(f"Failed to refresh YouTube token for {youtube_account.name}: {e}")

    service = build("youtube", "v3", credentials=credentials)
    return service, credentials


def refresh_youtube_token(youtube_account):
    """Explicitly refresh the access token for a YouTubeAccount.
    
    Returns dict with 'success' and 'error' keys.
    """
    from django.conf import settings
    from django.utils import timezone
    from datetime import timedelta
    import google.auth.transport.requests

    if not youtube_account.refresh_token:
        return {"success": False, "error": "No refresh token available. Please reconnect."}

    try:
        credentials = Credentials(
            token=youtube_account.access_token,
            refresh_token=youtube_account.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_OAUTH2_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH2_CLIENT_SECRET,
        )
        credentials.refresh(google.auth.transport.requests.Request())

        youtube_account.access_token = credentials.token
        youtube_account.token_expires_at = credentials.expiry or (timezone.now() + timedelta(hours=1))
        youtube_account.save(update_fields=["access_token", "token_expires_at"])
        logger.info(f"Refreshed YouTube token for {youtube_account.name}")
        return {"success": True, "error": ""}
    except Exception as e:
        logger.exception(f"Failed to refresh YouTube token: {e}")
        return {"success": False, "error": str(e)}


def get_channel_info(youtube_account):
    """
    Retrieve the authenticated user's YouTube channel details.
    Returns dict with 'id', 'title', 'thumbnail' or None on failure.
    """
    try:
        service, credentials = _get_youtube_service(youtube_account)
        response = service.channels().list(part="snippet", mine=True).execute()

        if response.get("items"):
            channel = response["items"][0]
            return {
                "id": channel["id"],
                "title": channel["snippet"]["title"],
                "thumbnail": channel["snippet"]["thumbnails"].get("default", {}).get("url", ""),
            }
        return None
    except HttpError as e:
        logger.exception(f"YouTube API error fetching channel info: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error fetching channel info: {e}")
        return None


def upload_video_to_youtube(
    youtube_account, 
    video_file_path, 
    title, 
    description="", 
    scheduled_time=None,
    privacy_status="public",
    tags="",
    category_id="22",
    made_for_kids=False
):
    """
    Upload a video to YouTube via Resumable Media Upload.
    Includes advanced metadata like tags, category, and kids compliance.
    """
    try:
        service, credentials = _get_youtube_service(youtube_account)

        # ---- Build request body ------------------------------------------------
        tags_list = [tag.strip() for tag in tags.split(",")] if tags else []
        
        body = {
            "snippet": {
                "title": title,
                "description": description or "",
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": made_for_kids,
            },
        }
        
        if tags_list:
            body["snippet"]["tags"] = tags_list

        # If a scheduled_time is supplied use YouTube's native scheduler
        if scheduled_time:
            # YouTube requires ISO 8601 in UTC
            publish_at_iso = scheduled_time.strftime("%Y-%m-%dT%H:%M:%S.0Z")
            body["status"]["publishAt"] = publish_at_iso
            body["status"]["privacyStatus"] = "private"  # Must be private when using publishAt
            logger.info(f"Scheduling YouTube publish at: {publish_at_iso}")

        # ---- Upload ------------------------------------------------------------
        if not os.path.isfile(video_file_path):
            return {"success": False, "video_id": "", "error": f"File not found: {video_file_path}"}

        media = MediaFileUpload(
            video_file_path,
            mimetype="video/*",
            resumable=True,
            chunksize=10 * 1024 * 1024,  # 10 MB chunks
        )

        request = service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(f"Upload progress: {int(status.progress() * 100)}%")

        video_id = response.get("id", "")
        logger.info(f"YouTube upload complete — video ID: {video_id}")

        # Persist any refreshed token back to the account
        if credentials.token != youtube_account.access_token:
            youtube_account.access_token = credentials.token
            youtube_account.save(update_fields=["access_token"])

        return {"success": True, "video_id": video_id, "error": ""}

    except HttpError as e:
        error_msg = str(e)
        logger.exception(f"YouTube API HttpError during upload: {error_msg}")
        return {"success": False, "video_id": "", "error": error_msg}
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Unexpected error during YouTube upload: {error_msg}")
        return {"success": False, "video_id": "", "error": error_msg}
