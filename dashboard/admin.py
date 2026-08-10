from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from unfold.admin import ModelAdmin
from .sites import custom_admin_site
from .models import ProfitSetting

# Registering User and Group models to the custom admin site
custom_admin_site.register(User, UserAdmin)
custom_admin_site.register(Group, GroupAdmin)

@admin.register(ProfitSetting, site=custom_admin_site)
class ProfitSettingAdmin(ModelAdmin):
    list_display = ('__str__', 'show_profit_to_coadmins')

    def has_add_permission(self, request):
        if ProfitSetting.objects.exists():
            return False
        return super().has_add_permission(request)
