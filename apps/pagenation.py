from rest_framework.pagination import PageNumberPagination

class CustomPagination(PageNumberPagination):
    page_size = 10  # default sahifa o'lchami
    page_size_query_param = 'page_size'  # URLda ?page_size=20 qilib o'zgartirish mumkin
    max_page_size = 100
