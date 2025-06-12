from rest_framework import serializers
from .models import (
    DataSource, PayrollRecord,
    Adjustment, RecastPL, SupplementalNote, QuickbookRecord, StocAccountingData
)

class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = '__all__'
        read_only_fields = ('uploaded_at', 'user',)

class QuickbookRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickbookRecord
        fields = '__all__'

class PayrollRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollRecord
        fields = '__all__'

class AdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Adjustment
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by')

class RecastPLSerializer(serializers.ModelSerializer):
    adjustments = serializers.PrimaryKeyRelatedField(many=True, queryset=Adjustment.objects.all(), required=False)

    class Meta:
        model = RecastPL
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['adjustments'] = AdjustmentSerializer(instance.adjustments.all(), many=True).data
        return representation

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

class SupplementalNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplementalNote
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class StocAccountingDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = StocAccountingData
        fields = '__all__'
        read_only_fields = ('uploaded_at', 'uploaded_by') 