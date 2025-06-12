from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Sum
from django.contrib.auth import authenticate, login
from .models import (
    DataSource, PayrollRecord,
    Adjustment, RecastPL, SupplementalNote, QuickbookRecord, StocAccountingData
)
from .serializers import (
    DataSourceSerializer, PayrollRecordSerializer,
    AdjustmentSerializer, RecastPLSerializer, SupplementalNoteSerializer, QuickbookRecordSerializer, StocAccountingDataSerializer
)
from rest_framework.authtoken.models import Token
from .utils import process_payroll_file, process_quickbooks_file, suggest_adjustments, generate_recast_pl, process_stoc_file
from datetime import date


class DataSourceViewSet(viewsets.ModelViewSet):
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Data source deleted successfully"}, status=status.HTTP_200_OK)

class QuickbookRecordViewSet(viewsets.ModelViewSet):
    queryset = QuickbookRecord.objects.all()
    serializer_class = QuickbookRecordSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def process_data_source(self, request):
        data_source_id = request.data.get('data_source_id')
        if not data_source_id:
            return Response({"error": "data_source_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data_source = DataSource.objects.get(id=data_source_id, source_type='QB')
        except DataSource.DoesNotExist:
            return Response({"error": "QuickBooks data source not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            processed_records = process_quickbooks_file(data_source.file_path.path)
            
            for record in processed_records:
                record.data_source = data_source
                record.save()

            return Response(
                {"message": f"Successfully processed {len(processed_records)} QuickBooks records from data source {data_source_id}"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": f"Error processing QuickBooks file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def monthly_summary(self, request):
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        
        if not month or not year:
            return Response(
                {"error": "Month and year are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        summary = self.queryset.filter(
            date__year=year,
            date__month=month
        ).values('account_name').annotate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )

        return Response(summary)

class PayrollRecordViewSet(viewsets.ModelViewSet):
    queryset = PayrollRecord.objects.all()
    serializer_class = PayrollRecordSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def monthly_summary(self, request):
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        
        if not month or not year:
            return Response(
                {"error": "Month and year are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        summary = self.queryset.filter(
            date__year=year,
            date__month=month
        ).aggregate(
            total_compensation=Sum('compensation'),
            total_taxes=Sum('taxes'),
            total_benefits=Sum('benefits')
        )

        return Response(summary)

    @action(detail=False, methods=['post'])
    def process_data_source(self, request):
        data_source_id = request.data.get('data_source_id')
        if not data_source_id:
            return Response({"error": "data_source_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data_source = DataSource.objects.get(id=data_source_id, source_type='PAYROLL')
        except DataSource.DoesNotExist:
            return Response({"error": "Payroll data source not found"}, status=status.HTTP_404_NOT_FOUND)

        try:

            processed_records = process_payroll_file(data_source.file_path.path)
            
            for record in processed_records:
                record.data_source = data_source
                record.save()

            return Response(
                {"message": f"Successfully processed {len(processed_records)} payroll records from data source {data_source_id}"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": f"Error processing payroll file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Payroll record deleted successfully"}, status=status.HTTP_200_OK)

class AdjustmentViewSet(viewsets.ModelViewSet):
    queryset = Adjustment.objects.all()
    serializer_class = AdjustmentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Adjustment deleted successfully"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def suggest(self, request):
        quickbook_records = QuickbookRecord.objects.all()
        payroll_records = PayrollRecord.objects.all()

        suggestions = suggest_adjustments(quickbook_records, payroll_records)

        saved_count = 0
        for suggestion in suggestions:
            suggestion.created_by = request.user
            suggestion.save()
            saved_count += 1

        return Response(
            {"message": f"Successfully suggested and saved {saved_count} adjustments."},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def pending_review(self, request):
        pending = self.queryset.filter(status='PENDING')
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)

class RecastPLViewSet(viewsets.ModelViewSet):
    queryset = RecastPL.objects.all()
    serializer_class = RecastPLSerializer
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Recast P&L statement deleted successfully"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        month = request.data.get('month')
        year = request.data.get('year')
        
        if not month or not year:
            return Response(
                {"error": "Month and year are required in the request body"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            target_date = date(int(year), int(month), 1) 
        except ValueError:
            return Response(
                {"error": "Invalid month or year provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        quickbook_records = QuickbookRecord.objects.filter(
            date__year=year,
            date__month=month
        )

        approved_adjustments = Adjustment.objects.filter(
            status='APPROVED',
            date__year=year,
            date__month=month
        )

        recast_pl_data = generate_recast_pl(quickbook_records, approved_adjustments, target_date)
        
        recast_pl_instance, created = RecastPL.objects.get_or_create(
            date=target_date, 
            defaults=recast_pl_data 
        )
        
        if not created:
            recast_pl_instance.revenue = recast_pl_data['revenue']
            recast_pl_instance.cogs = recast_pl_data['cogs']
            recast_pl_instance.gross_profit = recast_pl_data['gross_profit']
            recast_pl_instance.operating_expenses = recast_pl_data['operating_expenses']
            recast_pl_instance.ebitda = recast_pl_data['ebitda']
            recast_pl_instance.save()
            
        recast_pl_instance.adjustments.clear()
        recast_pl_instance.adjustments.set(approved_adjustments)

        serializer = self.get_serializer(recast_pl_instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def monthly_report(self, request):
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        
        if not month or not year:
            return Response(
                {"error": "Month and year are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        report = self.queryset.filter(
            date__year=year,
            date__month=month
        ).first()

        if not report:
            return Response(
                {"error": "No report found for the specified month"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(report)
        return Response(serializer.data)

class SupplementalNoteViewSet(viewsets.ModelViewSet):
    queryset = SupplementalNote.objects.all()
    serializer_class = SupplementalNoteSerializer
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Supplemental note deleted successfully"}, status=status.HTTP_200_OK)

class StocAccountingDataViewSet(viewsets.ModelViewSet):
    queryset = StocAccountingData.objects.all()
    serializer_class = StocAccountingDataSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    @action(detail=False, methods=['post'])
    def process_data_source(self, request):
        data_source_id = request.data.get('data_source_id')
        if not data_source_id:
            return Response({"error": "data_source_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data_source = DataSource.objects.get(id=data_source_id, source_type='STOC')
        except DataSource.DoesNotExist:
            return Response({"error": "STOC data source not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            from .utils import process_stoc_file
            processed_records_count = process_stoc_file(data_source.file_path.path, self.request.user)

            return Response(
                {"message": f"Successfully processed {processed_records_count} STOC accounting records from data source {data_source_id}"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": f"Error processing STOC file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    if username is None or password is None:
        return Response({'error': 'Please provide both username and password'},
                      status=status.HTTP_400_BAD_REQUEST)
    
    user = authenticate(username=username, password=password)
    
    if not user:
        return Response({'error': 'Invalid credentials'},
                      status=status.HTTP_401_UNAUTHORIZED)
    
    token, _ = Token.objects.get_or_create(user=user)
    
    return Response({
        'access_token': token.key,
        'token_type': 'Bearer',
        'user_id': user.pk,
        'username': user.username
    })
