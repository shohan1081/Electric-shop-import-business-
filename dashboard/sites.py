from django.contrib import admin
from unfold.sites import UnfoldAdminSite
from django.db.models import Sum, Q, F, DecimalField
from datetime import timedelta
from django.utils.timezone import now

class CustomAdminSite(UnfoldAdminSite):
    site_header = "Company Dashboard"
    site_title = "Global Trade Admin"
    index_title = "Inventory Management System"

    def index(self, request, extra_context=None):
        from sales.models import Sale, ProductReturn, Payment, Refund
        from expenses.models import DailyExpense, ExpenseItem, SalaryTransaction, AccountTransfer, ProductOrder, Account
        from inventory.models import Product 
        
        extra_context = extra_context or {}

        # Date filtering logic - start from midnight 00:00:00 of the target day
        time_filter = request.GET.get('time_filter', 'last_7_days')
        today = now().replace(hour=0, minute=0, second=0, microsecond=0)

        if time_filter == 'today':
            start_date = today
        elif time_filter == 'last_5_days':
            start_date = today - timedelta(days=5)
        elif time_filter == 'last_10_days':
            start_date = today - timedelta(days=10)
        elif time_filter == 'last_month':
            start_date = today - timedelta(days=30) 
        elif time_filter == 'last_year':
            start_date = today - timedelta(days=365) 
        else:
            start_date = today - timedelta(days=7) # Default last_7_days

        # --- PERIOD PERFORMANCE (Summary Cards) ---
        sales_queryset = Sale.objects.filter(sold_date__gte=start_date).select_related('product')
        total_sales_volume = 0
        total_potential_profit = 0
        
        for sale in sales_queryset:
            total_sales_volume += sale.total_price
            purchase_rate = sale.purchase_price_at_that_time or (sale.product.purchase_rate or 0)
            total_potential_profit += sale.quantity_sold * (sale.selling_price_at_that_time - purchase_rate)

        # Returns in period
        returns_queryset = ProductReturn.objects.filter(return_date__gte=start_date).select_related('sale__product')
        return_revenue_loss = 0
        return_profit_loss = 0
        for ret in returns_queryset:
            return_revenue_loss += ret.quantity_returned * ret.sale.selling_price_at_that_time
            purchase_rate = ret.sale.purchase_price_at_that_time or (ret.sale.product.purchase_rate or 0)
            return_profit_loss += ret.quantity_returned * (ret.sale.selling_price_at_that_time - purchase_rate)

        net_sales_volume = total_sales_volume - return_revenue_loss
        gross_profit_from_sales = total_potential_profit - return_profit_loss

        # Pending Cheques (All-Time, not just period, because they are still pending)
        pending_cheques = Payment.objects.filter(payment_method='bank_check', status='PENDING')
        pending_cheques_amount = pending_cheques.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        pending_cheques_count = pending_cheques.count()
        
        # Cash Flow in Period
        cleared_payments = Payment.objects.filter(payment_date__gte=start_date, status='CLEARED').aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        refunds_out = Refund.objects.filter(refund_date__gte=start_date, status='CLEARED').aggregate(Sum('amount'))['amount__sum'] or 0
        return_refunds_out = ProductReturn.objects.filter(return_date__gte=start_date).aggregate(Sum('amount_refunded'))['amount_refunded__sum'] or 0
        
        total_cash_received = cleared_payments - refunds_out - return_refunds_out
        
        # Operating Expenses in Period (Daily expenses + Salaries)
        daily_expenses = ExpenseItem.objects.filter(daily_expense__date__gte=start_date.date()).aggregate(Sum('amount'))['amount__sum'] or 0
        salaries = SalaryTransaction.objects.filter(date__gte=start_date.date(), transaction_type__in=['PAYMENT', 'ADVANCE']).aggregate(Sum('amount'))['amount__sum'] or 0
        total_expense_amount = daily_expenses + salaries

        # True Net Accrual Profit (Gross Sales Profit - Operating Expenses)
        net_profit = gross_profit_from_sales - total_expense_amount

        # --- INDIVIDUAL ACCOUNT BALANCES (All-Time) ---
        accounts = Account.objects.all().order_by('account_type', 'name')
        account_details = []
        total_cash = 0
        total_bank = 0
        total_mobile = 0

        for acc in accounts:
            # Money In
            payments_in = Payment.objects.filter(account=acc, status='CLEARED').aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
            transfers_in = AccountTransfer.objects.filter(to_account=acc).aggregate(Sum('amount'))['amount__sum'] or 0
            
            # Money Out
            expenses_out = ExpenseItem.objects.filter(account=acc).aggregate(Sum('amount'))['amount__sum'] or 0
            salaries_out = SalaryTransaction.objects.filter(account=acc, transaction_type__in=['PAYMENT', 'ADVANCE']).aggregate(Sum('amount'))['amount__sum'] or 0
            orders_out = ProductOrder.objects.filter(account=acc).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
            returns_out = ProductReturn.objects.filter(account=acc).aggregate(Sum('amount_refunded'))['amount_refunded__sum'] or 0
            refunds_out_all = Refund.objects.filter(account=acc, status='CLEARED').aggregate(Sum('amount'))['amount__sum'] or 0
            transfers_out = AccountTransfer.objects.filter(from_account=acc).aggregate(Sum('amount'))['amount__sum'] or 0

            balance = acc.initial_balance + (payments_in + transfers_in) - (expenses_out + salaries_out + orders_out + returns_out + refunds_out_all + transfers_out)
            
            account_details.append({
                'name': acc.name,
                'type': acc.get_account_type_display(),
                'number': acc.account_number or '-',
                'balance': balance
            })

            if acc.account_type == 'cash': total_cash += balance
            elif acc.account_type == 'bank': total_bank += balance
            elif acc.account_type == 'mobile': total_mobile += balance

        extra_context.update({
            'time_filter': time_filter,
            'total_sales_amount': total_cash_received,
            'total_expense_amount': total_expense_amount,
            'pending_cheques_amount': pending_cheques_amount,
            'pending_cheques_count': pending_cheques_count,
            'products': Product.objects.all().order_by('name'),
            'cash_balance': total_cash,
            'bank_balance': total_bank,
            'mobile_bank_balance': total_mobile,
            'account_details': account_details,
        })

        if request.user.is_superuser or request.user.groups.filter(name='Admin').exists():
            extra_context.update({
                'total_profit_from_sales': gross_profit_from_sales,
                'net_profit': net_profit,
                'show_profit_data': True, 
            })
        else:
            extra_context.update({
                'show_profit_data': False, 
            })

        return super().index(request, extra_context)

custom_admin_site = CustomAdminSite(name='custom_admin')
