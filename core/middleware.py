import threading
from django.utils.deprecation import MiddlewareMixin
from user_agents import parse
from .models import VisitorLog, IPLocationCache
from .utils import get_client_ip, fetch_ip_location

class VisitorTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to log page visits and trigger background IP geolocation.
    """
    def process_response(self, request, response):
        path = request.path
        
        # Don't track static files, media, or admin panel
        if any(path.startswith(prefix) for prefix in ['/static/', '/media/', '/admin/']):
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
        
        # Check cache, fetch location asynchronously if not found
        if not IPLocationCache.objects.filter(ip_address=ip_address).exists():
            # Fire and forget thread
            thread = threading.Thread(target=fetch_ip_location, args=(ip_address,))
            thread.daemon = True
            thread.start()
            
        return response
