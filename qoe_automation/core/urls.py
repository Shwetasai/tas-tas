from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'data-sources', views.DataSourceViewSet)
router.register(r'quickbook-record', views.QuickbookRecordViewSet, basename='quickbook-record')
router.register(r'payroll-records', views.PayrollRecordViewSet)
router.register(r'adjustments', views.AdjustmentViewSet)
router.register(r'recast-pl', views.RecastPLViewSet)
router.register(r'supplemental-notes', views.SupplementalNoteViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('login/', views.login_view, name='login'),
] 