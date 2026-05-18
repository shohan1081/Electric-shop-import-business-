from django.db import models
from inventory.models import Product
from expenses.models import Account
from django.core.exceptions import ValidationError
from django.utils import timezone


class Customer(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, null=True)
    total_due = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            # Capture the initial due amount as opening balance
            self.opening_balance = self.total_due
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (Due: ৳{self.total_due})"

    def get_transaction_history(self):
        """
        Gathers all related transactions (Sales, Payments, Returns) into a single chronological list.
        """
        history = []
        
        # 0. Add Opening Balance (if any)
        if self.opening_balance != 0:
            history.append({
                'date': self.created_at,
                'type': 'OPENING BALANCE',
                'description': "Initial balance at creation",
                'debit': self.opening_balance if self.opening_balance > 0 else 0,
                'credit': abs(self.opening_balance) if self.opening_balance < 0 else 0,
                'note': "System migration / Initial Setup"
            })

        # 1. Add Sales
        for sale in self.sales.all():
            sale_type = 'SALE'
            if sale.is_conditional:
                sale_type = 'CONDITIONAL SALE'
            
            history.append({
                'date': sale.sold_date,
                'type': sale_type,
                'description': f"Sold: {sale.product.name} ({sale.quantity_sold} units)",
                'debit': sale.total_price,  # Customer owes this
                'credit': 0,
                'note': f"Unit Price: ৳{sale.selling_price_at_that_time} | Profit: ৳{sale.profit} {sale.condition_notes or ''}"
            })

        # 2. Add Payments
        for pay in self.payments.all():
            payment_type = 'PAYMENT'
            description = f"Customer Payment (Cheque No: {pay.cheque_number or 'N/A'})"
            
            if pay.payment_method == 'bank_check':
                payment_type = f"CHEQUE ({pay.get_status_display()})"
            
            if pay.sale:
                description = f"Payment for {pay.sale.product.name}"

            history.append({
                'date': pay.payment_date,
                'type': payment_type,
                'description': description,
                'debit': 0,
                'credit': pay.amount_paid if pay.status == 'CLEARED' else 0, # Only cleared cheques affect credit
                'note': f"Account: {pay.account.name if pay.account else 'N/A'} {pay.note or ''}"
            })

        # 3. Add Returns
        for ret in self.returns.all():
            return_value = ret.quantity_returned * ret.sale.selling_price_at_that_time
            history.append({
                'date': ret.return_date,
                'type': 'RETURN',
                'description': f"Returned: {ret.sale.product.name} ({ret.quantity_returned} units)",
                'debit': 0,
                'credit': return_value, # Return reduces due (acts like a credit)
                'note': ret.reason or ""
            })
            
            # If cash was actually given back, it's a separate debit to the customer
            if ret.amount_refunded > 0:
                history.append({
                    'date': ret.return_date,
                    'type': 'REFUND',
                    'description': f"Cash Refund for returned {ret.sale.product.name}",
                    'debit': ret.amount_refunded, # Giving money back increases their "due" (offsetting the return credit)
                    'credit': 0,
                    'note': f"Account: {ret.account.name if ret.account else 'N/A'}"
                })

        # 4. Add Standalone Refunds
        for ref in self.standalone_refunds.all():
            history.append({
                'date': ref.refund_date,
                'type': 'REFUND (Direct)',
                'description': f"Standalone Cash Refund",
                'debit': ref.amount if ref.status == 'CLEARED' else 0,
                'credit': 0,
                'note': f"Account: {ref.account.name if ref.account else 'N/A'} {ref.note or ''}"
            })

        # Sort by date (oldest first)
        history.sort(key=lambda x: x['date'], reverse=False)
        return history


