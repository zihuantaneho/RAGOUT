import io
from PyPDF2 import PdfReader
from docx import Document

def extract_text_from_pdf(file):
    """Extract text from PDF file."""
    pdf_reader = PdfReader(file)
    text = []
    for page in pdf_reader.pages:
        text.append(page.extract_text())
    return '\n\n'.join(text)

def extract_text_from_docx(file):
    """Extract text from DOCX file."""
    doc = Document(file)
    text = []
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text.append(paragraph.text)
    return '\n\n'.join(text)

def extract_text_from_txt(file):
    """Extract text from TXT file."""
    return file.read().decode('utf-8')

def process_file(file):
    """Process file based on its extension and return text content."""
    filename = file.name.lower()
    
    try:
        if filename.endswith('.pdf'):
            return extract_text_from_pdf(file)
        elif filename.endswith('.docx'):
            return extract_text_from_docx(file)
        elif filename.endswith('.txt'):
            return extract_text_from_txt(file)
        else:
            raise ValueError("Unsupported file type")
    except Exception as e:
        raise ValueError(f"Error processing file: {str(e)}") 