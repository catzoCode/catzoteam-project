# test_ocr.py
import pytesseract
from PIL import Image

try:
    # Test if Python can find Tesseract
    version = pytesseract.get_tesseract_version()
    print(f"✅ SUCCESS! Tesseract version: {version}")
    print("✅ Python can communicate with Tesseract!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("Solution: Add this to your code:")
    print('pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"')