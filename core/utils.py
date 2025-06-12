import pandas as pd
import pdfplumber
from datetime import datetime
from decimal import Decimal
import re
import io
import os
import openpyxl
from .models import QuickbookRecord, PayrollRecord, Adjustment, StocAccountingData

def process_quickbooks_file(file_path):

    try:
        df = pd.read_csv(file_path, skiprows=4)
        gl_records = []
        
        df.rename(columns={
            df.columns[1]: 'Distribution account',
            df.columns[2]: 'Transaction date',
            df.columns[3]: 'Transaction type',
            df.columns[4]: 'Num',
            df.columns[5]: 'Name',
            df.columns[6]: 'Memo/Description',
            df.columns[7]: 'Split account',
            df.columns[8]: 'Amount',
            df.columns[9]: 'Balance'
        }, inplace=True)
        
        for _, row in df.iterrows():
            if pd.isna(row['Transaction date']) or \
               'Beginning Balance' in str(row['Distribution account']) or \
               'Total for' in str(row['Distribution account']) or \
               pd.isna(row['Amount']):
                continue

            amount_str = str(row['Amount']).strip()
            amount_str = amount_str.replace('$', '').replace(',', '')
            if amount_str.startswith('(') and amount_str.endswith(')'):
                amount_str = '-' + amount_str[1:-1]
            
            if not amount_str:
                amount_str = '0'

            amount = Decimal(amount_str)
            debit = Decimal('0')
            credit = Decimal('0')

            if amount < 0:
                debit = abs(amount)
            else:
                credit = amount

            try:
                record_date = pd.to_datetime(row['Transaction date']).date()
            except ValueError:
                continue

            account_full_name = str(row['Distribution account'])
            account_number_match = re.match(r'(\d+)\\s(.*)', account_full_name)

            account_number = ''
            account_name = account_full_name

            if account_number_match:
                account_number = account_number_match.group(1)
                account_name = account_number_match.group(2)
            else:
                account_number = ''
                account_name = account_full_name

            gl_record = QuickbookRecord(
                date=record_date,
                account_number=account_number,
                account_name=account_name,
                description=row['Memo/Description'] if pd.notna(row['Memo/Description']) else (row['Name'] if pd.notna(row['Name']) else row['Transaction type']),
                debit=debit,
                credit=credit,
                balance=Decimal(str(row['Balance']).strip().replace('$', '').replace(',', '').replace('(', '-').replace(')', '') if pd.notna(row['Balance']) else '0')
            )
            gl_records.append(gl_record)
        
        return gl_records
    except Exception as e:
        raise Exception(f"Error processing QuickBooks file: {str(e)}")

