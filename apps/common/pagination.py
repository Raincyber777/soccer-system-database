"""分页：page/page_size 入参，输出 { total, page, page_size, pages, results }"""
import math

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class EnvelopePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'

    def get_paginated_response(self, data):
        page_size = self.get_page_size(self.request)
        return Response({
            'total': self.page.paginator.count,
            'page': self.page.number,
            'page_size': page_size,
            'pages': math.ceil(self.page.paginator.count / page_size) if page_size else 1,
            'results': data,
        })
