import secrets
import logging
import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import UserProfile

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


def is_google_oauth_configured() -> bool:
    """Returns True if Google Client ID and Secret are configured."""
    return bool(getattr(settings, 'GOOGLE_CLIENT_ID', '') and getattr(settings, 'GOOGLE_CLIENT_SECRET', ''))


def build_google_auth_uri(request) -> str:
    """
    Constructs the standard OAuth2 authorization URI with CSRF state protection.
    Explicitly saves the session to ensure state survives the external redirect.
    """
    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
    redirect_uri = request.build_absolute_uri(reverse('google_oauth_callback'))
    state = secrets.token_urlsafe(32)
    request.session['google_oauth_state'] = state
    request.session.save()

    scope = "openid email profile"
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': scope,
        'state': state,
        'access_type': 'online',
        'prompt': 'select_account',
    }
    encoded = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{encoded}"


def exchange_code_for_user_info(request, code: str, state: str) -> dict:
    """
    Exchanges OAuth2 authorization code for Google user information.
    Verifies state token to prevent CSRF authentication attacks.
    """
    saved_state = request.session.pop('google_oauth_state', None)
    if not saved_state or saved_state != state:
        logger.warning("Google OAuth state token mismatch (possible CSRF attack).")
        raise ValueError("Invalid OAuth security state token. Please try again.")

    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
    client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '')
    redirect_uri = request.build_absolute_uri(reverse('google_oauth_callback'))

    # Exchange code for tokens
    payload = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    }
    token_resp = requests.post(GOOGLE_TOKEN_URL, data=payload, timeout=10)
    if token_resp.status_code != 200:
        logger.error("Failed to exchange code with Google: %s", token_resp.text)
        raise ValueError("Failed to retrieve authentication tokens from Google.")

    tokens = token_resp.json()
    access_token = tokens.get('access_token')

    # Fetch user profile info
    headers = {'Authorization': f'Bearer {access_token}'}
    info_resp = requests.get(GOOGLE_USERINFO_URL, headers=headers, timeout=10)
    if info_resp.status_code != 200:
        logger.error("Failed to fetch user info from Google: %s", info_resp.text)
        raise ValueError("Failed to fetch candidate profile from Google.")

    info_data = info_resp.json()
    if not info_data.get("email_verified", False):
        raise ValueError("Your Google account email is not verified.")
    return info_data


def verify_google_credential_jwt(credential: str) -> dict:
    """
    Verifies a Google Identity Services (One-Tap / Sign-In Button) ID Token JWT.
    """
    params = {'id_token': credential}
    resp = requests.get(GOOGLE_TOKENINFO_URL, params=params, timeout=10)
    if resp.status_code != 200:
        raise ValueError("Invalid Google credential token.")

    data = resp.json()
    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
    if client_id and data.get('aud') != client_id:
        raise ValueError("Google token audience mismatch.")
    if str(data.get("email_verified", "")).lower() not in ("true", "1"):
        raise ValueError("Google token email is not verified.")

    return data


def get_or_create_candidate_from_google(email: str, name: str = "") -> tuple[User, bool]:
    """
    Finds or creates a candidate User record matching the verified Google email address.
    Generates a unique username and sets up the UserProfile automatically.
    """
    clean_email = email.strip().lower()
    user = User.objects.filter(email__iexact=clean_email).first()

    if user:
        return user, False

    # Derive username from email prefix (e.g. sarah from sarah@gmail.com)
    base_username = clean_email.split('@')[0]
    base_username = "".join(c for c in base_username if c.isalnum() or c in '_-')[:20] or 'candidate'
    
    username = base_username
    counter = 1
    while User.objects.filter(username__iexact=username).exists():
        username = f"{base_username}_{secrets.randbelow(9000) + 1000}"
        counter += 1
        if counter > 20:
            username = f"user_{secrets.token_hex(4)}"

    user = User.objects.create_user(
        username=username,
        email=clean_email
    )
    user.set_unusable_password()

    # Populate first/last name if provided
    if name:
        parts = name.strip().split(maxsplit=1)
        user.first_name = parts[0][:30]
        if len(parts) > 1:
            user.last_name = parts[1][:30]
    user.save()

    # UserProfile is created automatically by post_save signal
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.save()

    return user, True
