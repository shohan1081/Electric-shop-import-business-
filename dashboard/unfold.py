from django.utils.translation import gettext_lazy as _

def dashboard_callback(request, context):
    """
    Injected into templates/admin/index.html
    """
    context.update({
        "greeting": "Welcome back,",
        "user_name": request.user.get_full_name() or request.user.username,
    })
    return context

def environment_callback(request):
    """
    Displays a badge in the top right corner.
    """
    return ["Production", "danger"] # Options: info, danger, warning, success

def badge_callback(request):
    from sales.models import Sale
    # Example: Show count of sales today as a badge
    return Sale.objects.filter(sold_date__date__gte=request.user.date_joined).count()