class Sale(models.Model):
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('bank_check', 'Bank Check'),
        ('bank_transaction', 'Bank Transaction'),
        ('mobile_banking', 'Mobile Banking'),
    )

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='sales')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_sold = models.DecimalField(max_digits=10, decimal_places=3)
    purchase_price_at_that_time = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=0)
    selling_price_at_that_time = models.DecimalField(max_digits=12, decimal_places=2)
    transport_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True)
    total_price = models.DecimalField(max_digits=14, decimal_places=2)
    profit = models.DecimalField(max_digits=14, decimal_places=2, default=0, editable=False)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    due_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    # New account management
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='sales', null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    
    # Conditional Sale fields
    is_conditional = models.BooleanField(default=False, verbose_name="Conditional Sale (Payment on Delivery)")
    condition_notes = models.CharField(max_length=255, blank=True, null=True, help_text="e.g., Courier details, delivery conditions")
    
    sold_date = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.product.unit_of_measure == 'unit' and self.quantity_sold is not None and self.quantity_sold % 1 != 0:
            raise ValidationError({'quantity_sold': f"Quantity sold for '{self.product.name}' (Unit based) must be a whole number."})

        if self.quantity_sold > self.product.quantity:
            raise ValidationError(f"Not enough stock available for {self.product.name}. Available: {self.product.quantity} {self.product.unit_of_measure}.")
        
        if self.is_conditional:
            if self.amount_paid > 0:
                raise ValidationError({'amount_paid': "For conditional sales (payment on delivery), the initial amount paid must be 0."})
        
        if self.amount_paid > 0 and not self.account and self.payment_method != 'bank_check':
            raise ValidationError({'account': "Please select the account where the payment was received."})

    def save(self, *args, **kwargs):
        # Calculate totals
        from decimal import Decimal, ROUND_HALF_UP
        fee = self.transport_fee or Decimal('0.00')
        self.total_price = ((self.quantity_sold * self.selling_price_at_that_time) + fee).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # We always add the FULL total_price to the debt.
        # The automated Payment object created below will handle the reduction of amount_paid.
        actual_due_impact = self.total_price

        self.due_amount = (self.total_price - self.amount_paid).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        self.full_clean()
        
        is_new = not self.pk
        customer = self.customer

        if is_new:
            # Atomic update to avoid stale data
            from django.db.models import F
            Customer.objects.filter(pk=customer.pk).update(total_due=F('total_due') + self.total_price)
            # Handle stock
            self.product.quantity -= self.quantity_sold
            self.product.save()
        else:
            # Atomic update for changes
            from django.db.models import F
            original = Sale.objects.get(pk=self.pk)
            diff = self.total_price - original.total_price
            if diff != 0:
                Customer.objects.filter(pk=customer.pk).update(total_due=F('total_due') + diff)
            
        customer.refresh_from_db()
        super().save(*args, **kwargs)

        # AUTOMATION: Create/Update Payment Record
        if self.amount_paid > 0:
            status = 'PENDING' if self.payment_method == 'bank_check' else 'CLEARED'
            
            payment = Payment.objects.filter(sale=self).first()
            
            if not payment:
                payment = Payment(
                    sale=self,
                    customer=self.customer,
                    amount_paid=self.amount_paid,
                    account=self.account,
                    payment_method=self.payment_method,
                    status=status
                )
            else:
                payment.amount_paid = self.amount_paid
                payment.account = self.account
                payment.payment_method = self.payment_method
            
            payment.save()

    def delete(self, *args, **kwargs):
        # Revert stock
        self.product.quantity += self.quantity_sold
        self.product.save()
        
        # Subtract the full total_price from customer due.
        # The linked Payment (if any) will be deleted via CASCADE and its
        # delete() method will handle reverting the amount_paid.
        customer = self.customer
        customer.total_due -= self.total_price
        customer.save()
        
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.customer.name} - {self.product.name}"


