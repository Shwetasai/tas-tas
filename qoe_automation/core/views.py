from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import authenticate, login
from .models import (
    DataSource, PayrollRecord, Adjustment, RecastPL,
    QuickbookRecord, ProfitLossRecord,
    PDFDocument, ExportTemplate
)
from .serializers import (
    DataSourceSerializer, PayrollRecordSerializer, AdjustmentSerializer,
    RecastPLSerializer, QuickbookRecordSerializer,
    ProfitLossRecordSerializer,
    PDFDocumentSerializer, ExportTemplateSerializer
)
from rest_framework.authtoken.models import Token
from .utils import (
    process_payroll_file, process_quickbooks_file,
    process_profit_and_loss_file, suggest_adjustments,
    generate_recast_pl, process_stoc_file
)

class DataSourceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data_sources = DataSource.objects.all()
        serializer = DataSourceSerializer(data_sources, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = DataSourceSerializer(data=request.data)
        if serializer.is_valid():
            data_source = serializer.save(user=request.user)
            self.process_data_source(data_source)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def process_data_source(self, data_source):
        data_source.processing_status = 'PROCESSING'
        data_source.processing_started_at = timezone.now()
        data_source.save()
        try:
            if data_source.source_type == 'QB':
                process_quickbooks_file(data_source)
            elif data_source.source_type == 'PAYROLL':
                process_payroll_file(data_source)
            elif data_source.source_type == 'PL':
                process_profit_and_loss_file(data_source)
            elif data_source.source_type == 'STOC':
                process_stoc_file(data_source)
            data_source.processing_status = 'COMPLETED'
            data_source.processing_completed_at = timezone.now()
        except Exception as e:
            data_source.processing_status = 'FAILED'
            data_source.error_message = str(e)
        finally:
            data_source.save()

class DataSourceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        data_source = get_object_or_404(DataSource, pk=pk)
        serializer = DataSourceSerializer(data_source)
        return Response(serializer.data)

    def delete(self, request, pk):
        data_source = get_object_or_404(DataSource, pk=pk)
        data_source.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class DataSourceRecordsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        data_source = get_object_or_404(DataSource, pk=pk)
        if data_source.source_type == 'QB':
            records = data_source.quickbook_records.all()
            serializer = QuickbookRecordSerializer(records, many=True)
        elif data_source.source_type == 'PAYROLL':
            records = data_source.payroll_records.all()
            serializer = PayrollRecordSerializer(records, many=True)
        elif data_source.source_type == 'PL':
            records = data_source.profit_loss_records.all()
            serializer = ProfitLossRecordSerializer(records, many=True)
        else:
            return Response(
                {"error": "Invalid source type for records"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(serializer.data)

class AdjustmentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        adjustments = Adjustment.objects.all()
        serializer = AdjustmentSerializer(adjustments, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = AdjustmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_pending_review(self, request):
        adjustments = Adjustment.objects.filter(status='PENDING_REVIEW')
        serializer = AdjustmentSerializer(adjustments, many=True)
        return Response(serializer.data)

class AdjustmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        adjustment = get_object_or_404(Adjustment, pk=pk)
        serializer = AdjustmentSerializer(adjustment)
        return Response(serializer.data)

    def put(self, request, pk):
        adjustment = get_object_or_404(Adjustment, pk=pk)
        serializer = AdjustmentSerializer(adjustment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        adjustment = get_object_or_404(Adjustment, pk=pk)
        serializer = AdjustmentSerializer(adjustment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        adjustment = get_object_or_404(Adjustment, pk=pk)
        adjustment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AdjustmentSuggestionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data_source_id = request.data.get('data_source_id')
        if not data_source_id:
            return Response({"error": "data_source_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            data_source = DataSource.objects.get(pk=data_source_id)
        except DataSource.DoesNotExist:
            return Response({"error": "Data source not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            suggested_adjustments = suggest_adjustments(data_source)
            return Response({
                "message": f"Successfully suggested {len(suggested_adjustments)} adjustments for data source {data_source_id}",
                "suggested_adjustments_count": len(suggested_adjustments),
                "data_source_id": data_source_id
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Error suggesting adjustments: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RecastPLView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        recast_pls = RecastPL.objects.all()
        serializer = RecastPLSerializer(recast_pls, many=True)
        return Response(serializer.data)

    def post(self, request):
        data_source_id = request.data.get('data_source_id')
        month = request.data.get('month')
        year = request.data.get('year')
        adjustment_ids = request.data.get('adjustment_ids', [])
        if not all([data_source_id, month, year]):
            return Response(
                {"error": "data_source_id, month, and year are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            from datetime import date
            target_date = date(int(year), int(month), 1)
        except ValueError:
            return Response(
                {"error": "Invalid month or year provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            recast_pl_instance = generate_recast_pl(data_source_id, adjustment_ids, target_date)
            serializer = RecastPLSerializer(recast_pl_instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Error generating Recast P&L: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_monthly_report(self, request):
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        if not month or not year:
            return Response(
                {"error": "Month and year are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        report = RecastPL.objects.filter(
            period_start__year=year,
            period_start__month=month
        ).first()
        if not report:
            return Response(
                {"error": "No report found for the specified period"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = RecastPLSerializer(report)
        return Response(serializer.data)

class PDFDocumentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        documents = PDFDocument.objects.all()
        serializer = PDFDocumentSerializer(documents, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PDFDocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ExportTemplateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        templates = ExportTemplate.objects.all()
        serializer = ExportTemplateSerializer(templates, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ExportTemplateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    if not username or not password:
        return Response(
            {"error": "Please provide both username and password"},
            status=status.HTTP_400_BAD_REQUEST
        )
    user = authenticate(username=username, password=password)
    if user:
        login(request, user)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "user_id": user.id,
            "username": user.username
        })
    return Response(
        {"error": "Invalid credentials"},
        status=status.HTTP_401_UNAUTHORIZED
    )
