from rest_framework import serializers
from .models import (
    DataSource, PayrollRecord,
    Adjustment, RecastPL, SupplementalNote, QuickbookRecord, StocAccountingData, ProfitLossRecord,
    PDFDocument, ExportTemplate
)

class QuickbookRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickbookRecord
        fields = '__all__'

class PayrollRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollRecord
        fields = '__all__'

class ProfitLossRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfitLossRecord
        fields = '__all__'

class SupplementalNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplementalNote
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class DataSourceSerializer(serializers.ModelSerializer):
    quickbook_records = QuickbookRecordSerializer(many=True, read_only=True, source='quickbookrecord_set')
    payroll_records = PayrollRecordSerializer(many=True, read_only=True, source='payrollrecord_set')
    profit_loss_records = ProfitLossRecordSerializer(many=True, read_only=True, source='profitlossrecord_set')
    supplemental_notes = SupplementalNoteSerializer(many=True, read_only=True, source='supplementalnote_set')

    class Meta:
        model = DataSource
        fields = '__all__'
        read_only_fields = ('uploaded_at', 'user',)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.source_type == 'QB':
            representation.pop('payroll_records', None)
            representation.pop('profit_loss_records', None)
            representation.pop('supplemental_notes', None)
        elif instance.source_type == 'PAYROLL':
            representation.pop('quickbook_records', None)
            representation.pop('profit_loss_records', None)
            representation.pop('supplemental_notes', None)
        elif instance.source_type == 'PL':
            representation.pop('quickbook_records', None)
            representation.pop('payroll_records', None)
            representation.pop('supplemental_notes', None)
        elif instance.source_type == 'SUPPLEMENTAL':
            representation.pop('quickbook_records', None)
            representation.pop('payroll_records', None)
            representation.pop('profit_loss_records', None)
        elif instance.source_type == 'STOC':
            representation.pop('quickbook_records', None)
            representation.pop('payroll_records', None)
            representation.pop('profit_loss_records', None)
            representation.pop('supplemental_notes', None)
        return representation

class AdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Adjustment
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by')

class RecastPLSerializer(serializers.ModelSerializer):
    adjustments = AdjustmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = RecastPL
        fields = [
            'id', 'date', 'revenue', 'cogs', 'gross_profit', 'operating_expenses',
            'ebitda', 'adjustments', 'created_at', 'updated_at', 'export_format',
            'export_status', 'validation_status'
        ]
        read_only_fields = ('created_at', 'updated_at')

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['adjustments'] = AdjustmentSerializer(instance.adjustments.all(), many=True).data
        return rep

    def create(self, validated_data):
        adjustments_data = validated_data.pop('adjustments', [])
        recast_pl = RecastPL.objects.create(**validated_data)
        recast_pl.adjustments.set(adjustments_data)
        return recast_pl

    def update(self, instance, validated_data):
        adjustments_data = validated_data.pop('adjustments', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if adjustments_data is not None:
            instance.adjustments.set(adjustments_data)

        return instance

class StocAccountingDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = StocAccountingData
        fields = '__all__'
        read_only_fields = ('uploaded_at', 'uploaded_by')

class PDFDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PDFDocument
        fields = '__all__'
        read_only_fields = ('uploaded_at', 'parsed_content', 'parsing_status')

class ExportTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportTemplate
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by') 