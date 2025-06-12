# QoE Automation Backend

A Django-based backend system for automating Quality of Earnings (QoE) preparation by processing accounting and payroll data to generate recast P&L statements with management adjustments.

## Features

- Process QuickBooks data (GL details, P&L, Chart of Accounts)
- Handle payroll data from various providers (Gusto, ADP, Paychex)
- Automatically identify potential adjustments
- Generate recast P&L statements
- Track adjustment rationales and sources
- RESTful API for data access and manipulation

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

4. Create a superuser:
```bash
python manage.py createsuperuser
```

5. Run the development server:
```bash
python manage.py runserver
```

## API Endpoints

- `/api/data-sources/` - Manage data source files
- `/api/gl-details/` - Access GL detail records
- `/api/payroll-records/` - Access payroll records
- `/api/adjustments/` - Manage adjustments
- `/api/recast-pl/` - Access recast P&L statements
- `/api/supplemental-notes/` - Manage supplemental notes

## Data Processing

The system supports the following file formats:
- QuickBooks exports (CSV)
- Payroll exports (CSV)
- PDF documents (bank statements, tax documents)

## Security

- All endpoints require authentication
- File uploads are restricted to specific file types
- Maximum file size is set to 10MB

## Development

To contribute to the project:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 