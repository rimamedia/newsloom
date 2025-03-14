from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request

from newsloom.contrib.serializers import IdsSerializer


class BulkDeleteMixin:

    @extend_schema(parameters=[IdsSerializer])
    def bulk_destroy(self, request: Request, *args, **kwargs) -> Response:
        serializers = IdsSerializer(data=request.query_params)
        serializers.is_valid(raise_exception=True)
        for instance in self.get_queryset().filter(pk__in=serializers.validated_data['id']):
            self.perform_destroy(instance)
        return Response('bulk_delete', status=status.HTTP_204_NO_CONTENT)
