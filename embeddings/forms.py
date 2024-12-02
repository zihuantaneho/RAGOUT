from django import forms

class TextFileUploadForm(forms.Form):
    file = forms.FileField(
        label='Select a file',
        help_text='Upload a .txt, .pdf, or .docx file to generate embeddings.',
        widget=forms.FileInput(attrs={
            'accept': '.txt,.pdf,.docx',
            'class': 'form-control'
        })
    )

class SearchForm(forms.Form):
    query = forms.CharField(
        label='Ask a question',
        help_text='Enter your question about the uploaded text.',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'What would you like to know about the text?'
        })
    ) 