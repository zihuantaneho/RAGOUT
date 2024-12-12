import io
from PyPDF2 import PdfReader
from docx import Document
import openai

# Set OpenAI API key
openai.api_key = "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"

def get_embedding(text):
    """Get embedding from OpenAI API."""
    try:
        response = openai.Embedding.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response['data'][0]['embedding']
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return None

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

def process_file(file, filename=None):
    """Process file based on its extension and return text content."""
    if hasattr(file, 'name'):
        filename = file.name.lower()
    elif filename:
        filename = filename.lower()
    else:
        raise ValueError("Filename is required for processing")
    
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

def generate_gpt_response(query, results, chat_history):
    """Generate a conversational response using GPT based on search results and chat history"""
    try:
        # Build the context from search results
        context = "\n\n".join([
            f"From {result['document'].filename}:\n{result['text']}"
            for result in results
        ])
        
        # Build the chat history string
        history = ""
        if chat_history:
            history = "\n".join([
                f"{'Human' if msg['role'] == 'user' else 'Rag'}: {msg['content']}"
                for msg in chat_history[:-1]  # Exclude the current query
            ])
            history = f"\nPrevious conversation:\n{history}\n"
        
        # Create the prompt
        system_prompt = """You are Rag, a friendly AI who helps users understand their documents. Your style is:
- Very concise and to the point, like texting with a friend
- Use short sentences and natural language
- Break up long responses into smaller messages
- Avoid formal language or lengthy explanations
- Get straight to the point
- Use casual, friendly tone
- If citing sources, be brief about it
- Keep responses under 3 sentences when possible"""

        user_prompt = f"""Based on these document excerpts:

{context}

Question: {query}

Give me a quick, chat-style response. Be concise and friendly, like we're texting."""

        # Get response from OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": history if history else "Let's start fresh!"},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error generating GPT response: {e}")
        return "Oops, something went wrong. Mind trying that again?" 