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
from django.conf import settings
from django.conf.urls.static import static
from embeddings.views import (
    index, collections_list, collection_detail,
    delete_collection, delete_document, download_document,
    search, document_status, login_view, logout_view, signup_view
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('signup/', signup_view, name='signup'),
    path('collections/', collections_list, name='collections_list'),
    path('collections/<uuid:collection_id>/', collection_detail, name='collection_detail'),
    path('collections/<uuid:collection_id>/delete/', delete_collection, name='delete_collection'),
    path('documents/<uuid:document_id>/delete/', delete_document, name='delete_document'),
    path('documents/<uuid:document_id>/download/', download_document, name='download_document'),
    path('search/', search, name='search'),
    path('status/<uuid:document_id>/', document_status, name='document_status'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
