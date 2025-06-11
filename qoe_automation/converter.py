import pandas as pd
import sys

def convert_xlsx_to_csv(xlsx_file_path, csv_file_path):
    """
    Converts an Excel (.xlsx) file to a CSV (.csv) file.
    """
    try:
        df = pd.read_excel(xlsx_file_path)
        df.to_csv(csv_file_path, index=False)
        print(f"Successfully converted '{xlsx_file_path}' to '{csv_file_path}'")
    except Exception as e:
        print(f"Error converting file: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python converter.py <input_xlsx_file_path> <output_csv_file_path>")
    else:
        input_xlsx = sys.argv[1]
        output_csv = sys.argv[2]
        convert_xlsx_to_csv(input_xlsx, output_csv) 