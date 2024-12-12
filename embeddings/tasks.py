import os
import io
import numpy as np
from celery import shared_task
from .models import Document, TextEmbedding
from .utils import process_file, get_embedding

@shared_task
def process_document(document_id, file_content, filename):
    """Process document and create embeddings."""
    try:
        # Get document
        document = Document.objects.get(id=document_id)
        document.status = 'processing'
        document.save()

        # Process file content
        file_obj = io.BytesIO(file_content)
        text = process_file(file_obj, filename)

        # Split text into paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        document.total_paragraphs = len(paragraphs)
        document.save()

        # Create embeddings for each paragraph
        for i, paragraph in enumerate(paragraphs):
            embedding = get_embedding(paragraph)
            if embedding:
                TextEmbedding.objects.create(
                    text=paragraph,
                    embedding=embedding,
                    document=document
                )
            document.processed_paragraphs = i + 1
            document.save()

        document.status = 'completed'
        document.save()

    except Exception as e:
        if document:
            document.status = 'failed'
            document.error_message = str(e)
            document.save()
        raise