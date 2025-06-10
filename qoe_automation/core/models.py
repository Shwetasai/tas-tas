from django.db import models
from django.contrib.auth.models import User

class DataSource(models.Model):
    SOURCE_TYPES = (
        ('QB', 'QuickBooks'),
        ('PAYROLL', 'Payroll System'),
        ('SUPPLEMENTAL', 'Supplemental Notes'),
    )
    
    name = models.CharField(max_length=100)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    file_path = models.FileField(upload_to='data_sources/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.source_type})"

class QuickbookRecord(models.Model):
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    date = models.DateField()
    account_number = models.CharField(max_length=50)
    account_name = models.CharField(max_length=200)
    description = models.TextField()
    debit = models.DecimalField(max_digits=15, decimal_places=2)
    credit = models.DecimalField(max_digits=15, decimal_places=2)
    balance = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['account_number']),
        ]

class PayrollRecord(models.Model):
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    employee_name = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    compensation = models.DecimalField(max_digits=15, decimal_places=2)
    taxes = models.DecimalField(max_digits=15, decimal_places=2)
    benefits = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField()

    class Meta:
        indexes = [
            models.Index(fields=['employee_name']),
            models.Index(fields=['date']),
        ]

class Adjustment(models.Model):
    ADJUSTMENT_TYPES = (
        ('ADDBACK', 'Addback'),
        ('NORMALIZATION', 'Normalization'),
        ('DISCRETIONARY', 'Discretionary'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )

    description = models.TextField()
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    rationale = models.TextField()
    source_reference = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['status']),
        ]

class RecastPL(models.Model):
    date = models.DateField()
    revenue = models.DecimalField(max_digits=15, decimal_places=2)
    cogs = models.DecimalField(max_digits=15, decimal_places=2)
    gross_profit = models.DecimalField(max_digits=15, decimal_places=2)
    operating_expenses = models.DecimalField(max_digits=15, decimal_places=2)
    ebitda = models.DecimalField(max_digits=15, decimal_places=2)
    adjustments = models.ManyToManyField(Adjustment)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['date']),
        ]

class SupplementalNote(models.Model):
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    note_type = models.CharField(max_length=100)
    description = models.TextField()
    impact_amount = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
