from django.contrib import admin
from .models import (
    InstagramAccount, ScheduledPost, YouTubeAccount,
    FacebookAccount, XAccount, PinterestAccount, TikTokAccount,
    PricingPlan, DiscountCoupon, UserSubscription, UserProfile,
    Workspace, WorkspaceMember
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


@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):
    list_display = [
        'order', 'name', 'plan_code', 'price_inr', 'original_price_inr',
        'discount_badge', 'max_connected_accounts', 'price_per_additional_account',
        'is_featured', 'is_custom_calculator', 'is_active'
    ]
    list_display_links = ['name', 'plan_code']
    list_editable = [
        'order', 'price_inr', 'original_price_inr', 'is_featured',
        'max_connected_accounts', 'price_per_additional_account', 'is_active'
    ]
    list_filter = ['is_active', 'is_featured', 'is_custom_calculator']
    search_fields = ['name', 'plan_code', 'description']
    
    fieldsets = (
        ('Plan Identification', {
            'fields': ('name', 'plan_code', 'description', 'order', 'is_active')
        }),
        ('Pricing & Discounts (₹ / $)', {
            'fields': (
                'price_inr', 'original_price_inr', 'yearly_price_inr',
                'yearly_discount_percent', 'price_usd', 'billing_period'
            ),
            'description': 'Set original_price_inr for strike-through discount. yearly_price_inr: set 0 to auto-calculate annual total with yearly_discount_percent (e.g. 20% off).'
        }),
        ('Account, Post & Workspace Limits', {
            'fields': (
                'max_connected_accounts', 'price_per_additional_account',
                'max_posts_per_month', 'max_workspaces', 'max_members_per_workspace',
                'is_custom_calculator'
            ),
            'description': 'max_connected_accounts: 0 for unlimited. max_workspaces: 0 for unlimited workspaces. max_members_per_workspace: 0 for unlimited members.'
        }),
        ('Visual Highlights & CTA', {
            'fields': ('is_featured', 'badge_text', 'cta_text', 'features_list'),
            'description': 'Features list: one per line. Prefix with ! for bold, or - for strikethrough/disabled.'
        }),
    )

    def discount_badge(self, obj):
        pct = obj.discount_percent
        if pct > 0:
            return f"{pct}% OFF"
        return "Regular"
    discount_badge.short_description = "Discount"


@admin.register(DiscountCoupon)
class DiscountCouponAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'discount_percent', 'discount_amount_inr',
        'used_count', 'max_uses', 'is_active', 'valid_until', 'created_at'
    ]
    list_editable = ['is_active']
    search_fields = ['code']
    list_filter = ['is_active']


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'plan', 'pricing_plan', 'connected_accounts_limit',
        'posts_limit_per_month', 'workspaces_limit', 'members_per_workspace_limit',
        'discount_applied_inr', 'is_active', 'updated_at'
    ]
    search_fields = ['user__username', 'user__email', 'plan', 'razorpay_order_id', 'razorpay_payment_id']
    list_filter = ['plan', 'is_active']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'phone_number', 'country_code', 'country_name', 'onboarding_completed', 'created_at']
    search_fields = ['user__username', 'user__email', 'full_name', 'phone_number', 'country_name']
    list_filter = ['country_name', 'onboarding_completed']


class WorkspaceMemberInline(admin.TabularInline):
    model = WorkspaceMember
    extra = 1
    fields = ['user', 'role', 'invited_by', 'joined_at']
    readonly_fields = ['joined_at']


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'owner', 'timezone', 'created_at']
    search_fields = ['name', 'slug', 'owner__username', 'owner__email']
    list_filter = ['timezone', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [WorkspaceMemberInline]


@admin.register(WorkspaceMember)
class WorkspaceMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'workspace', 'role', 'invited_by', 'joined_at']
    search_fields = ['user__username', 'user__email', 'workspace__name']
    list_filter = ['role', 'joined_at']



