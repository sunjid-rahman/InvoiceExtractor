from django.urls import path
from .views import ExtractPDF

urlpatterns = [
    path('extract-pdf', ExtractPDF.as_view(), name='extractPDF'),
]