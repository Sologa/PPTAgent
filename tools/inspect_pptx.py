
import sys
from pptx import Presentation

if len(sys.argv) != 2:
    print("Usage: python inspect_pptx.py <path_to_pptx>")
    sys.exit(1)

pptx_path = sys.argv[1]
try:
    prs = Presentation(pptx_path)
    slide_count = len(prs.slides)
    print(f"The PPTX file '{pptx_path}' has {slide_count} slides according to python-pptx.")
except Exception as e:
    print(f"Error reading PPTX file: {e}")
