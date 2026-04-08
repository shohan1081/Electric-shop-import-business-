from django.contrib import admin
from django.utils import timezone
from django.db.models import Sum, F, DecimalField
from dashboard.sites import custom_admin_site
from .models import DailyActivity
from sales.models import Sale, Payment, ProductReturn, Refund
from expenses.models import DailyExpense, ExpenseItem, SalaryTransaction, ProductOrder
from datetime import timedelta

class DateRangeFilter(admin.SimpleListFilter):
    title = 'Time Period'
    parameter_name = 'time_period'

    def lookups(self, request, model_admin):
        return (
            ('today', 'Today'),
            ('this_week', 'This Week'),
            ('this_month', 'This Month'),
            ('this_year', 'This Year'),
        )

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == 'today':
            return queryset.filter(action_time__date=today)
        if self.value() == 'this_week':
            start_week = today - timedelta(days=today.weekday())
            return queryset.filter(action_time__date__gte=start_week)
        if self.value() == 'this_month':
            return queryset.filter(action_time__month=today.month, action_time__year=today.year)
        if self.value() == 'this_year':
            return queryset.filter(action_time__year=today.year)
        return queryset

@admin.register(DailyActivity, site=custom_admin_site)
class DailyActivityAdmin(admin.ModelAdmin):
    list_display = ('action_time', 'user', 'content_type', 'object_repr', 'action_flag_display', 'change_message')
    list_filter = (DateRangeFilter, 'user', 'content_type') # Removed action_flag filter as it's now fixed to ADDITION
    search_fields = ('object_repr', 'change_message')
    date_hierarchy = 'action_time'
    change_list_template = 'admin/reports/dailyactivity/change_list.html'

    def get_queryset(self, request):
        from django.contrib.contenttypes.models import ContentType
        qs = super().get_queryset(request)
        
        # 1. Only show ADDITIONS
        qs = qs.filter(action_flag=admin.models.ADDITION)
        
        # 2. Only show main operation models
        main_models = [
            ('inventory', 'product'),
            ('sales', 'sale'),
            ('sales', 'payment'),
            ('sales', 'productreturn'),
            ('sales', 'refund'),
            ('expenses', 'dailyexpense'),
            ('expenses', 'salarytransaction'),
            ('expenses', 'accounttransfer'),
            ('expenses', 'productorder'),
        ]
        
        ct_ids = []
        for app, model in main_models:
            try:
                ct = ContentType.objects.get(app_label=app, model=model)
                ct_ids.append(ct.id)
            except ContentType.DoesNotExist:
                continue
                
        return qs.filter(content_type_id__in=ct_ids)

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

    def action_flag_display(self, obj):
        from django.utils.html import format_html
        if obj.is_addition(): return format_html('<b style="color:green;">{}</b>', 'Addition')
        if obj.is_change(): return format_html('<b style="color:orange;">{}</b>', 'Change')
        if obj.is_deletion(): return format_html('<b style="color:red;">{}</b>', 'Deletion')
        return "Unknown"
    action_flag_display.short_description = "Action"

    def changelist_view(self, request, extra_context=None):
        # 1. Determine the date range based on filters
        period = request.GET.get('time_period', 'today')
        today = timezone.now().date()
        start_date = today

        if period == 'this_week':
            start_date = today - timedelta(days=today.weekday())
        elif period == 'this_month':
            start_date = today.replace(day=1)
        elif period == 'this_year':
            start_date = today.replace(month=1, day=1)
        
        # Financial Aggregations
        # Sales
        sales = Sale.objects.filter(sold_date__date__gte=start_date)
        total_sales_volume = sales.aggregate(Sum('total_price'))['total_price__sum'] or 0
        direct_cash = sales.exclude(payment_method='bank_check').aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        
        # Payments
        payments_cleared = Payment.objects.filter(payment_date__date__gte=start_date, status='CLEARED').aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        
        # Returns/Refunds
        returns_value = ProductReturn.objects.filter(return_date__date__gte=start_date).aggregate(
            total=Sum(F('quantity_returned') * F('sale__selling_price_at_that_time'), output_field=DecimalField())
        )['total'] or 0
        refunds = Refund.objects.filter(refund_date__date__gte=start_date, status='CLEARED').aggregate(Sum('amount'))['amount__sum'] or 0
        return_refunds = ProductReturn.objects.filter(return_date__date__gte=start_date).aggregate(Sum('amount_refunded'))['amount_refunded__sum'] or 0

        # Expenses
        daily_expenses = ExpenseItem.objects.filter(daily_expense__date__gte=start_date).aggregate(Sum('amount'))['amount__sum'] or 0
        salaries = SalaryTransaction.objects.filter(date__gte=start_date, transaction_type__in=['PAYMENT', 'ADVANCE']).aggregate(Sum('amount'))['amount__sum'] or 0
        orders = ProductOrder.objects.filter(order_date__date__gte=start_date).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0

        total_cash_received = direct_cash + payments_cleared - refunds - return_refunds
        total_expenses = daily_expenses + salaries + orders
        
        # Simplified Profit Logic (Revenue - Returns - COGS - Expenses)
        # Note: True profit requires COGS (Purchase Rate), similar to Dashboard logic
        total_profit_potential = 0
        for sale in sales.select_related('product'):
            purchase_rate = sale.product.purchase_rate or 0
            total_profit_potential += (sale.quantity_sold * (sale.selling_price_at_that_time - purchase_rate))

        for ret in ProductReturn.objects.filter(return_date__date__gte=start_date).select_related('sale__product'):
            purchase_rate = ret.sale.product.purchase_rate or 0
            total_profit_potential -= (ret.quantity_returned * (ret.sale.selling_price_at_that_time - purchase_rate))

        extra_context = extra_context or {}
        extra_context['report_summaries'] = {
            'total_sales_volume': total_sales_volume - returns_value,
            'total_cash_received': total_cash_received,
            'total_expenses': total_expenses,
            'net_profit': total_profit_potential - total_expenses
        }
        
        return super().changelist_view(request, extra_context=extra_context)