class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('CLEARED', 'Cleared'),
        ('BOUNCED', 'Bounced'),
    )

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payments')
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='sale_payments', null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    
    # New account management
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='payments', null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=Sale.PAYMENT_METHODS, default='cash')
    
    # Cheque specific fields
    status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    cheque_number = models.CharField(max_length=50, blank=True, null=True)
    cheque_date = models.DateField(blank=True, null=True)
    clearance_date = models.DateTimeField(blank=True, null=True)

    note = models.CharField(max_length=255, blank=True, null=True)

    def clean(self):
        # Cheque specific validations
        if self.payment_method == 'bank_check':
            if not self.cheque_date:
                raise ValidationError({'cheque_date': "Cheque date is required for cheque payments."})
        else: # Not a bank_check payment
            # Force CLEARED status and set clearance date for all non-cheque payments
            self.status = 'CLEARED'
            if not self.clearance_date:
                self.clearance_date = timezone.now()

            # Ensure cheque-specific fields are empty
            if self.cheque_number or self.cheque_date:
                raise ValidationError("Cheque-specific fields (number/date) should only be set for cheque payments.")

        if self.amount_paid > 0 and not self.account:
            # Allow account to be null ONLY for pending cheques
            if not (self.payment_method == 'bank_check' and self.status == 'PENDING'):
                raise ValidationError({'account': "Please select the account where the payment was received."})

    def save(self, *args, **kwargs):
        self.full_clean() # Call full_clean to run model validation before saving

        if self.payment_method == 'bank_check':
            # Handle cheque status changes
            if self.pk: # Existing payment
                original_payment = Payment.objects.get(pk=self.pk)
                if original_payment.status == 'PENDING' and self.status == 'CLEARED':
                    # Cheque cleared: decrease customer due and set clearance date
                    customer = self.customer
                    customer.total_due -= self.amount_paid
                    customer.save()
                    self.clearance_date = timezone.now()
                elif original_payment.status == 'CLEARED' and self.status == 'PENDING':
                    # Reverting cleared cheque to pending: increase customer due
                    customer = self.customer
                    customer.total_due += self.amount_paid
                    customer.save()
                    self.clearance_date = None
                elif original_payment.status == 'CLEARED' and self.status == 'BOUNCED':
                    # Cheque bounced after being cleared: increase customer due
                    customer = self.customer
                    customer.total_due += self.amount_paid
                    customer.save()
                    self.clearance_date = None
                elif original_payment.status == 'PENDING' and self.status == 'BOUNCED':
                    # Cheque bounced from pending: no balance change, just status update
                    self.clearance_date = None
            else: # New cheque payment
                # Do not update customer.total_due on initial creation for cheques
                pass
        else: # Not a bank_check payment
            # Ensure status is CLEARED and clearance_date is set for non-cheque payments
            if not self.pk: # New non-cheque payment
                self.status = 'CLEARED'
                self.clearance_date = timezone.now()
                from django.db.models import F
                Customer.objects.filter(pk=self.customer.pk).update(total_due=F('total_due') - self.amount_paid)
                self.customer.refresh_from_db()
            else: # Existing non-cheque payment
                # If updating a non-cheque payment, adjust due by difference
                original_payment = Payment.objects.get(pk=self.pk)
                if original_payment.amount_paid != self.amount_paid:
                    from django.db.models import F
                    diff = original_payment.amount_paid - self.amount_paid
                    Customer.objects.filter(pk=self.customer.pk).update(total_due=F('total_due') + diff)
                    self.customer.refresh_from_db()
                # Ensure status remains CLEARED and clearance_date is set if it's not already
                self.status = 'CLEARED'
                if not self.clearance_date:
                    self.clearance_date = timezone.now()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Only cleared payments affect the balance
        if self.status == 'CLEARED':
            customer = self.customer
            customer.total_due += self.amount_paid
            customer.save()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Payment of ৳{self.amount_paid} by {self.customer.name} ({self.get_status_display()})"


