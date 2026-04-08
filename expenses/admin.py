from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import DailyExpense, ExpenseItem, Employee, SalaryTransaction, AccountTransfer, ProductOrder
from dashboard.sites import custom_admin_site

class ExpenseItemInline(TabularInline):
    model = ExpenseItem
    extra = 1

@admin.register(DailyExpense, site=custom_admin_site)
class DailyExpenseAdmin(ModelAdmin):
    list_display = ('date', 'total_amount_display', 'items_summary')
    inlines = [ExpenseItemInline]
    ordering = ('-date',)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('items')

    def total_amount_display(self, obj):
        return f"৳{obj.total_amount}"
    total_amount_display.short_description = 'Total Amount'

    def items_summary(self, obj):
        return ", ".join([f"{item.description} (৳{item.amount})" for item in obj.items.all()])
    items_summary.short_description = 'Items Summary'

class SalaryTransactionInline(TabularInline):
    model = SalaryTransaction
    extra = 1
    ordering = ('-date',)

@admin.register(Employee, site=custom_admin_site)
class EmployeeAdmin(ModelAdmin):
    list_display = ('name', 'designation', 'base_salary', 'current_balance_display')
    search_fields = ('name', 'phone')
    inlines = [SalaryTransactionInline]

    def current_balance_display(self, obj):
        return f"৳{obj.current_balance}"
    current_balance_display.short_description = 'Current Owed'

@admin.register(SalaryTransaction, site=custom_admin_site)
class SalaryTransactionAdmin(ModelAdmin):
    list_display = ('employee', 'transaction_type', 'amount', 'date')
    list_filter = ('transaction_type', 'date')
    search_fields = ('employee__name', 'note')
    ordering = ('-date',)

@admin.register(AccountTransfer, site=custom_admin_site)
class AccountTransferAdmin(ModelAdmin):
    list_display = ('date', 'from_account_display', 'to_account_display', 'amount', 'note')
    list_filter = ('from_account', 'to_account', 'date')
    search_fields = ('note',)
    ordering = ('-date',)

    def from_account_display(self, obj):
        return obj.get_from_account_display()
    from_account_display.short_description = 'From'

    def to_account_display(self, obj):
        return obj.get_to_account_display()
    to_account_display.short_description = 'To'

@admin.register(ProductOrder, site=custom_admin_site)
class ProductOrderAdmin(ModelAdmin):
    list_display = ('supplier_name', 'product', 'quantity', 'total_price', 'amount_paid', 'due_amount', 'payment_method', 'order_date')
    list_filter = ('payment_method', 'order_date', 'product')
    search_fields = ('supplier_name', 'product__name', 'note')
    autocomplete_fields = ('product',)
    readonly_fields = ('total_price', 'due_amount')
    ordering = ('-order_date',)
