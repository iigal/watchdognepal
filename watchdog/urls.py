"""
URL configuration for watchdog project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import (
    home, submit_activity, vote_activity,
    party_list, party_detail,
    elected_member_list, elected_member_detail,
    activities_list,
    petition_list, petition_detail, petition_create, petition_sign,
    dashboard,
)

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('activities/', activities_list, name='activities_list'),
    path('submit/', submit_activity, name='submit_activity'),
    path('vote/<int:activity_id>/', vote_activity, name='vote_activity'),
    path('parties/', party_list, name='party_list'),
    path('parties/<int:party_id>/', party_detail, name='party_detail'),
    path('members/', elected_member_list, name='elected_member_list'),
    path('members/<int:member_id>/', elected_member_detail, name='elected_member_detail'),
    path('accounts/', include('accounts.urls')),
    # Petitions
    path('petitions/', petition_list, name='petition_list'),
    path('petitions/create/', petition_create, name='petition_create'),
    path('petitions/<int:petition_id>/', petition_detail, name='petition_detail'),
    path('petitions/<int:petition_id>/sign/', petition_sign, name='petition_sign'),
    # Dashboard
    path('dashboard/', dashboard, name='dashboard'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
