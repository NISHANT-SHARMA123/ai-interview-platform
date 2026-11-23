from django.urls import path
from accounts import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/update/', views.update_profile_view, name='update_profile'),
    path('profile/delete/', views.delete_account_view, name='delete_account'),
    
    # Direct Instant Email Sign-In / Account Creation
    path('email-login/', views.direct_email_auth_view, name='direct_email_login'),
    
    # Google OAuth 2.0 & One-Tap Endpoints
    path('google/login/', views.google_login_view, name='google_oauth_login'),
    path('google/callback/', views.google_callback_view, name='google_oauth_callback'),
    path('google/one-tap/', views.google_one_tap_callback_view, name='google_one_tap_callback'),
    path('google/dev-login/', views.google_dev_login_view, name='google_dev_login'),
]
