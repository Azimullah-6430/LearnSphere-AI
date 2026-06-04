import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import os

def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF file using OCR
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        Extracted text from PDF
    """
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=300)
        
        full_text = ""
        for image in images:
            # Extract text using Tesseract
            text = pytesseract.image_to_string(image)
            full_text += text + "\n"
        
        return full_text
    
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"

def extract_text_from_image(image_path):
    """
    Extract text from image file using OCR
    
    Args:
        image_path: Path to image file
    
    Returns:
        Extracted text from image
    """
    try:
        # Open image
        image = Image.open(image_path)
        
        # Extract text using Tesseract
        text = pytesseract.image_to_string(image)
        
        return text
    
    except Exception as e:
        return f"Error extracting text from image: {str(e)}"

def preprocess_image(image_path):
    """
    Preprocess image for better OCR accuracy
    
    Args:
        image_path: Path to image file
    
    Returns:
        Preprocessed image
    """
    try:
        import cv2
        import numpy as np
        
        # Read image
        img = cv2.imread(image_path)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(thresh, h=10)
        
        # Apply dilation and erosion
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        processed = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel)
        
        return processed
    
    except Exception as e:
        return None
