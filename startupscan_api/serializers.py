from rest_framework import serializers

class PitchAnalysisSerializer(serializers.Serializer):
    text = serializers.CharField(required=False)
    audio = serializers.FileField(required=False)
    video = serializers.FileField(required=False)
    financial_data = serializers.JSONField(required=False)
    model_source = serializers.ChoiceField(
        choices=["local", "gpt"],
        required=False,
        default="local",
    )




class ModelRetrainSerializer(serializers.Serializer):
    pitches = serializers.FileField()
    financials = serializers.FileField()



from rest_framework import serializers

class BatchAnalysisSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)
    
    def validate_file(self, value):
        """Validar o arquivo de entrada"""
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("Only CSV files are accepted")
        
        # Verificar tamanho máximo (10MB)
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(f"File too large. Max size is {max_size} bytes")
        
        return value