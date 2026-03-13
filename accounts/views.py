from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import RegisterForm
from .models import UserProfile
from .utils import send_otp_sms, send_otp_email
import random

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False # Deactivate until OTP is verified
            user.save()
            
            mobile = form.cleaned_data.get('mobile')
            
            # Create UserProfile to reserve the mobile number
            UserProfile.objects.create(user=user, mobile=mobile)
            
            # Generate OTPs
            mobile_otp = str(random.randint(100000, 999999))
            email_otp = str(random.randint(100000, 999999))
            mobile = form.cleaned_data.get('mobile')
            email = form.cleaned_data.get('email')
            
            # Store in session
            request.session['registration_user_id'] = user.id
            request.session['registration_mobile_otp'] = mobile_otp
            request.session['registration_email_otp'] = email_otp
            request.session['registration_mobile'] = mobile
            request.session['registration_email'] = email
            
            # Send SMS and Email
            sms_success = send_otp_sms(mobile, mobile_otp)
            email_success = send_otp_email(email, email_otp)
            
            if sms_success and email_success:
                messages.info(request, f'Verification codes have been sent to {mobile} and {email}.')
            elif sms_success:
                messages.warning(request, f'Code sent to {mobile}, but failed to send to {email}.')
            elif email_success:
                messages.warning(request, f'Code sent to {email}, but failed to send to {mobile}.')
            else:
                messages.error(request, 'Failed to send verification codes. Please contact support.')
                
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
        
    if request.method == 'POST':
        entered_mobile_otp = request.POST.get('mobile_otp')
        entered_email_otp = request.POST.get('email_otp')
        
        expected_mobile_otp = request.session.get('registration_mobile_otp')
        expected_email_otp = request.session.get('registration_email_otp')
        
        if (entered_mobile_otp and entered_mobile_otp == expected_mobile_otp) and \
           (entered_email_otp and entered_email_otp == expected_email_otp):
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
                
                messages.success(request, 'Mobile and Email unified successfully! You can now log in.')
                return redirect('login')
            except User.DoesNotExist:
                messages.error(request, 'User not found. Please register again.')
                return redirect('register')
        else:
            messages.error(request, 'Invalid verification code(s). Please try again.')
            
    return render(request, 'accounts/verify_otp.html', {'mobile': mobile, 'email': email})
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
