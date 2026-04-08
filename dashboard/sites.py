from django.contrib import admin
from unfold.sites import UnfoldAdminSite
from django.db.models import Sum
from datetime import timedelta
from django.utils.timezone import now

class CustomAdminSite(UnfoldAdminSite):
    site_header = "Company Dashboard"
    site_title = "Global Trade Admin"
    index_title = "Inventory Management System"

    def index(self, request, extra_context=None):
        from sales.models import Sale, ProductReturn, Payment, Refund
        from expenses.models import DailyExpense, ExpenseItem, SalaryTransaction, AccountTransfer, ProductOrder
        from inventory.models import Product 
        
        extra_context = extra_context or {}

        # Date filtering logic
        time_filter = request.GET.get('time_filter', 'last_7_days')
        today = now()
        start_date = today - timedelta(days=7) # Default

        if time_filter == 'today':
            start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_filter == 'last_5_days':
            start_date = today - timedelta(days=5)
        elif time_filter == 'last_10_days':
            start_date = today - timedelta(days=10)
        elif time_filter == 'last_month':
            start_date = today - timedelta(days=30) 
        elif time_filter == 'last_year':
            start_date = today - timedelta(days=365) 

        # 1. Sales Data - Volume and Initial Payments
        sales_queryset = Sale.objects.filter(sold_date__gte=start_date).select_related('product')
        total_sales_count = sales_queryset.count()
        
        total_sales_volume = 0
        direct_cleared_revenue = 0
        total_potential_profit = 0
        pending_condition_amount = 0
        
        for sale in sales_queryset:
            total_sales_volume += sale.total_price
            
            if sale.is_conditional:
                pending_condition_amount += sale.total_price
            elif sale.payment_method != 'bank_check':
                direct_cleared_revenue += sale.amount_paid
            
            purchase_rate = sale.product.purchase_rate or 0
            profit_per_unit = sale.selling_price_at_that_time - purchase_rate
            total_potential_profit += sale.quantity_sold * profit_per_unit

        # 2. Payments Data - Subsequent Cleared/Pending in the period
        payments_queryset = Payment.objects.filter(payment_date__gte=start_date)
        cleared_payments_amount = 0
        pending_payments_amount = 0
        
        for pay in payments_queryset:
            if pay.status == 'CLEARED':
                cleared_payments_amount += pay.amount_paid
            elif pay.status == 'PENDING':
                pending_payments_amount += pay.amount_paid

        # 3. Account for Returns and Refunds in the period
        returns_queryset = ProductReturn.objects.filter(return_date__gte=start_date).select_related('sale', 'sale__product')
        return_revenue_loss = 0
        return_profit_loss = 0
        direct_refunds_from_returns = 0
        
        for ret in returns_queryset:
            return_revenue_loss += ret.quantity_returned * ret.sale.selling_price_at_that_time
            purchase_rate = ret.sale.product.purchase_rate or 0
            profit_per_unit = ret.sale.selling_price_at_that_time - purchase_rate
            return_profit_loss += ret.quantity_returned * profit_per_unit
            direct_refunds_from_returns += ret.amount_refunded

        # Standalone Refunds
        standalone_refunds_cleared = Refund.objects.filter(refund_date__gte=start_date, status='CLEARED').aggregate(Sum('amount'))['amount__sum'] or 0

        # 4. Final Calculations (Cash-Flow based)
        total_sales_amount = direct_cleared_revenue + cleared_payments_amount - direct_refunds_from_returns - standalone_refunds_cleared
        pending_sales_amount = pending_payments_amount

        # Profit Calculation
        total_profit_from_sales = 0
        effective_volume = total_sales_volume - return_revenue_loss
        if effective_volume > 0:
            total_profit_from_sales = (total_potential_profit - return_profit_loss) * (total_sales_amount / effective_volume)
        total_profit_from_sales = max(0, total_profit_from_sales)

        # Expenses data
        total_daily_expense = ExpenseItem.objects.filter(
            daily_expense__date__gte=start_date
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        total_salary_paid = SalaryTransaction.objects.filter(
            date__gte=start_date,
            transaction_type__in=['PAYMENT', 'ADVANCE']
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        total_product_order_paid = ProductOrder.objects.filter(
            order_date__gte=start_date
        ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0

        total_expense_amount = total_daily_expense + total_salary_paid + total_product_order_paid
        net_profit = total_profit_from_sales - total_expense_amount

        # Product inventory
        products = Product.objects.all().order_by('name')

        # --- ALL-TIME BALANCES CALCULATION ---
        # 1. Cash Balance
        cash_in_sales = Sale.objects.filter(payment_method='cash', is_conditional=False).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        cash_in_payments = Payment.objects.filter(payment_method='cash', status='CLEARED').aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        cash_out_returns = ProductReturn.objects.filter(refund_method='cash').aggregate(Sum('amount_refunded'))['amount_refunded__sum'] or 0
        cash_out_refunds = Refund.objects.filter(refund_method='cash', status='CLEARED').aggregate(Sum('amount'))['amount__sum'] or 0
        cash_out_expenses = ExpenseItem.objects.aggregate(Sum('amount'))['amount__sum'] or 0
        cash_out_salaries = SalaryTransaction.objects.filter(transaction_type__in=['PAYMENT', 'ADVANCE']).aggregate(Sum('amount'))['amount__sum'] or 0
        cash_out_orders = ProductOrder.objects.filter(payment_method='cash').aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        
        cash_transfer_in_cash = AccountTransfer.objects.filter(to_account='cash').aggregate(Sum('amount'))['amount__sum'] or 0
        cash_transfer_out_cash = AccountTransfer.objects.filter(from_account='cash').aggregate(Sum('amount'))['amount__sum'] or 0

        cash_balance = (cash_in_sales + cash_in_payments + cash_transfer_in_cash) - (cash_out_returns + cash_out_refunds + cash_out_expenses + cash_out_salaries + cash_out_orders + cash_transfer_out_cash)

        # 2. Bank Balance
        bank_in_sales = Sale.objects.filter(payment_method='bank_transaction', is_conditional=False).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        bank_in_payments = Payment.objects.filter(payment_method__in=['bank_check', 'bank_transaction'], status='CLEARED').aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        bank_out_returns = ProductReturn.objects.filter(refund_method__in=['bank_check', 'bank_transaction']).aggregate(Sum('amount_refunded'))['amount_refunded__sum'] or 0
        bank_out_refunds = Refund.objects.filter(refund_method__in=['bank_check', 'bank_transaction'], status='CLEARED').aggregate(Sum('amount'))['amount__sum'] or 0
        bank_out_orders = ProductOrder.objects.filter(payment_method='bank').aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        
        bank_transfer_in = AccountTransfer.objects.filter(to_account='bank').aggregate(Sum('amount'))['amount__sum'] or 0
        bank_transfer_out = AccountTransfer.objects.filter(from_account='bank').aggregate(Sum('amount'))['amount__sum'] or 0

        bank_balance = (bank_in_sales + bank_in_payments + bank_transfer_in) - (bank_out_returns + bank_out_refunds + bank_out_orders + bank_transfer_out)

        # 3. Mobile Bank Balance
        mobile_in_sales = Sale.objects.filter(payment_method='mobile_banking', is_conditional=False).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        mobile_in_payments = Payment.objects.filter(payment_method='mobile_banking', status='CLEARED').aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        mobile_out_returns = ProductReturn.objects.filter(refund_method='mobile_banking').aggregate(Sum('amount_refunded'))['amount_refunded__sum'] or 0
        mobile_out_refunds = Refund.objects.filter(refund_method='mobile_banking', status='CLEARED').aggregate(Sum('amount'))['amount__sum'] or 0
        mobile_out_orders = ProductOrder.objects.filter(payment_method='mobile').aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        
        mobile_transfer_in = AccountTransfer.objects.filter(to_account='mobile').aggregate(Sum('amount'))['amount__sum'] or 0
        mobile_transfer_out = AccountTransfer.objects.filter(from_account='mobile').aggregate(Sum('amount'))['amount__sum'] or 0

        mobile_bank_balance = (mobile_in_sales + mobile_in_payments + mobile_transfer_in) - (mobile_out_returns + mobile_out_refunds + mobile_out_orders + mobile_transfer_out)

        # --- INDIVIDUAL BANK BREAKDOWN ---
        bank_balances = {}
        
        # Sales
        for entry in Sale.objects.filter(payment_method='bank_transaction', is_conditional=False).values('bank_name').annotate(total=Sum('amount_paid')):
            name = entry['bank_name'] or 'Unspecified'
            bank_balances[name] = bank_balances.get(name, 0) + entry['total']
            
        # Payments
        for entry in Payment.objects.filter(payment_method__in=['bank_check', 'bank_transaction'], status='CLEARED').values('bank_name').annotate(total=Sum('amount_paid')):
            name = entry['bank_name'] or 'Unspecified'
            bank_balances[name] = bank_balances.get(name, 0) + entry['total']
            
        # Account Transfers (In)
        for entry in AccountTransfer.objects.filter(to_account='bank').values('to_bank_name').annotate(total=Sum('amount')):
            name = entry['to_bank_name'] or 'Unspecified'
            bank_balances[name] = bank_balances.get(name, 0) + entry['total']
            
        # Account Transfers (Out)
        for entry in AccountTransfer.objects.filter(from_account='bank').values('from_bank_name').annotate(total=Sum('amount')):
            name = entry['from_bank_name'] or 'Unspecified'
            bank_balances[name] = bank_balances.get(name, 0) - entry['total']
            
        # Returns
        for entry in ProductReturn.objects.filter(refund_method__in=['bank_check', 'bank_transaction']).values('bank_name').annotate(total=Sum('amount_refunded')):
            name = entry['bank_name'] or 'Unspecified'
            bank_balances[name] = bank_balances.get(name, 0) - entry['total']
            
        # Refunds
        for entry in Refund.objects.filter(refund_method__in=['bank_check', 'bank_transaction'], status='CLEARED').values('bank_name').annotate(total=Sum('amount')):
            name = entry['bank_name'] or 'Unspecified'
            bank_balances[name] = bank_balances.get(name, 0) - entry['total']

        # Subtract orders which don't have bank name (put under Unspecified for balance)
        if bank_out_orders > 0:
            bank_balances['Unspecified'] = bank_balances.get('Unspecified', 0) - bank_out_orders

        extra_context.update({
            'time_filter': time_filter,
            'total_sales_count': total_sales_count,
            'total_sales_amount': total_sales_amount,
            'pending_sales_amount': pending_sales_amount,
            'pending_condition_amount': pending_condition_amount,
            'total_expense_amount': total_expense_amount,
            'products': products,
            'cash_balance': cash_balance,
            'bank_balance': bank_balance,
            'bank_balances_detail': bank_balances,
            'mobile_bank_balance': mobile_bank_balance,
        })
        if request.user.is_superuser or request.user.groups.filter(name='Admin').exists():
            extra_context.update({
                'total_profit_from_sales': total_profit_from_sales,
                'net_profit': net_profit,
                'show_profit_data': True, 
            })
        else:
            extra_context.update({
                'show_profit_data': False, 
            })

        return super().index(request, extra_context)

custom_admin_site = CustomAdminSite(name='custom_admin')
