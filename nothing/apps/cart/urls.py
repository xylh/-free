
from django.conf.urls import include, url
from django.contrib import admin

from cart import views

urlpatterns = [


    url(r'^add$', views.AddCartView.as_view(), name='add'),  # 添加购物车
     url(r'^$', views.CartInfoView.as_view(), name='info'),  # 添加购物车

    url(r'^update$', views.UpdateCartView.as_view(), name='update'),
    url(r'^delete$', views.DeleteCartView.as_view(), name='delete'),



]



