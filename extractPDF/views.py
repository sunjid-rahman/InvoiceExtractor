from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from components.helper.extract_data import ExtractData


# Create your views here.


class ExtractPDF(APIView):
    def post(self, request):
        if 'file' in request.FILES:
            try:
                invoice_pdf_path = request.FILES['file']
                extract_data = ExtractData(invoice_pdf_path)
                invoice_info = extract_data.extract_information_from_invoice()
                return Response(data=invoice_info, status=status.HTTP_200_OK)
            except Exception as e:
                print(e)
                return Response("Error while processing file", status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response("File not found", status=status.HTTP_404_NOT_FOUND)