def process_payroll_file(file_path):
    try:
        with open(file_path, 'rb') as f: 
            raw_lines = f.readlines()

        decoded_lines = [line.decode('latin-1', errors='ignore') for line in raw_lines]

        header_index = -1
        for i, line in enumerate(decoded_lines):
            stripped_line = line.strip()
            if stripped_line.startswith("Employee Name") and "TIN" in stripped_line and "Pay Frequency" in stripped_line and "Department" in stripped_line:
                header_index = i
                print(f"DEBUG: Found header at line index: {header_index}")
                raw_header_line = decoded_lines[header_index].strip()
                print(f"DEBUG: Raw header line content: '{raw_header_line}'") 

        if header_index == -1:
            raise ValueError("Payroll header not found in the file. Please ensure 'Employee Name', 'TIN', and 'Pay Frequency' columns are present.")

        data_only_lines = decoded_lines[header_index + 1:] 
        data_string = "".join(data_only_lines)
        data_io = io.StringIO(data_string)

        df = pd.read_csv(data_io, encoding='latin-1', sep=',', quotechar='"', header=None)

        cleaned_header_columns = [col.strip() for col in raw_header_line.split(',')]
        
        seen_columns = {}
        unique_cleaned_header_columns = []
        for col in cleaned_header_columns:
            original_col = col
            count = seen_columns.get(original_col, 0)
            if count > 0:
                col = f'{original_col}.{count}'
            while col in unique_cleaned_header_columns: 
                count += 1
                col = f'{original_col}.{count}'
            unique_cleaned_header_columns.append(col)
            seen_columns[original_col] = count + 1
        
        df.columns = unique_cleaned_header_columns

        print(f"DEBUG: DataFrame columns after initial read (and manual assignment): {df.columns.tolist()}") 
        print(f"DEBUG: Initial DataFrame shape (after manual assignment): {df.shape}") 
        print(f"""DEBUG: First 5 rows of DataFrame (after manual assignment):
{df.head().to_string()}""") 
        payroll_records = []

        df['Employee Name'] = df['Employee Name'].astype(str)

        print(f"DEBUG_FILTER: df.info() after Employee Name astype(str):")
        df.info(verbose=True, show_counts=True)

        print(f"DEBUG_FILTER: Result of ~df['Employee Name'].str.contains('Total', case=False, na=False) (head):\n{(~df['Employee Name'].str.contains('Total', case=False, na=False)).head().to_string()}")
        df_filtered = df.loc[df['Employee Name'].notna() & ~df['Employee Name'].str.contains('Total', case=False, na=False)].copy()

        print(f"DEBUG: Filtered DataFrame shape: {df_filtered.shape}") 
        print(f"DEBUG: First 5 Employee Names in filtered DataFrame: {df_filtered['Employee Name'].head().tolist()}") 

        earning_amount_cols = ['Amount'] + [f'Amount.{i}' for i in range(1, 19)]
        earning_amount_cols = [col for col in earning_amount_cols if col in df_filtered.columns]

        benefit_cols = [
            '401k Employee Contribution',
            'Pre-tax Medical Health Insurance Deduc',
            'AFLAC pre-tax',
        ]
        benefit_cols = [col for col in benefit_cols if col in df_filtered.columns]
        
        for _, row in df_filtered.iterrows():
            employee_name = row.get('Employee Name')
            if pd.isna(employee_name):
                print(f"DEBUG: Skipping row due to missing Employee Name at index {_}")
                continue

            record_date = extract_date_from_payment_columns(row)
            if record_date is None:
                continue

            compensation = Decimal('0')
            for col in earning_amount_cols:
                if pd.notna(row[col]): 
                    print(f"DEBUG_COMP: Processing Column: {col}, Raw Value: '{row[col]}'")
                    try:
                        cleaned_val = str(row[col]).replace('$', '').replace(',', '').strip()
                        print(f"DEBUG_COMP: Cleaned Value: '{cleaned_val}'") 
                        if cleaned_val:
                            compensation += Decimal(cleaned_val)
                        print(f"DEBUG_COMP: Current Compensation Total: {compensation}")
                    except (ValueError, TypeError, AttributeError) as e:
                        print(f"DEBUG_COMP: Error converting {col} ('{row[col]}'): {e}") 
                        pass
            taxes_str = str(row['Total Taxes']).replace('$', '').replace(',', '').strip() if pd.notna(row['Total Taxes']) else '0'
            taxes = Decimal(taxes_str) if taxes_str else Decimal('0')

            benefits = Decimal('0')
            for col in benefit_cols:
                if pd.notna(row[col]): 
                    print(f"DEBUG_BENEFITS: Processing Column: {col}, Raw Value: '{row[col]}'") 
                    try:
                        cleaned_val = str(row[col]).replace('$', '').replace(',', '').strip()
                        print(f"DEBUG_BENEFITS: Cleaned Value: '{cleaned_val}'")
                        if cleaned_val:
                            benefits += Decimal(cleaned_val)
                        print(f"DEBUG_BENEFITS: Current Benefits Total: {benefits}") 
                    except (ValueError, TypeError, AttributeError) as e:
                        print(f"DEBUG_BENEFITS: Error converting {col} ('{row[col]}'): {e}") 
                        pass 

            payroll_record = PayrollRecord(
                employee_name=employee_name,
                title="Employee",
                compensation=compensation,
                taxes=taxes,
                benefits=benefits,
                date=record_date
            )
            payroll_records.append(payroll_record)
        
        print(f"DEBUG: Successfully processed {len(payroll_records)} payroll records.") 
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

    print(f"DEBUG_PL: Entered generate_recast_pl for date: {date}")
    print(f"DEBUG_PL: Number of QuickBooks records received: {len(gl_records)}")
    print(f"DEBUG_PL: Number of adjustments received (should be APPROVED): {len(adjustments)}")

    revenue = sum(r.credit for r in gl_records if 
                  ("deposit" in r.description.lower() or 
                   "fees" in r.description.lower() or 
                   "revenue" in r.account_name.lower()) 
                 )

    cogs = sum(r.debit for r in gl_records if 
               ("dental supplies" in r.description.lower() or 
                "cost of goods" in r.description.lower())
              )

    operating_expenses = sum(r.debit for r in gl_records if 
                             ("expense" in r.description.lower() or 
                              "payroll service" in r.description.lower() or
                              "rent" in r.description.lower() or
                              "legal & professional fees" in r.description.lower() or
                              "repairs & maintenance" in r.description.lower() or
                              "insurance" in r.description.lower() or
                              "janitorial services" in r.description.lower() or
                              "auto expense" in r.description.lower() or
                              "employee benefits" in r.description.lower()
                             )
                            )
    
    total_adjustments = sum(a.amount for a in adjustments)

    print(f"DEBUG_PL: Calculated Revenue: {revenue}")
    print(f"DEBUG_PL: Calculated COGS: {cogs}")
    print(f"DEBUG_PL: Calculated Operating Expenses: {operating_expenses}")
    print(f"DEBUG_PL: Calculated Total Adjustments: {total_adjustments}")
    
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

