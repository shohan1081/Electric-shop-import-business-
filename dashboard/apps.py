from django.apps import AppConfig
import django.contrib.admin.apps

class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'
    verbose_name = 'Dashboard'

class CustomAdminConfig(django.contrib.admin.apps.AdminConfig):
    default_site = 'dashboard.sites.CustomAdminSite'
