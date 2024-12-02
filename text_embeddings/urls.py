"""
URL configuration for text_embeddings project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from embeddings.views import upload_file, search, document_status

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', upload_file, name='upload_file'),
    path('search/', search, name='search'),
    path('status/<uuid:document_id>/', document_status, name='document_status'),
]
