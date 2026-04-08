from django.db import models
from django.utils import timezone
from inventory.models import Product

class DailyExpense(models.Model):
    date = models.DateField(unique=True)
    
    @property
    def total_amount(self):
        return self.items.aggregate(models.Sum('amount'))['amount__sum'] or 0

    def __str__(self):
        return f"Expenses for {self.date}"

class ExpenseItem(models.Model):
    daily_expense = models.ForeignKey(DailyExpense, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.description}: {self.amount}"

class Employee(models.Model):
    name = models.CharField(max_length=200)
    designation = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, unique=True)
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0, help_text="Amount company owes to the employee")
    joining_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} (Balance: ৳{self.current_balance})"

class SalaryTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('ACCRUAL', 'Salary Accrual (Add to Balance)'),
        ('PAYMENT', 'Salary Payment (Cash Out)'),
        ('ADVANCE', 'Advance Payment (Cash Out)'),
        ('BONUS', 'Bonus (Add to Balance)'),
    )
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    note = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            # New transaction: Update employee balance
            if self.transaction_type in ['ACCRUAL', 'BONUS']:
                # Company owes more to employee
                self.employee.current_balance += self.amount
            elif self.transaction_type in ['PAYMENT', 'ADVANCE']:
                # Company paid the employee, reducing the debt
                self.employee.current_balance -= self.amount
            self.employee.save()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Revert employee balance
        if self.transaction_type in ['ACCRUAL', 'BONUS']:
            self.employee.current_balance -= self.amount
        elif self.transaction_type in ['PAYMENT', 'ADVANCE']:
            self.employee.current_balance += self.amount
        self.employee.save()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.employee.name}: ৳{self.amount}"

class AccountTransfer(models.Model):
    ACCOUNT_CHOICES = (
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('mobile', 'Mobile Banking'),
    )

    MOBILE_BANKING_TYPES = (
        ('bkash', 'bKash'),
        ('nagad', 'Nagad'),
        ('rocket', 'Rocket'),
    )

    from_account = models.CharField(max_length=10, choices=ACCOUNT_CHOICES)
    from_bank_name = models.CharField(max_length=100, blank=True, null=True, help_text="Required if From Account is Bank")
    from_mobile_type = models.CharField(max_length=10, choices=MOBILE_BANKING_TYPES, blank=True, null=True, help_text="Required if From Account is Mobile Banking")
    
    to_account = models.CharField(max_length=10, choices=ACCOUNT_CHOICES)
    to_bank_name = models.CharField(max_length=100, blank=True, null=True, help_text="Required if To Account is Bank")
    to_mobile_type = models.CharField(max_length=10, choices=MOBILE_BANKING_TYPES, blank=True, null=True, help_text="Required if To Account is Mobile Banking")
    
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    date = models.DateTimeField(default=timezone.now)
    note = models.CharField(max_length=255, blank=True, null=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.from_account == self.to_account:
            # If same account type, they must be different banks/mobile types
            if self.from_account == 'bank':
                if self.from_bank_name == self.to_bank_name:
                    raise ValidationError("Source and destination banks cannot be the same.")
            elif self.from_account == 'mobile':
                if self.from_mobile_type == self.to_mobile_type:
                    raise ValidationError("Source and destination mobile banking types cannot be the same.")
            else:
                raise ValidationError("Source and destination accounts cannot be the same.")
        
        if self.from_account == 'bank' and not self.from_bank_name:
            raise ValidationError({'from_bank_name': "Bank name is required for bank source."})
        if self.to_account == 'bank' and not self.to_bank_name:
            raise ValidationError({'to_bank_name': "Bank name is required for bank destination."})
            
        if self.from_account == 'mobile' and not self.from_mobile_type:
            raise ValidationError({'from_mobile_type': "Mobile banking type is required for mobile source."})
        if self.to_account == 'mobile' and not self.to_mobile_type:
            raise ValidationError({'to_mobile_type': "Mobile banking type is required for mobile destination."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Transfer ৳{self.amount} from {self.get_from_account_display()} to {self.get_to_account_display()}"

class ProductOrder(models.Model):
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('mobile', 'Mobile Banking'),
    )

    MOBILE_BANKING_TYPES = (
        ('bkash', 'bKash'),
        ('nagad', 'Nagad'),
        ('rocket', 'Rocket'),
    )

    supplier_name = models.CharField(max_length=200)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='orders')
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=14, decimal_places=2, editable=False)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    due_amount = models.DecimalField(max_digits=14, decimal_places=2, editable=False)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    bank_name = models.CharField(max_length=100, blank=True, null=True, help_text="Required if Payment Method is Bank")
    mobile_banking_type = models.CharField(max_length=10, choices=MOBILE_BANKING_TYPES, blank=True, null=True)
    
    order_date = models.DateTimeField(default=timezone.now)
    note = models.TextField(blank=True, null=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.amount_paid > 0:
            if self.payment_method == 'bank' and not self.bank_name:
                raise ValidationError({'bank_name': "Bank name is required for bank payments."})
            if self.payment_method == 'mobile' and not self.mobile_banking_type:
                raise ValidationError({'mobile_banking_type': "Mobile banking type is required for mobile payments."})

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        self.due_amount = self.total_price - self.amount_paid
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order from {self.supplier_name} for {self.product.name}"
