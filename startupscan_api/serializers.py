from rest_framework import serializers

from startupscan_api.engines import AnalysisEngine

class PitchAnalysisSerializer(serializers.Serializer):
    text = serializers.CharField(required=False)
    text_file = serializers.FileField(required=False)
    audio = serializers.FileField(required=False)
    video = serializers.FileField(required=False)
    youtube_url = serializers.URLField(required=False, allow_blank=True)
    financial_data = serializers.JSONField(required=False)
    model_source = serializers.ChoiceField(
        choices=AnalysisEngine.values,
        required=False,
        default=AnalysisEngine.LOCAL,
    )




class ModelRetrainSerializer(serializers.Serializer):
    pitches = serializers.FileField()
    financials = serializers.FileField()



class BatchAnalysisSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)
    
    def validate_file(self, value):
        """Validate the input file"""
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("Only CSV files are accepted")

        # Check maximum size (10MB)
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(f"File too large. Max size is {max_size} bytes")
        
        return value