from django.urls import path
from django.views.generic.base import RedirectView
from . import views

urlpatterns = [
    # Favicon & Web Manifest
    path('favicon.ico', RedirectView.as_view(url='/static/scheduler/images/favicon.ico', permanent=True)),
    path('site.webmanifest', RedirectView.as_view(url='/static/scheduler/site.webmanifest', permanent=True)),
    
    # Landing & Legal & SEO & Guides
    path('', views.landing_page, name='landing'),
    path('growth-guide/', views.growth_guide_view, name='growth_guide'),
    path('blog/', views.growth_guide_view, name='blog'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('sitemap.xml', views.sitemap_xml, name='sitemap_xml'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms/', views.terms_of_service, name='terms_of_service'),
    
    # Dashboard & Post Creation
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.new_post_select, name='new_post_select'),
    path('studio/', views.create_post, name='studio'),
    path('bulk-tools/', views.bulk_tools, name='bulk_tools'),
    path('settings/', views.settings_view, name='settings'),
    path('api-keys/', views.api_keys_view, name='api_keys'),
    
    # Posts
    path('posts/', views.post_list, name='post_list'),
    path('posts/create/', views.create_post, name='create_post'),
    path('posts/<int:pk>/cancel/', views.post_cancel, name='post_cancel'),
    path('posts/<int:pk>/retry/', views.post_retry, name='post_retry'),
    path('posts/<int:pk>/delete/', views.post_delete, name='post_delete'),
    
    # Instagram Accounts
    path('accounts/', views.account_list, name='account_list'),
    path('accounts/add/', views.account_add, name='account_add'),
    path('accounts/<int:pk>/edit/', views.account_edit, name='account_edit'),
    path('accounts/<int:pk>/delete/', views.account_delete, name='account_delete'),
    path('accounts/<int:pk>/exchange-token/', views.account_exchange_token, name='account_exchange_token'),
    path('accounts/<int:pk>/refresh-token/', views.account_refresh_token, name='account_refresh_token'),
    
    # YouTube OAuth
    path('accounts/youtube/login/', views.youtube_login, name='youtube_login'),
    path('accounts/youtube/callback/', views.youtube_callback, name='youtube_callback'),
    path('accounts/youtube/<int:pk>/disconnect/', views.youtube_disconnect, name='youtube_disconnect'),
    
    # Facebook Simulated Connect
    path('accounts/facebook/connect/', views.connect_facebook, name='connect_facebook'),
    path('accounts/facebook/<int:pk>/disconnect/', views.disconnect_facebook, name='disconnect_facebook'),

    # X Simulated Connect
    path('accounts/x/connect/', views.connect_x, name='connect_x'),
    path('accounts/x/<int:pk>/disconnect/', views.disconnect_x, name='disconnect_x'),

    # Pinterest Simulated Connect
    path('accounts/pinterest/connect/', views.connect_pinterest, name='connect_pinterest'),
    path('accounts/pinterest/<int:pk>/disconnect/', views.disconnect_pinterest, name='disconnect_pinterest'),

    # TikTok Simulated Connect
    path('accounts/tiktok/connect/', views.connect_tiktok, name='connect_tiktok'),
    path('accounts/tiktok/<int:pk>/disconnect/', views.disconnect_tiktok, name='disconnect_tiktok'),

    # LinkedIn Connect
    path('accounts/linkedin/connect/', views.connect_linkedin, name='connect_linkedin'),
    path('accounts/linkedin/<int:pk>/disconnect/', views.disconnect_linkedin, name='disconnect_linkedin'),

    # Reddit Connect
    path('accounts/reddit/connect/', views.connect_reddit, name='connect_reddit'),
    path('accounts/reddit/<int:pk>/disconnect/', views.disconnect_reddit, name='disconnect_reddit'),

    # Snapchat Connect
    path('accounts/snapchat/connect/', views.connect_snapchat, name='connect_snapchat'),
    path('accounts/snapchat/<int:pk>/disconnect/', views.disconnect_snapchat, name='disconnect_snapchat'),

    # Visual Content Calendar
    path('calendar/', views.calendar_view, name='calendar'),
    path('api/calendar/events/', views.calendar_events_api, name='calendar_events_api'),

    # AI Caption Generator
    path('api/ai/generate-caption/', views.api_generate_caption, name='api_generate_caption'),

    # Pricing & Razorpay Billing
    path('pricing/', views.pricing_view, name='pricing'),
    path('pricing/create-order/', views.create_razorpay_order, name='create_razorpay_order'),
    path('pricing/verify/', views.verify_razorpay_payment, name='verify_razorpay_payment'),
    path('pricing/validate-coupon/', views.api_validate_coupon, name='api_validate_coupon'),

    # Developer & AI Agent REST API & MCP
    path('api/v1/posts/', views.api_list_posts, name='api_list_posts'),
    path('api/v1/posts/create/', views.api_create_post, name='api_create_post'),
    path('api/mcp/', views.api_mcp_endpoint, name='api_mcp'),

    # Auth & Onboarding
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/signup/', views.signup_view, name='signup'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('onboarding/connect/', views.onboarding_connect, name='onboarding_connect'),
]
