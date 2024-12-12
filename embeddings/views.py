import json
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from .tasks import process_document
from .models import Document, TextEmbedding, Collection, ChatSession, ChatMessage
from .forms import DocumentUploadForm, CollectionForm, SearchForm, SignUpForm
from .utils import get_embedding, generate_gpt_response

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('index')
        
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('index')
    else:
        form = SignUpForm()
    return render(request, 'embeddings/signup.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, 'Logged in successfully!')
            # Redirect to 'next' parameter if it exists
            next_url = request.GET.get('next', 'index')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
            
    return render(request, 'embeddings/login.html', {
        'next': request.GET.get('next', '')
    })

def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('login')

@login_required
def index(request):
    return redirect('collections_list')

@login_required
def collections_list(request):
    collections = Collection.objects.filter(user=request.user).order_by('-updated_at')
    
    if request.method == 'POST':
        form = CollectionForm(request.POST)
        if form.is_valid():
            collection = form.save(commit=False)
            collection.user = request.user
            collection.save()
            messages.success(request, 'Collection created successfully')
            return redirect('collections_list')
    else:
        form = CollectionForm()
    
    return render(request, 'embeddings/collections.html', {
        'collections': collections,
        'form': form
    })

@login_required
def collection_detail(request, collection_id):
    collection = get_object_or_404(Collection, id=collection_id, user=request.user)
    documents = collection.documents.all().order_by('-created_at')
    
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist('files')
            
            for file in files:
                # Save file to media directory
                file_path = default_storage.save(
                    os.path.join('documents', file.name),
                    ContentFile(file.read())
                )
                
                # Create document record
                document = Document.objects.create(
                    filename=file.name,
                    collection=collection,
                    status='pending'
                )
                
                # Start async processing
                with open(default_storage.path(file_path), 'rb') as f:
                    process_document.delay(
                        document_id=str(document.id),
                        file_content=f.read(),
                        filename=file.name
                    )
            
            messages.success(request, f'{len(files)} document(s) uploaded successfully')
            return redirect('collection_detail', collection_id=collection_id)
    else:
        form = DocumentUploadForm(initial={'collection': collection})
        # Filter collection choices to only show user's collections
        form.fields['collection'].queryset = Collection.objects.filter(user=request.user)
    
    return render(request, 'embeddings/collection_detail.html', {
        'collection': collection,
        'documents': documents,
        'form': form
    })

@login_required
def delete_collection(request, collection_id):
    collection = get_object_or_404(Collection, id=collection_id, user=request.user)
    if request.method == 'POST':
        collection.delete()
        messages.success(request, 'Collection deleted successfully')
    return redirect('collections_list')

@login_required
def delete_document(request, document_id):
    document = get_object_or_404(Document, id=document_id, collection__user=request.user)
    collection_id = document.collection.id
    
    if request.method == 'POST':
        # Delete the associated file if it exists
        if document.filename:
            file_path = os.path.join('documents', document.filename)
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
        
        # Delete the document and its embeddings
        document.delete()
        messages.success(request, 'Document deleted successfully')
    
    return redirect('collection_detail', collection_id=collection_id)

@login_required
def download_document(request, document_id):
    document = get_object_or_404(Document, id=document_id, collection__user=request.user)
    file_path = os.path.join('documents', document.filename)
    
    if default_storage.exists(file_path):
        file = default_storage.open(file_path, 'rb')
        response = FileResponse(file)
        response['Content-Disposition'] = f'attachment; filename="{document.filename}"'
        return response
    else:
        messages.error(request, 'File not found')
        return redirect('search')

@login_required
def search(request):
    # Get requested chat session or active session
    session_id = request.GET.get('session') or request.session.get('active_chat_session')
    chat_session = None
    
    if session_id:
        try:
            chat_session = ChatSession.objects.get(id=session_id, user=request.user)
            request.session['active_chat_session'] = str(chat_session.id)
        except ChatSession.DoesNotExist:
            session_id = None
    
    if not session_id:
        chat_session = ChatSession.objects.create(user=request.user)
        request.session['active_chat_session'] = str(chat_session.id)
    
    # Get all user's chat sessions
    chat_sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')
    
    # Get chat messages for current session
    chat_messages = chat_session.messages.all()
    
    if request.method == 'POST':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                action = data.get('action')
                
                if action == 'new_chat':
                    # Create new chat session
                    chat_session = ChatSession.objects.create(user=request.user)
                    request.session['active_chat_session'] = str(chat_session.id)
                    return JsonResponse({
                        'status': 'success',
                        'session_id': str(chat_session.id),
                        'redirect_url': f'/search/?session={chat_session.id}'
                    })
                
                if action == 'delete_chat':
                    chat_id = data.get('chat_id')
                    if not chat_id:
                        return JsonResponse({'error': 'Chat ID is required'}, status=400)
                    
                    # Get the chat to delete
                    chat_to_delete = get_object_or_404(ChatSession, id=chat_id, user=request.user)
                    
                    # If deleting active chat, we'll need to redirect to another chat
                    is_active = str(chat_to_delete.id) == session_id
                    
                    # Delete the chat
                    chat_to_delete.delete()
                    
                    if is_active:
                        # Find another chat to redirect to
                        next_chat = ChatSession.objects.filter(user=request.user).order_by('-updated_at').first()
                        if next_chat:
                            request.session['active_chat_session'] = str(next_chat.id)
                            return JsonResponse({
                                'status': 'success',
                                'redirect_url': f'/search/?session={next_chat.id}'
                            })
                        else:
                            # No more chats, create a new one
                            new_chat = ChatSession.objects.create(user=request.user)
                            request.session['active_chat_session'] = str(new_chat.id)
                            return JsonResponse({
                                'status': 'success',
                                'redirect_url': f'/search/?session={new_chat.id}'
                            })
                    
                    return JsonResponse({'status': 'success'})
                
                if action == 'set_collection':
                    collection_id = data.get('collection_id')
                    if collection_id:
                        collection = get_object_or_404(Collection, id=collection_id, user=request.user)
                        chat_session.collection = collection
                        chat_session.save()
                    else:
                        chat_session.collection = None
                        chat_session.save()
                    return JsonResponse({'status': 'success'})
                
                # Handle chat message
                query = data.get('query', '')
                if not query:
                    return JsonResponse({'error': 'Query is required'}, status=400)
                
                # Save user message
                ChatMessage.objects.create(
                    session=chat_session,
                    role='user',
                    content=query
                )
                
                # Update session timestamp
                chat_session.save()  # This will update the updated_at field
                
                # Generate embedding for the query
                query_embedding = get_embedding(query)
                if query_embedding is None:
                    return JsonResponse({'error': 'Error generating query embedding'}, status=500)
                
                # Get similar texts
                results = TextEmbedding.find_similar(query_embedding, limit=5, user=request.user)
                if chat_session.collection:
                    results = [r for r in results if r['document'].collection_id == chat_session.collection.id]
                
                # Build chat history for GPT
                chat_history = []
                for msg in chat_messages:
                    chat_history.append({
                        'role': msg.role,
                        'content': msg.content
                    })
                
                # Generate GPT response with sources
                if results:
                    gpt_response = generate_gpt_response(query, results, chat_history)
                    
                    # Extract unique sources from results
                    seen_files = set()
                    unique_sources = []
                    for r in results:
                        if r['document'].filename not in seen_files:
                            seen_files.add(r['document'].filename)
                            unique_sources.append({
                                'document_id': str(r['document'].id),
                                'filename': r['document'].filename,
                                'similarity': r['similarity']
                            })
                    
                    # Save assistant message with sources
                    assistant_message = ChatMessage.objects.create(
                        session=chat_session,
                        role='assistant',
                        content=gpt_response,
                        sources=unique_sources
                    )
                    
                    return JsonResponse({
                        'message': {
                            'id': str(assistant_message.id),
                            'content': gpt_response,
                            'sources': unique_sources,
                            'created_at': assistant_message.created_at.isoformat()
                        }
                    })
                else:
                    return JsonResponse({'error': 'No relevant documents found'}, status=404)
            
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
        else:
            return JsonResponse({'error': 'Invalid content type'}, status=400)
    
    # Get user's collections for the dropdown
    collections = Collection.objects.filter(user=request.user)
    
    return render(request, 'embeddings/search.html', {
        'collections': collections,
        'chat_session': chat_session,
        'chat_sessions': chat_sessions,
        'chat_messages': chat_messages
    })

@login_required
def document_status(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    return JsonResponse({
        'status': document.status,
        'progress': document.progress,
        'error_message': document.error_message
    })
