from rest_framework import serializers


class IdsSerializer(serializers.Serializer):
    id = serializers.ListField(child=serializers.IntegerField())
