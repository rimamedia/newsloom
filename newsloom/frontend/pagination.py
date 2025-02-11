from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100
    # Parameter to disable pagination
    no_pagination_param = "no_pagination"

    def get_paginated_response(self, data):
        # Check if pagination should be disabled
        if (
            self.request
            and self.request.query_params.get(self.no_pagination_param, "").lower()
            == "true"
        ):
            return Response(data)

        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )

    def paginate_queryset(self, queryset, request, view=None):
        # Check if pagination should be disabled
        if (
            request
            and request.query_params.get(self.no_pagination_param, "").lower() == "true"
        ):
            return None

        return super().paginate_queryset(queryset, request, view)
