import pandas as pd
import tabula
import PyPDF2
import numpy as np
import tempfile
import re
from camelot import read_pdf


class ExtractData:
    def __init__(self, pdf_path):
        self.PDF_PATH = pdf_path

    def extract_text_from_pdf(self):
        reader = PyPDF2.PdfReader(self.PDF_PATH)
        num_pages = len(reader.pages)
        text = ''
        for i in range(num_pages):
            page = reader.pages[i]
            text += page.extract_text()
        return text

    # Extract Invoice Number
    @staticmethod
    def extract_invoice_number(text):
        # Define patterns or keywords for invoice number extraction
        patterns = ['Invoice No.', 'Order No.', 'Invoice Number', 'Order #']
        for pattern in patterns:
            match = re.search(r'{}(\s*:\s*|\s+)(\w+)'.format(pattern), text, re.IGNORECASE)
            if match:
                return match.group(2)
        return None

    # Extract Invoice Date
    @staticmethod
    def extract_invoice_date(text):
        # Define patterns or keywords for invoice date extraction
        patterns = ['Invoice Date', 'Date of Issue', 'Billing Date', 'Order Date', 'Date']
        for pattern in patterns:
            match = re.search(r'{}(\s*(.*))'.format(pattern), text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    # Extract Total Amount
    @staticmethod
    def extract_total_amount(text):
        # Define patterns or keywords for total amount extraction
        patterns = ['Total', 'TOTAL', 'Amount Due', 'Total Payable', 'Grand Total']
        for pattern in patterns:
            match = re.search(r'{}(\s*(.*))'.format(pattern), text, re.IGNORECASE)
            if match:
                line = match.group(2).replace(',', '')
                pattern = r'(\d+\.\d+)'
                match = re.search(pattern, line)
                if match:
                    result = match.group(1)
                    return result
        return None

    # Extract List of Ordered Items

    def extract_table_from_pdf(self):
        tables = tabula.read_pdf(self.PDF_PATH, pages='all', multiple_tables=True)
        table_label = [table.columns.tolist() for table in tables]
        table_header = None  # Initialize the result variable

        for sublist in table_label:
            lowercase_sublist = [item.lower() for item in sublist]  # Convert sublist elements to lowercase
            if 'item' in lowercase_sublist or 'product' in lowercase_sublist or 'product name' in lowercase_sublist or 'item name' in lowercase_sublist:
                table_header = sublist
                break
        table_data = [table.values.tolist() for table in tables]
        clean_table = []
        for data in table_data[1]:
            # clean_list = [x for x in data if str(x).lower() != 'nan']
            # dic = {}
            # if len(clean_list) >= 2:
            #     dic[clean_list[0]] = clean_list[1]
            #     clean_table.append(dic)
            # else:
            #     clean_table.append(clean_list)
            if len(data) == len(table_header):
                my_dict = {k: v for k, v in zip(table_header, data)}
                clean_table.append(my_dict)
        return clean_table

    def extract_table_using_camelot(self):
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            # Save the uploaded PDF to a temporary file
            for chunk in self.PDF_PATH.chunks():
                temp_file.write(chunk)

            temp_file_path = temp_file.name
        tables = read_pdf(temp_file_path, pages="all", flavor='stream')
        allin = []
        last_table_index = tables.n - 1  # last table grab kortese

        last_table = tables[last_table_index]

        table_data = last_table.df
        table_data = table_data.iloc[3:]  # Extra info remove kortese

        allin.append(table_data)
        df = pd.concat(allin)
        df = df.reset_index(drop=True)
        df.columns = df.iloc[0]
        df = df[1:]
        df = df.reset_index(drop=True)
        df = df.replace('', np.nan)
        df = df.dropna(how='any')
        dict_list = []
        for index, row in df.iterrows():
            dict_list.append(row.to_dict())
        return dict_list

    # Main function
    def extract_information_from_invoice(self):
        # Step 1: Preprocessing
        extracted_text = self.extract_text_from_pdf()
        invoice_number = self.extract_invoice_number(extracted_text)
        invoice_date = self.extract_invoice_date(extracted_text)
        total_amount = self.extract_total_amount(extracted_text)
        # ordered_items = self.extract_ordered_items(extracted_text)
        # table_data = self.extract_table_from_pdf(pdf_path)
        table = self.extract_table_using_camelot()
        item_details = []
        for dict in table:
            new_dict = {(
                            "name" if key.lower() == "items" or key.lower() == "item" or key.lower() == "product" or key.lower() == "products" or key.lower() == "item name" or key.lower() == "product name" else key): value
                        for key, value in dict.items()}
            new_dict = {("unit_price" if "unit" in key.lower() else key): value for key, value in new_dict.items()}
            new_dict = {("quantity" if key.lower() == "quantity" or key.lower() == "qty" else key): value for key, value
                        in new_dict.items()}
            new_dict = {("amount" if "amount" in key.lower() else key): value for key, value in new_dict.items()}
            new_dict = {("discount" if "discount" in key.lower() else key): value for key, value in new_dict.items()}
            item_details.append(new_dict)
        invoice_info = {
            "invoice_info": {
                "date": str(invoice_date),
                "number": str(invoice_number)
            },
            "total_amount": str(total_amount),
            "item_details": item_details,
            "note": "",
            "customer_info": {}

        }
        return invoice_info