from django.db import models
from django.utils import timezone
from inventory.models import Product

class Account(models.Model):
    ACCOUNT_TYPES = (
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('mobile', 'Mobile Banking'),
    )

    name = models.CharField(max_length=100, unique=True)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    initial_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"

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
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='expenses', null=True)

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
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='salary_payments', null=True, blank=True)
    date = models.DateField(default=timezone.now)
    note = models.CharField(max_length=255, blank=True, null=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.transaction_type in ['PAYMENT', 'ADVANCE'] and not self.account:
            raise ValidationError({'account': "Account is required for salary payments or advances."})

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
    from_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='transfers_out')
    to_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='transfers_in')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    date = models.DateTimeField(default=timezone.now)
    note = models.CharField(max_length=255, blank=True, null=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.from_account == self.to_account:
            raise ValidationError("Source and destination accounts cannot be the same.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Transfer ৳{self.amount} from {self.from_account.name} to {self.to_account.name}"

class ProductOrder(models.Model):
    supplier_name = models.CharField(max_length=200)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='orders')
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=14, decimal_places=2, editable=False)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    due_amount = models.DecimalField(max_digits=14, decimal_places=2, editable=False)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='product_orders', null=True, blank=True)
    
    order_date = models.DateTimeField(default=timezone.now)
    note = models.TextField(blank=True, null=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.amount_paid > 0 and not self.account:
            raise ValidationError({'account': "Account is required if an amount is paid."})

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        self.due_amount = self.total_price - self.amount_paid
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order from {self.supplier_name} for {self.product.name}"
