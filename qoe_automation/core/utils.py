import pandas as pd
import pdfplumber
from datetime import datetime
from decimal import Decimal
from .models import QuickbookRecord, PayrollRecord, Adjustment

def process_quickbooks_file(file_path):

    try:
        df = pd.read_csv(file_path)
        gl_records = []
        
        for _, row in df.iterrows():
            gl_record = QuickbookRecord(
                date=pd.to_datetime(row['Date']).date(),
                account_number=str(row['Account Number']),
                account_name=row['Account Name'],
                description=row['Description'],
                debit=Decimal(str(row['Debit'])) if pd.notna(row['Debit']) else Decimal('0'),
                credit=Decimal(str(row['Credit'])) if pd.notna(row['Credit']) else Decimal('0'),
                balance=Decimal(str(row['Balance'])) if pd.notna(row['Balance']) else Decimal('0')
            )
            gl_records.append(gl_record)
        
        return gl_records
    except Exception as e:
        raise Exception(f"Error processing QuickBooks file: {str(e)}")

def process_payroll_file(file_path):

    try:
        df = pd.read_csv(file_path)
        payroll_records = []
        
        for _, row in df.iterrows():
            payroll_record = PayrollRecord(
                employee_name=row['Employee Name'],
                title=row['Title'],
                compensation=Decimal(str(row['Compensation'])),
                taxes=Decimal(str(row['Taxes'])),
                benefits=Decimal(str(row['Benefits'])),
                date=pd.to_datetime(row['Date']).date()
            )
            payroll_records.append(payroll_record)
        
        return payroll_records
    except Exception as e:
        raise Exception(f"Error processing payroll file: {str(e)}")

def extract_pdf_data(file_path):

    try:
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text()
        return text
    except Exception as e:
        raise Exception(f"Error extracting PDF data: {str(e)}")

def suggest_adjustments(gl_records, payroll_records):

    adjustments = []
    
    for record in gl_records:
        if record.debit > 10000:  
            adjustment = Adjustment(
                description=f"Potential one-time expense: {record.description}",
                adjustment_type='ADDBACK',
                amount=record.debit,
                date=record.date,
                rationale="Large one-time expense that may be non-recurring",
                source_reference=f"GL Account: {record.account_number}"
            )
            adjustments.append(adjustment)
    
    for record in payroll_records:
        if "owner" in record.title.lower() or "president" in record.title.lower():
            adjustment = Adjustment(
                description=f"Owner compensation: {record.employee_name}",
                adjustment_type='NORMALIZATION',
                amount=record.compensation,
                date=record.date,
                rationale="Owner compensation may need to be normalized",
                source_reference=f"Payroll: {record.employee_name}"
            )
            adjustments.append(adjustment)
    
    return adjustments

def generate_recast_pl(gl_records, adjustments, date):

    revenue = sum(r.credit for r in gl_records if "revenue" in r.account_name.lower())
    cogs = sum(r.debit for r in gl_records if "cost of goods" in r.account_name.lower())
    operating_expenses = sum(r.debit for r in gl_records if "expense" in r.account_name.lower())
    
    total_adjustments = sum(a.amount for a in adjustments)
    
    gross_profit = revenue - cogs
    ebitda = gross_profit - operating_expenses + total_adjustments
    
    return {
        'date': date,
        'revenue': revenue,
        'cogs': cogs,
        'gross_profit': gross_profit,
        'operating_expenses': operating_expenses,
        'ebitda': ebitda
    } 