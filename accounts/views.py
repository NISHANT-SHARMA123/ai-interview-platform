import json
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods
from accounts.forms import CandidateSignupForm, CandidateLoginForm
from accounts.models import UserProfile
from accounts.oauth import (
    is_google_oauth_configured,
    build_google_auth_uri,
    exchange_code_for_user_info,
    verify_google_credential_jwt,
    get_or_create_candidate_from_google
)

logger = logging.getLogger(__name__)


def landing_view(request):
    """Renders the Glassmorphism marketing and product landing page."""
    return render(request, 'landing.html')


@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    Candidate login endpoint.
    Supports username and email authentication, Google OAuth 1-click trigger,
    remember-me duration, and automatic lockout tracking via django-axes.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = CandidateLoginForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            raw_identifier = form.cleaned_data['username'].strip()
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)

            # Dual lookup: check if input is email or username
            lookup_username = raw_identifier
            if '@' in raw_identifier:
                user_match = User.objects.filter(email__iexact=raw_identifier).first()
                if user_match:
                    lookup_username = user_match.username

            user = authenticate(request, username=lookup_username, password=password)

            if user is not None and user.is_active:
                login(request, user)

                # Session persistence
                if remember_me:
                    request.session.set_expiry(1209600)  # 2 weeks
                else:
                    request.session.set_expiry(0)  # Browser close

                messages.success(request, f"Welcome back, {user.username}!")

                next_url = request.GET.get('next')
                if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                    return redirect(next_url)
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid username/email or password. Please try again.")

    context = {
        'form': form,
        'google_oauth_configured': is_google_oauth_configured(),
        'google_client_id': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
    }
    return render(request, 'accounts/login.html', context)


@require_http_methods(["GET", "POST"])
def signup_view(request):
    """
    Candidate registration view.
    Validates email format, enforces Django password validators,
    and initializes candidate UserProfile.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = CandidateSignupForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            target_role = form.cleaned_data.get('target_role', 'Software Engineer')
            preferred_domain = form.cleaned_data.get('preferred_domain', 'fullstack')
            anxiety_mode_default = form.cleaned_data.get('anxiety_mode_default', False)

            # Create User
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            # Update UserProfile preferences (UserProfile auto-created via post_save signal)
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.target_role = target_role
            profile.preferred_domain = preferred_domain
            profile.anxiety_mode_default = anxiety_mode_default
            profile.save()

            # Auto-login newly registered candidate
            authenticated_user = authenticate(request, username=username, password=password)
            if authenticated_user:
                login(request, authenticated_user)

            messages.success(request, f"Welcome to InterViewStudio, {username}! Your preparation studio is ready.")
            return redirect('dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")

    context = {
        'form': form,
        'google_oauth_configured': is_google_oauth_configured(),
        'google_client_id': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
    }
    return render(request, 'accounts/signup.html', context)


def logout_view(request):
    """Flushes session and signs candidate out."""
    logout(request)
    messages.success(request, "You have been safely signed out.")
    return redirect('landing')


# -----------------------------------------------------------------------------
# Google OAuth 2.0 & Direct Email Authentication
# -----------------------------------------------------------------------------
def google_login_view(request):
    """
    Initiates Google OAuth flow or instant 1-click Google sign-in.
    - If GOOGLE_CLIENT_ID is configured, redirects to Google's real OAuth2 authorization screen.
    - In local dev mode without Google credentials, instantly logs in as a Google Candidate,
      eliminating friction and intermediate setup hurdles.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if is_google_oauth_configured():
        auth_uri = build_google_auth_uri(request)
        return redirect(auth_uri)
    
    # In local development without Google credentials, provide seamless 1-click login:
    if settings.DEBUG:
        if request.GET.get('customize') == 'true':
            return redirect('google_dev_login')

        dev_email = request.GET.get('email', 'sarah.developer@gmail.com').strip().lower()
        dev_name = request.GET.get('name', 'Sarah Chen')
        user, created = get_or_create_candidate_from_google(dev_email, dev_name)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        if created:
            messages.success(request, f"Welcome to InterViewStudio! Account created with Google ({dev_email}).")
        else:
            messages.success(request, f"Welcome back, {user.first_name or user.username}! Signed in with Google.")
        return redirect('dashboard')

    messages.error(request, "Google OAuth is not configured on this server. Please sign in with email or credentials.")
    return redirect('login')