def extract_date_from_payment_columns(row):
    record_date = None
    print(f"\nDEBUG_DATE: Checking dates for employee: {row.get('Employee Name', 'N/A')}")
    print(f"DEBUG_DATE_COL_CHECK: Columns in current row object: {list(row.index)}")

    for i in range(1, 28): 
        date_col_regex = rf'payment\s* {re.escape(str(i))}\s* check date' 
        print(f"DEBUG_DATE_COL_CHECK: Trying to match regex: {date_col_regex}")
        found_date_col = None

        for col_name in row.index:
            if re.search(date_col_regex, col_name.lower()):
                found_date_col = col_name
                break

        if found_date_col and pd.notna(row[found_date_col]):
            raw_date_val = row[found_date_col]
            print(f"DEBUG_DATE: Column: {found_date_col}")
            print(f"DEBUG_DATE: Raw value type: {type(raw_date_val)}")
            print(f"DEBUG_DATE: Raw value: '{raw_date_val}'")
            try:
                record_date = pd.to_datetime(raw_date_val, errors='coerce')
                if pd.notna(record_date):
                    print(f"DEBUG_DATE: Successfully parsed date with pandas: {record_date.date()}")
                    break
                else:
                    print(f"DEBUG_DATE: Pandas failed to parse date: '{raw_date_val}'")

                for fmt in ["%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%m-%d-%Y", "%m-%d-%y"]:
                    try:
                        record_date = datetime.strptime(str(raw_date_val).strip(), fmt).date()
                        print(f"DEBUG_DATE: Successfully parsed date with format {fmt}: {record_date}")
                        break
                    except ValueError:
                        print(f"DEBUG_DATE: Failed to parse '{raw_date_val}' with format {fmt}")
                if record_date:
                    break

            except Exception as e:
                print(f"DEBUG_DATE: Error parsing date '{raw_date_val}': {e}")
        else:
            print(f"DEBUG_DATE_COL_CHECK: Column matching regex '{date_col_regex}' not found or is NaN in row for {row.get('Employee Name', 'N/A')}.")

    if not record_date:
        print(f"DEBUG_DATE: No valid date found for employee '{row.get('Employee Name', 'N/A')}'. Skipping record.")
    return record_date 

