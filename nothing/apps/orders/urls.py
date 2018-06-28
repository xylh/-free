
from django.conf.urls import include, url
from django.contrib import admin

from orders import views

urlpatterns = [

    url(r'^place$', views.PlaceView.as_view(), name='place'),
   url(r'^commit$', views.CommitView.as_view(), name='commit'),
    # 我的订单
    url('^(?P<page>\d+)$', views.UserOrdersView.as_view(), name="info"),



]



