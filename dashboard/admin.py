from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from .sites import custom_admin_site

# Registering User and Group models to the custom admin site
custom_admin_site.register(User, UserAdmin)
custom_admin_site.register(Group, GroupAdmin)
