from django.urls import path
from dashboard.sites import custom_admin_site
from sales.views import export_customer_history
from dashboard.views import download_backup

urlpatterns = [
    path('admin/sales/customer/<int:customer_id>/export/', export_customer_history, name='export_customer_history'),
    path('admin/backup/download/', download_backup, name='download_backup'),
    path('admin/', custom_admin_site.urls),
]
