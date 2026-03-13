from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import RegisterForm
from .utils import send_otp_sms
import random

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False # Deactivate until OTP is verified
            user.save()
            
            # Generate OTP
            otp = str(random.randint(100000, 999999))
            mobile = form.cleaned_data.get('mobile')
            
            # Store in session
            request.session['registration_user_id'] = user.id
            request.session['registration_otp'] = otp
            request.session['registration_mobile'] = mobile
            
            # Send SMS
            success = send_otp_sms(mobile, otp)
            if success:
                messages.info(request, f'An OTP has been sent to {mobile}. Please verify to complete registration.')
            else:
                # We can choose to alert the user it failed but still allow them to verify if they somehow received it,
                # or we can resend. For now just show error msg.
                messages.error(request, 'Failed to send OTP SMS. Please contact support if you do not receive it.')
                
            return redirect('verify_otp')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

def verify_otp_view(request):
    if 'registration_user_id' not in request.session:
        messages.error(request, 'No active registration found. Please register first.')
        return redirect('register')
        
    mobile = request.session.get('registration_mobile', '')
        
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        expected_otp = request.session.get('registration_otp')
        
        if entered_otp and entered_otp == expected_otp:
            # Activate user
            try:
                user = User.objects.get(id=request.session['registration_user_id'])
                user.is_active = True
                user.save()
                
                # Clear session
                request.session.pop('registration_user_id', None)
                request.session.pop('registration_otp', None)
                request.session.pop('registration_mobile', None)
                
                messages.success(request, 'Mobile number verified successfully! You can now log in.')
                return redirect('login')
            except User.DoesNotExist:
                messages.error(request, 'User not found. Please register again.')
                return redirect('register')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
            
    return render(request, 'accounts/verify_otp.html', {'mobile': mobile})
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
