from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.widgets import UnfoldAdminSelect2Widget
from .models import Customer, Sale, ProductReturn, Payment, Refund
from django.db import models
from dashboard.sites import custom_admin_site
from dashboard.utils import export_to_excel
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, time

class PaymentInline(TabularInline):
    model = Payment
    extra = 1
    fields = ['amount_paid', 'account', 'payment_method', 'status', 'cheque_number', 'cheque_date', 'clearance_date', 'note', 'payment_date']
    readonly_fields = ('payment_date', 'clearance_date', 'status') # Status is changed via actions, not directly editable here

class CustomerProductReturnInline(TabularInline):
    model = ProductReturn
    extra = 0
    fields = ['get_product_name', 'quantity_returned', 'amount_refunded', 'account', 'reason', 'return_date']
    readonly_fields = ('get_product_name', 'quantity_returned', 'amount_refunded', 'account', 'reason', 'return_date')
    can_delete = False
    verbose_name = "Product Return History"
    verbose_name_plural = "Product Returns History"

    def get_product_name(self, obj):
        if obj.sale and obj.sale.product:
            return obj.sale.product.name
        return "N/A"
    get_product_name.short_description = 'Product Name'

    def has_add_permission(self, request, obj=None):
        return False

class ProductReturnInline(TabularInline):
    model = ProductReturn
    extra = 1
    fields = ['get_customer_name', 'quantity_returned', 'amount_refunded', 'account', 'reason']
    readonly_fields = ('get_customer_name',)
    
    def get_customer_name(self, obj):
        if obj.sale and obj.sale.customer:
            return obj.sale.customer.name
        return "N/A"
    get_customer_name.short_description = 'Customer'

class SaleInline(TabularInline):
    model = Sale
    extra = 0
    fields = ['product', 'quantity_sold', 'selling_price_at_that_time', 'total_price', 'amount_paid', 'due_amount', 'sold_date']
    readonly_fields = ('product', 'total_price', 'due_amount', 'sold_date')
    show_change_link = True

class RefundInline(TabularInline):
    model = Refund
    extra = 1
    fields = ['amount', 'account', 'refund_method', 'status', 'cheque_number', 'cheque_date', 'clearance_date', 'note', 'refund_date']
    readonly_fields = ('refund_date', 'clearance_date')

class CustomerAdmin(ModelAdmin):
    list_display = ('name', 'phone', 'total_due', 'created_at')
    search_fields = ('name', 'phone', 'email')
    inlines = [SaleInline, PaymentInline, CustomerProductReturnInline, RefundInline]
    actions = [export_to_excel]
    change_form_template = 'admin/sales/customer/change_form.html'

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        if obj:
            context.update({
                'transaction_history': obj.get_transaction_history(),
            })
        return super().render_change_form(request, context, add, change, form_url, obj)

    class Media:
        js = ('admin/js/auto_search.js',)

