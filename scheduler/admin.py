from django.contrib import admin
from .models import InstagramAccount, ScheduledPost


@admin.register(InstagramAccount)
class InstagramAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'instagram_user_id', 'is_active', 'token_status', 'token_days_remaining', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'instagram_user_id']
    readonly_fields = ['token_expires_at', 'token_last_refreshed', 'created_at', 'updated_at']


@admin.register(ScheduledPost)
class ScheduledPostAdmin(admin.ModelAdmin):
    list_display = ['account', 'post_type', 'status', 'scheduled_time', 'published_at', 'created_at']
    list_filter = ['status', 'post_type', 'account']
    search_fields = ['caption', 'account__name']
    readonly_fields = ['ig_container_id', 'ig_media_id', 'published_at', 'created_at']
