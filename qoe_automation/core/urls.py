from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),

    path('data-sources/', views.DataSourceView.as_view(), name='data-source-list-create'),
    path('data-sources/<int:pk>/', views.DataSourceDetailView.as_view(), name='data-source-detail'),
    path('data-sources/<int:pk>/records/', views.DataSourceRecordsView.as_view(), name='data-source-records'),

    path('adjustments/', views.AdjustmentView.as_view(), name='adjustment-list-create'),
    path('adjustments/<int:pk>/', views.AdjustmentDetailView.as_view(), name='adjustment-detail'),
    path('adjustments/suggest/', views.AdjustmentSuggestionView.as_view(), name='adjustment-suggest'),

    path('recast-pl/', views.RecastPLView.as_view(), name='recast-pl-list-create'),

    path('pdf-documents/', views.PDFDocumentView.as_view(), name='pdf-document-list-create'),

    path('export-templates/', views.ExportTemplateView.as_view(), name='export-template-list-create'),
] 