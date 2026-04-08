from django.urls import path
from dashboard.sites import custom_admin_site
from sales.views import export_customer_history

urlpatterns = [
    path('admin/sales/customer/<int:customer_id>/export/', export_customer_history, name='export_customer_history'),
    path('admin/', custom_admin_site.urls),
]
