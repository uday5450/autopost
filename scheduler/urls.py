from django.urls import path
from . import views

urlpatterns = [
    # Landing & Legal
    path('', views.landing_page, name='landing'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms/', views.terms_of_service, name='terms_of_service'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
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

    # Auth
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/signup/', views.signup_view, name='signup'),
    path('accounts/logout/', views.logout_view, name='logout'),
]