@require_http_methods(["POST"])
def direct_email_auth_view(request):
    if not settings.DEBUG:
        messages.error(request, "Passwordless email sign-in is disabled in production. Please use Google OAuth or your password.")
        return redirect('login')
    """
    Direct Email Sign-In / Account Creation without requiring a password.
    Directly addresses: 'create an account via email directly it helps users for easy login'.
    Finds existing candidate by email or instantly provisions a new candidate User & Profile.
    """
    email = request.POST.get('email', '').strip().lower()
    if not email or '@' not in email or '.' not in email.split('@')[-1]:
        messages.error(request, "Please provide a valid email address.")
        next_url = request.POST.get('next') or 'login'
        return redirect(next_url)

    name = request.POST.get('name', '')
    user, created = get_or_create_candidate_from_google(email, name=name)
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    if created:
        messages.success(request, f"Welcome to InterViewStudio! Account created directly for {email}.")
    else:
        messages.success(request, f"Welcome back, {user.first_name or user.username}! Signed in via email.")

    next_url = request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('dashboard')


def google_callback_view(request):
    """
    Handles Google's OAuth2 authorization code callback.
    Exchanges code for user info, provisions or logs in candidate.
    """
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')

    if error:
        messages.error(request, f"Google authentication was cancelled: {error}")
        return redirect('login')

    if not code or not state:
        messages.error(request, "Invalid authentication response from Google.")
        return redirect('login')

    try:
        user_info = exchange_code_for_user_info(request, code, state)
        email = user_info.get('email')
        name = user_info.get('name', '')

        if not email:
            messages.error(request, "Google did not provide an email address for your account.")
            return redirect('login')

        user, created = get_or_create_candidate_from_google(email, name)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        if created:
            messages.success(request, f"Welcome! Account created successfully via Google ({email}).")
        else:
            messages.success(request, f"Welcome back, {user.username}! Signed in via Google.")

        return redirect('dashboard')
    except Exception as e:
        logger.error("Google OAuth callback error: %s", str(e), exc_info=True)
        messages.error(request, f"Google sign-in error: {str(e)}")
        return redirect('login')


@require_http_methods(["POST"])
def google_one_tap_callback_view(request):
    """
    Receives Google Identity Services (GIS) One-Tap / Button credential token.
    Verifies JWT token and logs candidate in seamlessly via AJAX.
    """
    try:
        data = json.loads(request.body)
        credential = data.get('credential')
        if not credential:
            return JsonResponse({'status': 'error', 'message': 'Missing credential'}, status=400)

        token_data = verify_google_credential_jwt(credential)
        email = token_data.get('email')
        name = token_data.get('name', '')

        if not email:
            return JsonResponse({'status': 'error', 'message': 'Email not provided by Google'}, status=400)

        user, created = get_or_create_candidate_from_google(email, name)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        return JsonResponse({'status': 'ok', 'redirect': '/dashboard/'})
    except Exception as e:
        logger.error("Google One-Tap error: %s", str(e))
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


def google_dev_login_view(request):
    """
    Development/Testing helper: allows 1-click Google sign-in simulation
    when developers test locally before provisioning a Google Cloud Console client ID.
    Only accessible when DEBUG=True.
    """
    if not settings.DEBUG:
        return redirect('login')

    if request.method == 'POST':
        dev_email = request.POST.get('email', 'google_candidate@example.com').strip().lower()
        dev_name = request.POST.get('name', 'Google Candidate')
        user, created = get_or_create_candidate_from_google(dev_email, dev_name)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        if created:
            messages.success(request, f"[Dev OAuth] Account created for {dev_email}!")
        else:
            messages.success(request, f"[Dev OAuth] Signed in as {dev_email}!")
        return redirect('dashboard')

    return render(request, 'accounts/google_dev_login.html')


@login_required
@require_http_methods(["POST"])
def update_profile_view(request):
    """Updates candidate target role, preferred domain, and anxiety mode preference."""
    target_role = request.POST.get('target_role', '').strip()
    preferred_domain = request.POST.get('preferred_domain', '').strip()
    anxiety_mode_default = request.POST.get('anxiety_mode_default') == 'on'

    profile = request.user.profile
    if target_role:
        profile.target_role = target_role[:120]
    if preferred_domain:
        profile.preferred_domain = preferred_domain[:60]
    profile.anxiety_mode_default = anxiety_mode_default
    profile.save()

    messages.success(request, "Your profile preferences have been updated.")
    return redirect('dashboard')


@login_required
@require_http_methods(["POST"])
def delete_account_view(request):
    """
    Zero-Data Privacy Guarantee: Completely purges candidate user account,
    profile, interviews, and all associated metric telemetry from the platform.
    """
    user = request.user
    logout(request)
    user.delete()
    messages.success(request, "Your account and all associated interview telemetry have been permanently deleted.")
    return redirect('landing')
