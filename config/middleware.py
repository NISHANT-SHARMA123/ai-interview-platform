from django.conf import settings

class SecurityHeadersMiddleware:
    """
    Appends Content-Security-Policy and permissions headers required for
    browser-side MediaPipe WASM, WebWorkers, and WebRTC MediaDevices.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if hasattr(settings, 'CSP_HEADER_POLICY'):
            response['Content-Security-Policy'] = settings.CSP_HEADER_POLICY
        
        # Permissions policy explicitly allowing camera and microphone only on self
        response['Permissions-Policy'] = "camera=(self), microphone=(self), display-capture=()"
        response['X-Content-Type-Options'] = 'nosniff'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response
