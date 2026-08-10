from django.db import models

class ProfitSetting(models.Model):
    show_profit_to_coadmins = models.BooleanField(
        default=False, 
        verbose_name="Allow Co-Admins & Staff to view Profit data",
        help_text="If unchecked, profit calculations and profit columns are only visible to Superusers (Main Admin)."
    )

    class Meta:
        verbose_name = "Profit Visibility Setting"
        verbose_name_plural = "Profit Visibility Settings"

    def __str__(self):
        return f"Profit Visibility Setting ({'Enabled for Co-Admins' if self.show_profit_to_coadmins else 'Superuser Only'})"

    @classmethod
    def can_user_see_profit(cls, user):
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        setting = cls.objects.first()
        if setting and setting.show_profit_to_coadmins:
            return True
        return False
