from django.contrib import admin
from .models import InstagramAccount, ScheduledPost, YouTubeAccount


@admin.register(InstagramAccount)
class InstagramAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'instagram_user_id', 'is_active', 'token_status', 'token_days_remaining', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'instagram_user_id']
    readonly_fields = ['token_expires_at', 'token_last_refreshed', 'created_at', 'updated_at']


@admin.register(YouTubeAccount)
class YouTubeAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel_id', 'is_active', 'token_status', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'channel_id']
    readonly_fields = ['token_expires_at', 'created_at', 'updated_at']


@admin.register(ScheduledPost)
class ScheduledPostAdmin(admin.ModelAdmin):
    list_display = ['platform', 'account', 'youtube_account', 'post_type', 'status', 'scheduled_time', 'published_at', 'created_at']
    list_filter = ['platform', 'status', 'post_type', 'account', 'youtube_account']
    search_fields = ['caption', 'title', 'account__name', 'youtube_account__name']
    readonly_fields = ['ig_container_id', 'ig_media_id', 'yt_video_id', 'published_at', 'created_at']
