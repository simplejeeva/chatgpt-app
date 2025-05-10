from . import views 
from django.urls import path

urlpatterns = [
    path('', views.index, name='index'),
    path('signup/', views.signup, name='signup'),
    path('signin/', views.signin, name='signin'),
    path('signout/', views.signout, name='signout'),
    path('get-value/', views.get_value, name='get_value'),
    path('upload-pdf/', views.upload_pdf, name='upload_pdf'),



]
