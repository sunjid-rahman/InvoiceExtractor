import PyPDF2
import json
import numpy as np
import tempfile
import re
import tabula
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from camelot import read_pdf
import pandas as pd
from invoice2data import extract_data

# Create your views here.


class ExtractPDF(APIView):
    @staticmethod
    def extract_text_from_pdf(file):
        reader = PyPDF2.PdfReader(file)
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

    @staticmethod
    def extract_table_from_pdf(pdf_path):
        tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
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

    @staticmethod
    def extract_table_using_camelot(pdf_path):
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            # Save the uploaded PDF to a temporary file
            for chunk in pdf_path.chunks():
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

    @staticmethod
    def preprocess_text(text):
        # Example preprocessing steps: removing line breaks and extra spaces
        text = text.replace('\n', ' ').replace('\r', '')
        text = re.sub(' +', ' ', text)
        return text

    def extract_line_items(self, text):
        # Example regular expressions for line item patterns
        item_pattern = r'(?P<item>.+?)\s+(?P<quantity>\d+)\s+(?P<unit_price>\d+(\.\d+)?)\s+(?P<total>\d+(\.\d+)?)'
        line_items = re.findall(item_pattern, text, re.IGNORECASE)
        return line_items

    # Main function
    def extract_information_from_invoice(self, pdf_path):
        # Step 1: Preprocessing
        extracted_text = self.extract_text_from_pdf(pdf_path)
        invoice_number = self.extract_invoice_number(extracted_text)
        invoice_date = self.extract_invoice_date(extracted_text)
        total_amount = self.extract_total_amount(extracted_text)
        # ordered_items = self.extract_ordered_items(extracted_text)
        # table_data = self.extract_table_from_pdf(pdf_path)
        table = self.extract_table_using_camelot(pdf_path)
        self.extract_line_items(extracted_text)
        invoice_info = {
            "invoice_number": str(invoice_number),
            "invoice_date": str(invoice_date),
            "total_amount": str(total_amount),
            "items": table
        }
        return invoice_info

    def post(self, request):
        if 'file' in request.FILES:
            try:
                invoice_pdf_path = request.FILES['file']
                invoice_info = self.extract_information_from_invoice(invoice_pdf_path)
                return Response(data=invoice_info, status=status.HTTP_200_OK)
            except Exception as e:
                return Response("Error while processing file", status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response("File not found", status=status.HTTP_404_NOT_FOUND)