class DefaultTodayFilter(admin.SimpleListFilter):
    title = 'date filter'
    parameter_name = 'sold_date'
    template = 'admin/sales/date_range_filter.html'

    def __init__(self, request, params, model, model_admin):
        super().__init__(request, params, model, model_admin)
        self.from_date = request.GET.get('sold_date__range__gte')
        self.to_date = request.GET.get('sold_date__range__lte')
        self.query_params = {k: v for k, v in request.GET.items() if k not in ['sold_date', 'sold_date__range__gte', 'sold_date__range__lte', 'p']}

    def lookups(self, request, model_admin):
        return (
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('last_7_days', 'Last 7 Days'),
            ('this_month', 'This Month'),
            ('all', 'All Time'),
            ('custom', 'Custom Range'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'today' or self.value() is None:
            today = timezone.now().date()
            return queryset.filter(sold_date__date=today)
        
        if self.value() == 'yesterday':
            yesterday = timezone.now().date() - timezone.timedelta(days=1)
            return queryset.filter(sold_date__date=yesterday)

        if self.value() == 'last_7_days':
            seven_days_ago = timezone.now().date() - timezone.timedelta(days=7)
            return queryset.filter(sold_date__date__gte=seven_days_ago)

        if self.value() == 'this_month':
            return queryset.filter(sold_date__month=timezone.now().month, sold_date__year=timezone.now().year)

        if self.value() == 'all':
            return queryset

        if self.value() == 'custom':
            from_date = request.GET.get('sold_date__range__gte')
            to_date = request.GET.get('sold_date__range__lte')
            
            if from_date and to_date:
                return queryset.filter(sold_date__date__range=[from_date, to_date])
            elif from_date:
                return queryset.filter(sold_date__date__gte=from_date)
            elif to_date:
                return queryset.filter(sold_date__date__lte=to_date)

        return queryset

    def expected_parameters(self):
        return [self.parameter_name, 'sold_date__range__gte', 'sold_date__range__lte']

class SaleAdmin(ModelAdmin):
    list_display = ('customer', 'product', 'quantity_sold', 'total_price', 'amount_paid', 'payment_method', 'account', 'is_conditional', 'due_amount', 'sold_date')
    list_filter = (DefaultTodayFilter, 'is_conditional', 'payment_method', 'customer', 'product', 'account')
    search_fields = ('customer__name', 'product__name', 'condition_notes')
    formfield_overrides = {
        models.ForeignKey: {'widget': UnfoldAdminSelect2Widget},
    }
    readonly_fields = ('total_price', 'due_amount', 'sold_date')
    inlines = [ProductReturnInline]
    actions = [export_to_excel]

    class Media:
        js = ('admin/js/auto_search.js', 'admin/js/payment_logic.js')

    def get_fieldsets(self, request, obj=None):
        fields = [
            'customer', 'product', 'quantity_sold', 'selling_price_at_that_time', 
            'transport_fee', 'total_price', 'amount_paid', 
            'is_conditional', 'condition_notes',
            'payment_method', 'account',
            'due_amount', 'sold_date'
        ]
        return ((None, {'fields': fields}),)

class PaymentAdmin(ModelAdmin):
    list_display = ('customer', 'amount_paid', 'account', 'payment_method', 'status_display', 'cheque_number', 'cheque_date', 'clearance_date', 'payment_date')
    list_filter = ('payment_method', 'status', 'payment_date', 'account')
    search_fields = ('customer__name', 'cheque_number', 'account__name')
    autocomplete_fields = ('customer', 'account')
    readonly_fields = ('payment_date', 'clearance_date')
    actions = [export_to_excel, 'mark_cheque_cleared', 'mark_cheque_bounced']

    class Media:
        js = ('admin/js/auto_search.js',)

    def get_fieldsets(self, request, obj=None):
        fields = [
            'customer', 'amount_paid', 'account',
            'payment_method', 'status', 'cheque_number', 'cheque_date', 'clearance_date',
            'payment_date', 'note'
        ]
        return ((None, {'fields': fields}),)

    def status_display(self, obj):
        colors = {
            'PENDING': 'orange',
            'CLEARED': 'green',
            'BOUNCED': 'red',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'

    def mark_cheque_cleared(self, request, queryset):
        updated_count = 0
        for payment in queryset:
            if payment.payment_method == 'bank_check' and payment.status == 'PENDING':
                payment.status = 'CLEARED'
                payment.save()
                updated_count += 1
        if updated_count > 0:
            self.message_user(request, f"{updated_count} cheque payment(s) marked as CLEARED and customer due updated.", messages.SUCCESS)
        else:
            self.message_user(request, "No pending cheque payments selected.", messages.WARNING)
    mark_cheque_cleared.short_description = "Mark selected cheques as Cleared"

    def mark_cheque_bounced(self, request, queryset):
        updated_count = 0
        for payment in queryset:
            if payment.payment_method == 'bank_check' and payment.status == 'PENDING':
                payment.status = 'BOUNCED'
                payment.save()
                updated_count += 1
            elif payment.payment_method == 'bank_check' and payment.status == 'CLEARED':
                payment.status = 'BOUNCED'
                payment.save()
                updated_count += 1
        if updated_count > 0:
            self.message_user(request, f"{updated_count} cheque payment(s) marked as BOUNCED.", messages.WARNING)
        else:
            self.message_user(request, "No pending or cleared cheque payments selected.", messages.WARNING)
    mark_cheque_bounced.short_description = "Mark selected cheques as Bounced"


class ProductReturnAdmin(ModelAdmin):
    list_display = ('sale', 'quantity_returned', 'amount_refunded', 'account', 'refund_method', 'return_date')
    search_fields = ('sale__customer__name', 'sale__product__name', 'account__name')
    raw_id_fields = ('sale',)
    actions = [export_to_excel]

    class Media:
        js = ('admin/js/auto_search.js',)

    def get_fieldsets(self, request, obj=None):
        fields = [
            'sale', 'quantity_returned', 'reason',
            'amount_refunded', 'account', 'refund_method'
        ]
        return ((None, {'fields': fields}),)

    def has_add_permission(self, request):
        if request.user.is_superuser or request.user.groups.filter(name__in=['Admin', 'Co-Admin']).exists():
            return True
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser or request.user.groups.filter(name__in=['Admin', 'Co-Admin']).exists():
            return True
        return super().has_change_permission(request, obj)

class RefundAdmin(ModelAdmin):
    list_display = ('customer', 'amount', 'account', 'refund_method', 'status', 'refund_date')
    list_filter = ('refund_method', 'status', 'refund_date', 'account')
    search_fields = ('customer__name', 'account__name', 'cheque_number')
    autocomplete_fields = ('customer', 'account')
    readonly_fields = ('refund_date', 'clearance_date')
    actions = [export_to_excel, 'mark_refund_cleared', 'mark_refund_bounced']

    class Media:
        js = ('admin/js/auto_search.js',)

    def mark_refund_cleared(self, request, queryset):
        updated_count = 0
        for refund in queryset:
            if refund.refund_method == 'bank_check' and refund.status == 'PENDING':
                refund.status = 'CLEARED'
                refund.save()
                updated_count += 1
        self.message_user(request, f"{updated_count} refund(s) marked as CLEARED.")
    mark_refund_cleared.short_description = "Mark selected refunds as Cleared"

    def mark_refund_bounced(self, request, queryset):
        updated_count = 0
        for refund in queryset:
            if refund.refund_method == 'bank_check' and refund.status != 'BOUNCED':
                refund.status = 'BOUNCED'
                refund.save()
                updated_count += 1
        self.message_user(request, f"{updated_count} refund(s) marked as BOUNCED.")
    mark_refund_bounced.short_description = "Mark selected refunds as Bounced"

custom_admin_site.register(Customer, CustomerAdmin)
custom_admin_site.register(Sale, SaleAdmin)
custom_admin_site.register(Payment, PaymentAdmin)
custom_admin_site.register(ProductReturn, ProductReturnAdmin)
custom_admin_site.register(Refund, RefundAdmin)
