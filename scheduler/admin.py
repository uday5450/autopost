from django.contrib import admin
from .models import (
    InstagramAccount, ScheduledPost, YouTubeAccount,
    FacebookAccount, XAccount, PinterestAccount, TikTokAccount
)


@admin.register(InstagramAccount)
class InstagramAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'instagram_user_id', 'user', 'is_active', 'token_status', 'token_days_remaining', 'created_at']
    list_filter = ['user', 'is_active']
    search_fields = ['name', 'instagram_user_id', 'user__email']
    readonly_fields = ['token_expires_at', 'token_last_refreshed', 'created_at', 'updated_at']


@admin.register(YouTubeAccount)
class YouTubeAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel_id', 'user', 'is_active', 'token_status', 'created_at']
    list_filter = ['user', 'is_active']
    search_fields = ['name', 'channel_id', 'user__email']
    readonly_fields = ['token_expires_at', 'created_at', 'updated_at']


@admin.register(FacebookAccount)
class FacebookAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'page_id', 'user', 'is_active', 'token_status', 'created_at']
    list_filter = ['user', 'is_active']
    search_fields = ['name', 'page_id', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(XAccount)
class XAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'screen_name', 'user', 'is_active', 'token_status', 'created_at']
    list_filter = ['user', 'is_active']
    search_fields = ['name', 'screen_name', 'user__email']
    readonly_fields = ['token_expires_at', 'created_at', 'updated_at']


@admin.register(PinterestAccount)
class PinterestAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'board_name', 'user', 'is_active', 'token_status', 'created_at']
    list_filter = ['user', 'is_active']
    search_fields = ['name', 'board_name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TikTokAccount)
class TikTokAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'username', 'user', 'is_active', 'token_status', 'created_at']
    list_filter = ['user', 'is_active']
    search_fields = ['name', 'username', 'user__email']
    readonly_fields = ['token_expires_at', 'created_at', 'updated_at']


@admin.register(ScheduledPost)
class ScheduledPostAdmin(admin.ModelAdmin):
    list_display = ['platform', 'user', 'account', 'youtube_account', 'facebook_account', 'x_account', 'pinterest_account', 'tiktok_account', 'post_type', 'status', 'scheduled_time', 'published_at', 'created_at']
    list_filter = ['user', 'platform', 'status', 'post_type']
    search_fields = ['caption', 'title', 'account__name', 'youtube_account__name', 'facebook_account__name', 'x_account__name', 'user__email']
    readonly_fields = ['ig_container_id', 'ig_media_id', 'yt_video_id', 'published_at', 'created_at']
