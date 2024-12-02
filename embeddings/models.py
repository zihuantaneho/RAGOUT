from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.db import connection
import numpy as np
import uuid

class Document(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_paragraphs = models.IntegerField(default=0)
    processed_paragraphs = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.filename} ({self.status})"

    @property
    def progress(self):
        if self.total_paragraphs == 0:
            return 0
        return int((self.processed_paragraphs / self.total_paragraphs) * 100)

class TextEmbedding(models.Model):
    text = models.TextField()
    embedding = ArrayField(models.FloatField(), size=1536)  # OpenAI embeddings are 1536-dimensional
    created_at = models.DateTimeField(auto_now_add=True)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='embeddings')

    def __str__(self):
        return f"Embedding for text: {self.text[:50]}..."

    class Meta:
        indexes = [
            models.Index(fields=['created_at']),
        ]

    @classmethod
    def create_vector_extension(cls):
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            # Create a function to convert array to vector
            cursor.execute("""
                CREATE OR REPLACE FUNCTION array_to_vector(input_array float[])
                RETURNS vector
                AS $$
                SELECT input_array::vector;
                $$ LANGUAGE SQL IMMUTABLE;
            """)

    @classmethod
    def find_similar(cls, query_embedding, limit=3):
        # Convert the embedding to a numpy array and normalize it
        query_array = np.array(query_embedding)
        query_norm = query_array / np.linalg.norm(query_array)
        
        # Convert the normalized array back to a list
        query_list = query_norm.tolist()
        
        # Construct the SQL query for cosine similarity search using array_to_vector conversion
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, text, embedding,
                       1 - (array_to_vector(embedding) <=> array_to_vector(%s::float[])) as cosine_similarity
                FROM embeddings_textembedding
                ORDER BY cosine_similarity DESC
                LIMIT %s
            """, [query_list, limit])
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'text': row[1],
                    'embedding': row[2],
                    'similarity': row[3]
                })
        
        return results
