from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils import timezone
from .forms import RegisterForm
from .models import UserProfile, SMSLog, UserActivityLog
from .utils import send_otp_sms, send_otp_email, get_client_ip
from core.utils import get_country_from_ip
import random

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user_ip = get_client_ip(request)
            # Detect country and determine verification method
            country = get_country_from_ip(user_ip)
            is_nepal = country == 'Nepal'
            verification_method = 'sms' if is_nepal else 'email'
            
            # Rate limiting check for SMS (only if SMS is used)
            if verification_method == 'sms':
                today = timezone.now().date()
                sms_count = SMSLog.objects.filter(ip_address=user_ip, sent_at__date=today).count()
                if sms_count >= 10:
                    messages.error(request, 'You have exceeded the maximum number of SMS requests for today. Please try again tomorrow.')
                    return redirect('register')
                
            user = form.save(commit=False)
            user.is_active = False # Deactivate until OTP is verified
            user.save()
            
            mobile = form.cleaned_data.get('mobile')
            email = form.cleaned_data.get('email')
            
            # Create UserProfile
            UserProfile.objects.create(user=user, mobile=mobile)
            
            # Generate OTPs
            mobile_otp = str(random.randint(100000, 999999))
            email_otp = str(random.randint(100000, 999999))
            
            # Store in session
            request.session['registration_user_id'] = user.id
            request.session['registration_mobile_otp'] = mobile_otp
            request.session['registration_email_otp'] = email_otp
            request.session['registration_mobile'] = mobile
            request.session['registration_email'] = email
            request.session['verification_method'] = verification_method
            
            # Send requested OTP
            success = False
            if verification_method == 'sms':
                success = send_otp_sms(mobile, mobile_otp, ip_address=user_ip)
                if success:
                    messages.info(request, f'A verification code has been sent to your mobile number: {mobile}.')
                else:
                    messages.error(request, 'Failed to send SMS verification code. Please try again.')
            else:
                success = send_otp_email(email, email_otp)
                if success:
                    messages.info(request, f'A verification code has been sent to your email address: {email}.')
                else:
                    messages.error(request, 'Failed to send email verification code. Please try again.')
            
            if not success:
                # Cleanup user if notification failed to avoid dead accounts
                user.delete()
                return redirect('register')
                
            return redirect('verify_otp')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

def verify_otp_view(request):
    if 'registration_user_id' not in request.session:
        messages.error(request, 'No active registration found. Please register first.')
        return redirect('register')
        
    mobile = request.session.get('registration_mobile', '')
    email = request.session.get('registration_email', '')
    method = request.session.get('verification_method', 'sms')
        
    if request.method == 'POST':
        is_valid = False
        
        if method == 'sms':
            entered_otp = request.POST.get('mobile_otp')
            expected_otp = request.session.get('registration_mobile_otp')
            is_valid = entered_otp and entered_otp == expected_otp
        else:
            entered_otp = request.POST.get('email_otp')
            expected_otp = request.session.get('registration_email_otp')
            is_valid = entered_otp and entered_otp == expected_otp
            
        if is_valid:
            # Activate user
            try:
                user = User.objects.get(id=request.session['registration_user_id'])
                user.is_active = True
                user.save()
                
                # Clear session
                request.session.pop('registration_user_id', None)
                request.session.pop('registration_mobile_otp', None)
                request.session.pop('registration_email_otp', None)
                request.session.pop('registration_mobile', None)
                request.session.pop('registration_email', None)
                request.session.pop('verification_method', None)
                
                messages.success(request, 'Identity verified successfully! You can now log in.')
                return redirect('login')
            except User.DoesNotExist:
                messages.error(request, 'User not found. Please register again.')
                return redirect('register')
        else:
            messages.error(request, 'Invalid verification code. Please try again.')
            
    return render(request, 'accounts/verify_otp.html', {
        'mobile': mobile, 
        'email': email,
        'method': method
    })
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')


from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

@login_required
def profile_view(request):
    """User profile page showing gamification stats."""
    profile = request.user.profile
    recent_logs = request.user.activity_logs.all()[:10]
    
    context = {
        'profile': profile,
        'recent_logs': recent_logs,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def user_logs_view(request):
    """User-facing activity log page."""
    logs = request.user.activity_logs.all()
    
    # Filter by action type
    action_filter = request.GET.get('action', '')
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    paginator = Paginator(logs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'action_filter': action_filter,
        'action_choices': UserActivityLog.ACTION_CHOICES,
    }
    return render(request, 'accounts/user_logs.html', context)


@login_required
def admin_logs_view(request):
    """Superadmin dashboard to view all user logs globally."""
    if not request.user.is_superuser:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    logs = UserActivityLog.objects.all().select_related('user')
    
    # Filters
    action_filter = request.GET.get('action', '')
    user_filter = request.GET.get('user', '')
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    if user_filter:
        logs = logs.filter(user__username__icontains=user_filter)
    
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'action_filter': action_filter,
        'user_filter': user_filter,
        'action_choices': UserActivityLog.ACTION_CHOICES,
    }
    return render(request, 'accounts/admin_logs.html', context)
