from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('embeddings', '0002_chatsession_chatmessage'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE EXTENSION IF NOT EXISTS vector;
            
            CREATE OR REPLACE FUNCTION array_to_vector(input_array float[])
            RETURNS vector
            AS $$
            SELECT input_array::vector;
            $$ LANGUAGE SQL IMMUTABLE;
            """,
            reverse_sql="""
            DROP FUNCTION IF EXISTS array_to_vector(float[]);
            DROP EXTENSION IF EXISTS vector;
            """
        ),
    ] 