
import sys
from pdf2image import pdfinfo_from_path

if len(sys.argv) != 2:
    print("Usage: python inspect_pdf.py <path_to_pdf>")
    sys.exit(1)

pdf_path = sys.argv[1]
try:
    info = pdfinfo_from_path(pdf_path)
    page_count = info['Pages']
    print(f"The PDF file '{pdf_path}' has {page_count} pages.")
except Exception as e:
    print(f"Error reading PDF file: {e}")
