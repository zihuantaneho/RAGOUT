from django.shortcuts import render, redirect
from django.contrib import messages
from openai import OpenAI
from .forms import TextFileUploadForm, SearchForm
from .models import TextEmbedding, Document
from .utils import process_file
from .tasks import process_document
import base64

# Initialize OpenAI client
client = OpenAI(
    api_key='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'
)

def get_embedding(text):
    try:
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        return None

def get_chatgpt_response(query, context):
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided context. Keep your answers concise and relevant to the query."},
            {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}\n\nPlease answer the question based on the context provided."}
        ]
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=150
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error getting ChatGPT response: {str(e)}")
        return "Sorry, I couldn't generate a response at this time."

def upload_file(request):
    if request.method == 'POST':
        form = TextFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            
            try:
                # Create document record
                document = Document.objects.create(
                    filename=file.name,
                    status='pending'
                )
                
                # Read and encode file content
                file_content = base64.b64encode(file.read()).decode('utf-8')
                
                # Start background processing
                process_document.delay(
                    document_id=str(document.id),
                    file_content=file_content,
                    filename=file.name
                )
                
                # Redirect to status page
                return redirect('document_status', document_id=document.id)
                
            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
    else:
        form = TextFileUploadForm()
    
    # Get all documents for display
    documents = Document.objects.all().order_by('-created_at')
    
    return render(request, 'embeddings/upload.html', {
        'form': form,
        'documents': documents
    })

def document_status(request, document_id):
    document = Document.objects.get(id=document_id)
    return render(request, 'embeddings/status.html', {
        'document': document
    })

def search(request):
    form = SearchForm()
    results = []
    answer = ""
    
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            query = form.cleaned_data['query']
            
            # Get embedding for the query
            query_embedding = get_embedding(query)
            if query_embedding:
                # Find similar texts
                similar_texts = TextEmbedding.find_similar(query_embedding, limit=3)
                
                if similar_texts:
                    # Prepare context from similar texts
                    context = "\n\n".join([text['text'] for text in similar_texts])
                    
                    # Get ChatGPT response
                    answer = get_chatgpt_response(query, context)
                    results = similar_texts
    
    return render(request, 'embeddings/search.html', {
        'form': form,
        'results': results,
        'answer': answer
    })
