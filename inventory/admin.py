from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Product, ProductValuation
from dashboard.sites import custom_admin_site
from dashboard.utils import export_to_excel
from django.db.models import Sum, F, DecimalField

class ProductAdmin(ModelAdmin):
    list_display = ('name', 'import_number', 'model', 'brand', 'unit_of_measure', 'display_quantity', 'listing_date')
    list_filter = ('listing_date', 'brand', 'model', 'unit_of_measure')
    search_fields = ('name', 'import_number', 'model', 'brand')
    actions = [export_to_excel]

    def display_quantity(self, obj):
        if obj.unit_of_measure == 'unit':
            return int(obj.quantity)
        return obj.quantity
    display_quantity.short_description = 'Quantity'
    display_quantity.admin_order_field = 'quantity'

    class Media:
        js = (
            'admin/js/auto_search.js',
            'admin/js/inventory_product_admin.js',
        )

    def get_fieldsets(self, request, obj=None):
        # Base fields visible to everyone
        fields = ['name', 'import_number', 'model', 'brand', 'unit_of_measure', 'quantity']
        
        # Logic for Purchase Rate visibility:
        # Only Superusers/Admins see it.
        if request.user.is_superuser or request.user.groups.filter(name='Admin').exists():
            fields.append('purchase_rate')
            
        return (
            (None, {
                'fields': fields
            }),
        )

    def get_readonly_fields(self, request, obj=None):
        # Prevent Co-Admin from seeing the value in edit mode even if they try to hack it
        if not request.user.is_superuser and not request.user.groups.filter(name='Admin').exists():
            return self.readonly_fields + ('purchase_rate',)
        return self.readonly_fields

    def get_list_display(self, request):
        # Only Admins see purchase_rate in the main list
        if request.user.is_superuser or request.user.groups.filter(name='Admin').exists():
            return ('name', 'import_number', 'model', 'brand', 'unit_of_measure', 'display_quantity', 'purchase_rate', 'listing_date')
        return ('name', 'import_number', 'model', 'brand', 'unit_of_measure', 'display_quantity', 'listing_date')

    def has_add_permission(self, request):
        # Only Admins/Superusers can add products
        if request.user.is_superuser or request.user.groups.filter(name='Admin').exists():
            return True
        return False

    def has_change_permission(self, request, obj=None):
        # Admins and Co-Admins can change products
        if request.user.is_superuser or request.user.groups.filter(name__in=['Admin', 'Co-Admin']).exists():
            return True
        return False

    def has_view_permission(self, request, obj=None):
        # All authenticated staff can view products
        return True

    def has_delete_permission(self, request, obj=None):
        # Co-Admins cannot delete products
        if request.user.groups.filter(name='Co-Admin').exists() and not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)

@admin.register(ProductValuation, site=custom_admin_site)
class ProductValuationAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'model', 'display_quantity', 'purchase_rate', 'total_valuation')
    list_filter = ('brand', 'model')
    search_fields = ('name', 'brand', 'model')
    actions = [export_to_excel]
    change_list_template = 'admin/inventory/productvaluation/change_list.html'

    def display_quantity(self, obj):
        if obj.unit_of_measure == 'unit':
            return int(obj.quantity)
        return obj.quantity
    display_quantity.short_description = 'Stock'

    def total_valuation(self, obj):
        if obj.quantity and obj.purchase_rate:
            return f"৳{obj.quantity * obj.purchase_rate:,.2f}"
        return "৳0.00"
    total_valuation.short_description = 'Total Value'

    def changelist_view(self, request, extra_context=None):
        # Calculate Grand Total
        grand_total = Product.objects.all().aggregate(
            total=Sum(F('quantity') * F('purchase_rate'), output_field=DecimalField())
        )['total'] or 0
        
        extra_context = extra_context or {}
        extra_context['grand_total'] = grand_total
        return super().changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        return False # Read-only report

    def has_delete_permission(self, request, obj=None):
        return False # Read-only report

    def get_queryset(self, request):
        # Restrict access to Admins/Superusers
        if not (request.user.is_superuser or request.user.groups.filter(name='Admin').exists()):
            return ProductValuation.objects.none()
        return super().get_queryset(request)

custom_admin_site.register(Product, ProductAdmin)
admin.site.register(Product, ProductAdmin)