def process_stoc_file(file_path, uploaded_by_user):
    try:
        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension == '.csv':
            df = pd.read_csv(file_path, 
                           header=None,
                           encoding='latin-1',
                           skip_blank_lines=False,
                           on_bad_lines='warn')
            
            if df.shape[1] < 4:
                for i in range(df.shape[1], 4):
                    df[i] = None

            def get_cell_value_pandas(dataframe, row_idx, col_idx):
                try:
                    if row_idx < dataframe.shape[0] and col_idx < dataframe.shape[1]:
                        return dataframe.iloc[row_idx, col_idx]
                    return None
                except Exception as e:
                    return None

            def find_row_index(dataframe, search_text):
                for idx, row in dataframe.iterrows():
                    if any(str(cell).strip() == search_text for cell in row if pd.notna(cell)):
                        return idx
                return None

            project_name_row = find_row_index(df, "Project Name")
            if project_name_row is None:
                project_name_row = 13
            project_name = get_cell_value_pandas(df, project_name_row, 1)
            location_city = get_cell_value_pandas(df, project_name_row + 1, 1)
            location_state = get_cell_value_pandas(df, project_name_row + 2, 1)

            financial_section_row = find_row_index(df, "Financial / reporting period:")
            if financial_section_row is None:
                financial_section_row = 18
            external_financial_statement = get_cell_value_pandas(df, financial_section_row + 1, 1)
            calendar_year_fiscal_year = get_cell_value_pandas(df, financial_section_row + 3, 1)
            stub_period_raw = get_cell_value_pandas(df, financial_section_row + 4, 1)
            
            financial_reporting_period_2_raw = get_cell_value_pandas(df, financial_section_row + 5, 1)
            financial_reporting_period_1_raw = get_cell_value_pandas(df, financial_section_row + 6, 1)

            status_section_row = find_row_index(df, "Tab checks:")
            if status_section_row is None:
                status_section_row = 25

            def get_status_value(row_idx):
                status_name = get_cell_value_pandas(df, row_idx, 1)
                if status_name and isinstance(status_name, str):
                    if 'Error' in status_name or 'Error!' in status_name:
                        return 'ERROR'
                    elif 'Ok!' in status_name:
                        return 'OK'
                return 'N/A'

            qe_summary_status = get_status_value(status_section_row + 1)
            recast_reported_status = get_status_value(status_section_row + 2)
            recast_mgmt_adjusted_status = get_status_value(status_section_row + 3)
            other_recast_status = get_status_value(status_section_row + 4)
            lead_profit_and_loss_status = get_status_value(status_section_row + 5)
            monthly_profit_and_loss_status = get_status_value(status_section_row + 6)

        else:
            raise ValueError(f"Unsupported file type: {file_extension}. Only .csv is supported for STOC files.")

        def parse_date_safely(date_val):
            if date_val is None or (isinstance(date_val, float) and pd.isna(date_val)):
                return None
            try:
                if isinstance(date_val, str) and ',' in date_val:
                    date_val = date_val.replace(',', ', ')
                return pd.to_datetime(str(date_val)).date()
            except (ValueError, TypeError):
                return None

        stub_period = parse_date_safely(stub_period_raw)
        financial_reporting_period_1 = parse_date_safely(financial_reporting_period_1_raw)
        financial_reporting_period_2 = parse_date_safely(financial_reporting_period_2_raw)

        stoc_data = StocAccountingData.objects.create(
            project_name=str(project_name) if project_name is not None else 'Unknown Project',
            location_city=str(location_city) if location_city is not None else None,
            location_state=str(location_state) if location_state is not None else None,
            external_financial_statement=str(external_financial_statement) if external_financial_statement is not None else None,
            calendar_year_fiscal_year=str(calendar_year_fiscal_year) if calendar_year_fiscal_year is not None else None,
            stub_period=stub_period,
            financial_reporting_period_1=financial_reporting_period_1,
            financial_reporting_period_2=financial_reporting_period_2,
            qe_summary_status=qe_summary_status,
            recast_reported_status=recast_reported_status,
            recast_mgmt_adjusted_status=recast_mgmt_adjusted_status,
            other_recast_status=other_recast_status,
            lead_profit_and_loss_status=lead_profit_and_loss_status,
            monthly_profit_and_loss_status=monthly_profit_and_loss_status,
            uploaded_by=uploaded_by_user
        )

        return 1
    except Exception as e:
        raise Exception(f"Error processing STOC file: {str(e)}") 