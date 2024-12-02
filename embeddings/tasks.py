from celery import shared_task
from .models import Document, TextEmbedding
from .utils import process_file
from django.core.files.base import ContentFile
from openai import OpenAI
import io
import base64
from time import sleep
from celery import group
import numpy as np
from datetime import datetime, timedelta

# Initialize OpenAI client
client = OpenAI(
    api_key='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'
)

# Rate limiting settings
MAX_REQUESTS_PER_MINUTE = 3000
BATCH_SIZE = 10  # Process 10 paragraphs in parallel
request_timestamps = []

def get_embeddings_batch(texts):
    """Get embeddings for a batch of texts with rate limiting"""
    global request_timestamps
    
    # Clean up old timestamps (older than 1 minute)
    current_time = datetime.now()
    request_timestamps = [ts for ts in request_timestamps 
                        if current_time - ts < timedelta(minutes=1)]
    
    # Check if we're about to exceed rate limit
    if len(request_timestamps) >= MAX_REQUESTS_PER_MINUTE:
        # Calculate sleep time needed
        sleep_time = (request_timestamps[0] + timedelta(minutes=1) - current_time).total_seconds()
        if sleep_time > 0:
            sleep(sleep_time)
        request_timestamps = request_timestamps[1:]
    
    try:
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=texts
        )
        # Record the request timestamp
        request_timestamps.append(datetime.now())
        return [data.embedding for data in response.data]
    except Exception as e:
        print(f"Error generating embeddings: {str(e)}")
        return [None] * len(texts)

@shared_task(bind=True, max_retries=3)
def process_document(self, document_id, file_content, filename):
    try:
        # Get document
        document = Document.objects.get(id=document_id)
        document.status = 'processing'
        document.save()

        # Decode base64 content
        if isinstance(file_content, str):
            file_content = base64.b64decode(file_content)

        # Create file-like object from content
        file_obj = ContentFile(file_content)
        file_obj.name = filename

        # Process the file
        content = process_file(file_obj)
        paragraphs = [p.strip() for p in content.strip().split('\n\n') if p.strip()]
        
        # Update total paragraphs
        document.total_paragraphs = len(paragraphs)
        document.save()

        # Process paragraphs in batches
        for i in range(0, len(paragraphs), BATCH_SIZE):
            batch = paragraphs[i:i + BATCH_SIZE]
            embeddings = get_embeddings_batch(batch)
            
            # Create TextEmbedding objects for successful embeddings
            for text, embedding in zip(batch, embeddings):
                if embedding is not None:
                    TextEmbedding.objects.create(
                        document=document,
                        text=text,
                        embedding=embedding
                    )
                    # Update progress
                    document.processed_paragraphs += 1
                    document.save()

        # Mark as completed
        document.status = 'completed'
        document.save()

    except Exception as e:
        # Handle errors
        document.status = 'failed'
        document.error_message = str(e)
        document.save()
        
        # Retry the task
        try:
            self.retry(exc=e, countdown=60)  # Retry after 60 seconds
        except self.MaxRetriesExceededError:
            document.error_message = f"Failed after {self.max_retries} retries: {str(e)}"
            document.save()