class ProductReturn(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='returns', null=True, blank=True)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='returns')
    quantity_returned = models.DecimalField(max_digits=10, decimal_places=3)
    return_date = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, null=True)
    
    # Refund fields
    amount_refunded = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='product_returns', null=True, blank=True)
    refund_method = models.CharField(max_length=20, choices=Sale.PAYMENT_METHODS, default='cash')

    def clean(self):
        if self.sale.product.unit_of_measure == 'unit' and self.quantity_returned is not None and self.quantity_returned % 1 != 0:
            raise ValidationError({'quantity_returned': f"Quantity returned for '{self.sale.product.name}' (Unit based) must be a whole number."})

        already_returned = ProductReturn.objects.filter(sale=self.sale).exclude(pk=self.pk).aggregate(models.Sum('quantity_returned'))['quantity_returned__sum'] or 0
        if self.quantity_returned + already_returned > self.sale.quantity_sold:
            raise ValidationError(f"Cannot return more than purchased. Total purchased: {self.sale.quantity_sold}, Already returned: {already_returned}")
        
        # Validate refund fields
        if self.amount_refunded > 0 and not self.account:
            raise ValidationError({'account': "Please select the account from which the refund was paid."})

    def save(self, *args, **kwargs):
        self.full_clean() # Call full_clean to run model validation before saving
        from decimal import Decimal, ROUND_HALF_UP
        if not self.pk:
            # 0. Set Customer automatically
            self.customer = self.sale.customer

            # 1. Update Product Stock
            product = self.sale.product
            product.quantity += self.quantity_returned
            product.save()

            # 2. Update Customer Due
            # Net impact is the return value MINUS what we gave back as cash
            return_value = (self.quantity_returned * self.sale.selling_price_at_that_time).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            net_return_impact = return_value - self.amount_refunded
            
            customer = self.sale.customer
            customer.total_due = (customer.total_due - net_return_impact).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            customer.save()
            
            # 3. Update the specific Sale's due amount
            self.sale.due_amount = (self.sale.due_amount - net_return_impact).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            self.sale.save()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from decimal import Decimal, ROUND_HALF_UP
        # 1. Revert Product Stock
        product = self.sale.product
        product.quantity -= self.quantity_returned
        product.save()

        # 2. Revert Customer Due
        return_value = (self.quantity_returned * self.sale.selling_price_at_that_time).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        net_return_impact = return_value - self.amount_refunded
        
        customer = self.customer
        customer.total_due = (customer.total_due + net_return_impact).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        customer.save()
        
        # 3. Revert Sale's due amount
        self.sale.due_amount = (self.sale.due_amount + net_return_impact).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.sale.save()

        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Return for {self.sale.product.name} ({self.quantity_returned} units)"

class Refund(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='standalone_refunds')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    refund_date = models.DateTimeField(auto_now_add=True)
    
    # Refund details
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='standalone_refunds', null=True, blank=True)
    refund_method = models.CharField(max_length=20, choices=Sale.PAYMENT_METHODS, default='cash')
    
    # Cheque specific fields (if company gives refund via cheque)
    status = models.CharField(max_length=10, choices=Payment.PAYMENT_STATUS_CHOICES, default='CLEARED')
    cheque_number = models.CharField(max_length=50, blank=True, null=True)
    cheque_date = models.DateField(blank=True, null=True)
    clearance_date = models.DateTimeField(blank=True, null=True)
    
    note = models.CharField(max_length=255, blank=True, null=True)

    def clean(self):
        # Force CLEARED status and set clearance date for all non-cheque refunds
        if self.refund_method != 'bank_check':
            self.status = 'CLEARED'
            if not self.clearance_date:
                self.clearance_date = timezone.now()
            if self.cheque_number or self.cheque_date:
                raise ValidationError("Cheque-specific fields should only be set for cheque refunds.")
        else:
            if not self.cheque_date:
                raise ValidationError({'cheque_date': "Cheque date is required for cheque refunds."})

        if self.amount > 0 and not self.account:
            raise ValidationError({'account': "Please select the account from which the refund was paid."})

    def save(self, *args, **kwargs):
        self.full_clean()
        from decimal import Decimal, ROUND_HALF_UP
        if not self.pk:
            # New refund
            if self.status == 'CLEARED':
                customer = self.customer
                customer.total_due = (customer.total_due + self.amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                customer.save()
        else:
            # Existing refund update
            original = Refund.objects.get(pk=self.pk)
            # Only cleared refunds affect the balance
            if original.status != 'CLEARED' and self.status == 'CLEARED':
                customer = self.customer
                customer.total_due = (customer.total_due + self.amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                customer.save()
            elif original.status == 'CLEARED' and self.status != 'CLEARED':
                customer = self.customer
                customer.total_due = (customer.total_due - original.amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                customer.save()
            elif original.status == 'CLEARED' and self.status == 'CLEARED' and original.amount != self.amount:
                diff = self.amount - original.amount
                customer = self.customer
                customer.total_due = (customer.total_due + diff).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                customer.save()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from decimal import Decimal, ROUND_HALF_UP
        if self.status == 'CLEARED':
            customer = self.customer
            customer.total_due = (customer.total_due - self.amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            customer.save()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Refund of ৳{self.amount} to {self.customer.name}"
