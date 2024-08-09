from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('stat/', views.stat, name='stat'),
    path('download/', views.download, name='download'),
    path('wx_get_qr_code/', views.wx_get_qr_code, name='wx_get_qr_code'),
    path('wx_login_callback/', views.wx_login_callback, name='wx_login_callback'),
    path('wx_create_payment/', views.wx_create_payment, name='wx_create_payment'),
    path('wx_payment_callback/', views.wx_payment_callback, name='wx_payment_callback'),
    path('logout/', views.do_logout, name='logout'),
]
