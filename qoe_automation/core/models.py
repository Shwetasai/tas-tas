from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

class DataSource(models.Model):
    SOURCE_TYPES = (
        ('QB', 'QuickBooks'),
        ('PAYROLL', 'Payroll System'),
        ('SUPPLEMENTAL', 'Supplemental Notes'),
        ('STOC', 'STOC Accounting'),
        ('PL', 'Profit and Loss'),
    )
    
    PROCESSING_STATUS = (
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )
    
    name = models.CharField(max_length=100)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    file_path = models.FileField(upload_to='data_sources/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    processing_status = models.CharField(max_length=20, choices=PROCESSING_STATUS, default='PENDING')
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    processed_records_count = models.IntegerField(default=0)
    processed_adjustments_count = models.IntegerField(default=0)
    
    quickbook_records = models.ManyToManyField('QuickbookRecord', blank=True)
    payroll_records = models.ManyToManyField('PayrollRecord', blank=True)
    profit_loss_records = models.ManyToManyField('ProfitLossRecord', blank=True)
    supplemental_notes = models.ManyToManyField('SupplementalNote', blank=True)

    def __str__(self):
        return f"{self.name} ({self.source_type})"

    class Meta:
        indexes = [
            models.Index(fields=['source_type']),
            models.Index(fields=['processing_status']),
        ]

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
        ('OWNER_COMP', 'Owner Compensation'),
        ('ONE_TIME', 'One-time Expense'),
        ('NON_RECURRING', 'Non-recurring'),
    )
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('AI_SUGGESTED', 'AI Suggested'),
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
    
    is_ai_suggested = models.BooleanField(default=False)
    ai_confidence_score = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        null=True,
        blank=True
    )
    ai_suggestion_reason = models.TextField(blank=True, null=True)
    
    category = models.CharField(max_length=100, blank=True, null=True)
    subcategory = models.CharField(max_length=100, blank=True, null=True)
    impact_type = models.CharField(
        max_length=20,
        choices=(
            ('POSITIVE', 'Positive Impact'),
            ('NEGATIVE', 'Negative Impact'),
            ('NEUTRAL', 'Neutral Impact'),
        ),
        default='NEUTRAL'
    )
    
    validation_status = models.CharField(
        max_length=20,
        choices=(
            ('VALID', 'Valid'),
            ('INVALID', 'Invalid'),
            ('NEEDS_REVIEW', 'Needs Review'),
        ),
        default='NEEDS_REVIEW'
    )
    validation_notes = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['status']),
            models.Index(fields=['is_ai_suggested']),
            models.Index(fields=['validation_status']),
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
    
    export_format = models.CharField(
        max_length=20,
        choices=(
            ('EXCEL', 'Excel'),
            ('SHEETS', 'Google Sheets'),
            ('PDF', 'PDF'),
        ),
        default='EXCEL'
    )
    export_status = models.CharField(
        max_length=20,
        choices=(
            ('PENDING', 'Pending'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed'),
        ),
        default='PENDING'
    )
    export_file_path = models.CharField(max_length=255, blank=True, null=True)
    export_metadata = models.JSONField(blank=True, null=True)
    
    validation_status = models.CharField(
        max_length=20,
        choices=(
            ('VALID', 'Valid'),
            ('INVALID', 'Invalid'),
            ('NEEDS_REVIEW', 'Needs Review'),
        ),
        default='NEEDS_REVIEW'
    )
    validation_notes = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['export_status']),
            models.Index(fields=['validation_status']),
        ]

class ProfitLossRecord(models.Model):
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    date = models.DateField()
    revenue = models.DecimalField(max_digits=15, decimal_places=2)
    cogs = models.DecimalField(max_digits=15, decimal_places=2)
    gross_profit = models.DecimalField(max_digits=15, decimal_places=2)
    operating_expenses = models.DecimalField(max_digits=15, decimal_places=2)
    ebitda = models.DecimalField(max_digits=15, decimal_places=2)
    net_income = models.DecimalField(max_digits=15, decimal_places=2)

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

class StocAccountingData(models.Model):
    STATUS_CHOICES = (
        ('OK', 'Ok!'),
        ('ERROR', 'Error!'),
        ('N/A', 'Not Applicable'),
    )

    project_name = models.CharField(max_length=255)
    location_city = models.CharField(max_length=100, blank=True, null=True)
    location_state = models.CharField(max_length=100, blank=True, null=True)

    external_financial_statement = models.CharField(max_length=100, blank=True, null=True)
    calendar_year_fiscal_year = models.CharField(max_length=100, blank=True, null=True)
    stub_period = models.DateField(blank=True, null=True)
    financial_reporting_period_1 = models.DateField(blank=True, null=True)
    financial_reporting_period_2 = models.DateField(blank=True, null=True)

    qe_summary_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='N/A')
    recast_reported_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='N/A')
    recast_mgmt_adjusted_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='N/A')
    other_recast_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='N/A')
    lead_profit_and_loss_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='N/A')
    monthly_profit_and_loss_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='N/A')

    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"STOC Data for {self.project_name} ({self.financial_reporting_period_1})"

    class Meta:
        verbose_name = "STOC Accounting Data"
        verbose_name_plural = "STOC Accounting Data"

class PDFDocument(models.Model):
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    file_path = models.FileField(upload_to='pdf_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    parsed_content = models.JSONField(blank=True, null=True)
    parsing_status = models.CharField(
        max_length=20,
        choices=(
            ('PENDING', 'Pending'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed'),
        ),
        default='PENDING'
    )
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['parsing_status']),
        ]

class ExportTemplate(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    template_format = models.CharField(
        max_length=20,
        choices=(
            ('EXCEL', 'Excel'),
            ('SHEETS', 'Google Sheets'),
            ('PDF', 'PDF'),
        )
    )
    template_file = models.FileField(upload_to='export_templates/')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['template_format']),
            models.Index(fields=['is_active']),
        ]
