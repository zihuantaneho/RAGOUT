import os
import json
from openai import OpenAI
from openai import RateLimitError, AuthenticationError

# Initialize OpenAI client with API key
client = OpenAI(
    api_key=''
)

def read_paragraphs(filename):
    with open(filename, 'r') as file:
        content = file.read()
        paragraphs = content.strip().split('\n\n')
        return paragraphs

def get_embedding(text):
    try:
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding
    except RateLimitError as e:
        print(f"Error: OpenAI API quota exceeded. Please check your billing details.")
        print(f"Error details: {str(e)}")
        return None
    except AuthenticationError as e:
        print(f"Error: Authentication failed. Please check your API key.")
        print(f"Error details: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None

def save_to_json(data, filename='paragraph_embeddings.json'):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\nSaved embeddings to {filename}")

def main():
    # Read paragraphs
    paragraphs = read_paragraphs('sample_text.txt')
    
    # Create array to store paragraph objects
    paragraph_objects = []
    
    # Process each paragraph
    for i, paragraph in enumerate(paragraphs, 1):
        print(f"\nProcessing paragraph {i}...")
        
        # Generate embedding for the paragraph
        embedding = get_embedding(paragraph)
        
        if embedding is None:
            print("Failed to generate embedding. Stopping process.")
            break
            
        # Create paragraph object
        paragraph_obj = {
            "type": "paragraph",
            "text": paragraph,
            "embeddings": embedding
        }
        
        # Add to array
        paragraph_objects.append(paragraph_obj)
        
        print(f"Successfully processed paragraph {i}")
    
    if paragraph_objects:
        # Save results to file
        save_to_json(paragraph_objects)
        
        # Print summary
        for i, obj in enumerate(paragraph_objects, 1):
            print(f"\nParagraph {i}:")
            print(f"Text: {obj['text']}")
            print(f"Embedding length: {len(obj['embeddings'])}")

if __name__ == "__main__":
    main() 
