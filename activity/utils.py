import re
from .models import LoginActivity


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def parse_user_agent(user_agent_string):
    if not user_agent_string:
        return 'Unknown', 'Unknown', 'OTHER'
    
    user_agent_string = user_agent_string.lower()
    
    browser = 'Unknown'
    os = 'Unknown'
    device_type = 'OTHER'
    
    if 'chrome' in user_agent_string and 'edg' not in user_agent_string:
        browser = 'Chrome'
    elif 'firefox' in user_agent_string:
        browser = 'Firefox'
    elif 'safari' in user_agent_string and 'chrome' not in user_agent_string:
        browser = 'Safari'
    elif 'edg' in user_agent_string:
        browser = 'Edge'
    elif 'opera' in user_agent_string or 'opr' in user_agent_string:
        browser = 'Opera'
    elif 'msie' in user_agent_string or 'trident' in user_agent_string:
        browser = 'Internet Explorer'
    
    if 'windows' in user_agent_string:
        os = 'Windows'
        device_type = 'DESKTOP'
    elif 'macintosh' in user_agent_string or 'mac os x' in user_agent_string:
        os = 'macOS'
        device_type = 'DESKTOP'
    elif 'linux' in user_agent_string:
        os = 'Linux'
        device_type = 'DESKTOP'
    elif 'android' in user_agent_string:
        os = 'Android'
        if 'mobile' in user_agent_string:
            device_type = 'MOBILE'
        else:
            device_type = 'TABLET'
    elif 'iphone' in user_agent_string:
        os = 'iOS'
        device_type = 'MOBILE'
    elif 'ipad' in user_agent_string:
        os = 'iOS'
        device_type = 'TABLET'
    elif 'ipod' in user_agent_string:
        os = 'iOS'
        device_type = 'MOBILE'
    
    return browser, os, device_type


def create_login_activity(user, request):
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    browser, operating_system, device_type = parse_user_agent(user_agent)
    
    LoginActivity.objects.create(
        user=user,
        ip_address=ip_address,
        browser=browser,
        operating_system=operating_system,
        device_type=device_type
    )

