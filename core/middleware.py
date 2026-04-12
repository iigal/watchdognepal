import threading
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from user_agents import parse
from .models import VisitorLog, IPLocationCache
from .utils import get_client_ip, fetch_ip_location


class ForceDefaultLanguageMiddleware(MiddlewareMixin):
    """
    Ensure Nepali is the default language for first-time visitors.
    Django's LocaleMiddleware respects Accept-Language from the browser
    (typically 'en'), which overrides LANGUAGE_CODE='ne'. This middleware
    sets the language cookie to the configured default when no explicit
    choice has been made by the user.
    """
    def process_request(self, request):
        if settings.LANGUAGE_COOKIE_NAME not in request.COOKIES:
            from django.utils import translation
            translation.activate(settings.LANGUAGE_CODE)
            request.LANGUAGE_CODE = settings.LANGUAGE_CODE

    def process_response(self, request, response):
        if settings.LANGUAGE_COOKIE_NAME not in request.COOKIES:
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                settings.LANGUAGE_CODE,
                max_age=365 * 24 * 60 * 60,  # 1 year
                httponly=False,
                samesite='Lax',
            )
        return response

class VisitorTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to log page visits and trigger background IP geolocation.
    """
    def process_response(self, request, response):
        path = request.path
        
        # Don't track static files, media, or admin panel
        if any(path.startswith(prefix) for prefix in ['/static/', '/media/', '/admin/']):
            return response
            
        # Don't track staff/admin activity
        if hasattr(request, 'user') and request.user.is_authenticated and request.user.is_staff:
            return response

        ip_address = get_client_ip(request)
        
        # Define user agent
        ua_string = request.META.get('HTTP_USER_AGENT', '')
        user_agent = parse(ua_string)
        
        browser = user_agent.browser.family if user_agent.browser.family else "Unknown"
        os_name = user_agent.os.family if user_agent.os.family else "Unknown"
        device_type = "Desktop" # Default
        if user_agent.is_mobile:
            device_type = "Mobile"
        elif user_agent.is_tablet:
            device_type = "Tablet"
        elif user_agent.is_bot:
            device_type = "Bot"
        
        # Ensure session exists (for unauthenticated users)
        session_key = None
        if hasattr(request, 'session') and request.session.session_key:
            session_key = request.session.session_key
        
        user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
        
        try:
            # Save Visitor Log
            VisitorLog.objects.create(
                user=user,
                session_key=session_key,
                ip_address=ip_address,
                path=path,
                method=request.method,
                browser=browser,
                os_name=os_name,
                device_type=device_type,
                status_code=response.status_code
            )
        except Exception as e:
            # Logging should not crash the site
            import logging
            logging.getLogger(__name__).error(f"Failed to log visitor: {e}")
        
        # Check cache, fetch location asynchronously if not found
        if not IPLocationCache.objects.filter(ip_address=ip_address).exists():
            # Fire and forget thread
            thread = threading.Thread(target=fetch_ip_location, args=(ip_address,))
            thread.daemon = True
            thread.start()
            
        return response
