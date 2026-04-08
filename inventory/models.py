from django.db import models
from django.core.exceptions import ValidationError

class Product(models.Model):
    UNIT_CHOICES = [
        ('unit', 'Unit'),
        ('meter', 'Meter'),
    ]

    name = models.CharField(max_length=200)
    import_number = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    unit_of_measure = models.CharField(max_length=10, choices=UNIT_CHOICES, default='unit')
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    purchase_rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    listing_date = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.unit_of_measure == 'unit' and self.quantity is not None and self.quantity % 1 != 0:
            raise ValidationError({'quantity': "Quantity for 'Unit' based products must be a whole number."})
        super().clean()

    def __str__(self):
        parts = [self.name]
        if self.brand:
            parts.append(f"[{self.brand}]")
        if self.model:
            parts.append(f"({self.model})")
        
        parts.append(f"- Stock: {self.quantity} {self.unit_of_measure}")
        
        return " ".join(parts)

class ProductValuation(Product):
    class Meta:
        proxy = True
        verbose_name = "Inventory Valuation Report"
        verbose_name_plural = "Inventory Valuation Reports"
