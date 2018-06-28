import json

from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect

# Create your views here.
from django.utils import timezone
from django.views.generic import View
from django_redis import get_redis_connection

from goods.models import GoodsSKU
from orders.models import OrderInfo, OrderGoods

from users.models import Address
# from utils.views import LoginRequiredJsonMixin
from utils.views import LoginRequiredJsonMixin, TransactionAtomicMixin, LoginRequired


class PlaceView(View):
    def post(self, request):
        user = request.user

        # 1购物车点击传来数据
        # 2点击立即购买,传来sku_id和count
        # getlist可获取多个值
        sku_ids = request.POST.getlist('sku_ids')
        print(sku_ids)
        count = request.POST.get('count')
        if not user.is_authenticated():
            response = redirect('/users/login?next=/cart')
            # 用户没有登录

            if count is not None:
                # 取出cookie里的数据
                cart_json = request.COOKIES.get('cart')
                # 如果cookie里有数据
                print(cart_json)
                if cart_json:

                    cart_dict = json.loads(cart_json)
                else:
                    cart_dict = {}
                # {'id1':5,'id2':7}
                # 从立即购买页面进来 只有一个商品 取第0个
                print(sku_ids)
                sku_id = sku_ids[0]
                # 添加到字典里
                cart_dict[sku_id] = int(count)
                # 从定向到购物车
                if cart_dict:
                    response.set_cookie('cart', json.dumps(cart_dict))
            return response
            # 上面的逻辑最后再写

        # 检验参数
        if sku_ids is None:
            return redirect(reverse('cart:info'))
        # 1收货地址
        try:
            address = Address.objects.filter(user=user).latest('create_time')
        except:
            address = None
        total_count = 0
        total_amount = 0
        trans = 10
        total_sku_amount = 0
        skus = []
        redis_conn = get_redis_connection("default")
        cart_dict = redis_conn.hgetall("cart_%s" % user.id)
        if count is None:
            # 数据从购物车买出来的


            for sku_id in sku_ids:
                print(sku_id)
                try:
                    sku = GoodsSKU.objects.get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    return redirect(reverse('cart:info'))
                print(sku_id)
                sku_count = cart_dict.get(sku_id.encode())
                sku_count = int(sku_count)
                sku_amount = sku_count * sku.price
                # 把信息存到对象里
                sku.sku_count = sku_count
                sku.sku_amount = sku_amount
                # 获取总的数量和价格
                total_sku_amount += sku_amount
                total_count += sku_count
                skus.append(sku)

        else:
            for sku_id in sku_ids:
                try:
                    sku = GoodsSKU.objects.get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    return redirect(reverse('cart:info'))

                try:
                    sku_count = int(count)
                except:
                    return redirect(reverse('goods:detail', args=sku_id))
                if sku_count > sku.stock:
                    return redirect(reverse('goods:detail', args=sku_id))
                sku_amount = sku_count * sku.price
                sku.count = sku_count
                sku.amount = sku_amount
                # 获取总的数量和价格
                skus.append(sku)
                total_sku_amount += sku_amount
                total_count += sku_count
            # 吧商品存到购物车字典中
            cart_dict[sku_id] = sku_count

            # 吧商品存到购物车中

            redis_conn.hmset('cart_%s' % user.id, cart_dict)
        total_amount = total_sku_amount + trans
        con = {
            'skus': skus,
            "total_amount": total_amount,
            "total_count": total_count,
            'trans': trans,
            'address': address,
            'total_sku_amount': total_sku_amount,
            'sku_ids':','.join(sku_ids)
        }

        return render(request, 'place_order.html', con)


class CommitView(LoginRequiredJsonMixin, TransactionAtomicMixin, View):
    def post(self, request):
        user = request.user
        address_id = request.POST.get('address_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')
        # 校验参数
        print('++++++++++++++++++')
        print( address_id)
        print( sku_ids)
        if not all([address_id, pay_method, sku_ids]):
            return JsonResponse({'code': 1, "message": '参数不全'})

        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return JsonResponse({'code': 2, "message": '地址不对'})
        if pay_method not in OrderInfo.PAY_METHOD:
            return JsonResponse({'code': 3, "message": '支付方式不对'})
          # 注意这里生成订单时 还没有计算商品的总数量和总价格 后面再去添加 save一次

        redis_conn = get_redis_connection('default')
        redis_dict = redis_conn.hgetall('cart_%s' % user.id)
        # 订单号规则 20180315155959+userid
        order_id = timezone.now().strftime('%Y%m%d%H%M%S') + str(user.id)
        # 生成一个保存点 回滚用

        save_point = transaction.savepoint()
        try:

            order = OrderInfo.objects.create(
                order_id=order_id,  # 订单号
                user=user,  # 用户
                address=address,  # 地址
                total_amount=0,  # 总价格
                trans_cost=10,  # 运费
                pay_method=pay_method,  # 支付方式
            )
            total_count = 0  # 订单全部商品的总数量
            total_amount = 0  # 订单全部商品的总价格
            # 分割得到一个列表
            sku_ids = sku_ids.split(',')
            print(22222222222222)
            for sku_id in sku_ids:
                for i in range(3):
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except GoodsSKU.DoesNotExist:
                        return JsonResponse({'code': 4, "message": '商品不存在'})
                    # 获取当前商品的数量
                    sku_count = redis_dict.get(sku_id.encode())
                    sku_count = int(sku_count)
                    if sku_count > sku.stock:
                        # 有异常 订单就不需要了 回滚 到save_point
                        transaction.savepoint_rollback(save_point)
                        return JsonResponse({'code': 5, 'msg': '库存不足'})
                    # 保存之前查出来的库存
                    origin_stock = sku.stock
                    new_stock = origin_stock - sku_count
                    new_sales = sku.sales + sku_count
                    result = GoodsSKU.objects.filter(id=sku_id, stock=origin_stock) \
                        .update(stock=new_stock, sales=new_sales)
                    if result == 0 and i < 2:
                        continue
                    elif result==0 and i == 2:
                        transaction.savepoint_rollback(save_point)
                        return JsonResponse({'code':6,'message':'不成功'})
                    break

                # 当前商品总价
                sku_amount = sku_count * sku.price
                # 订单总价
                total_amount += sku_amount
                total_count += sku_count  # 订单总数

                # 保存商品数据到订单商品中

                # 保存一个商品数据到订单商品表OrderGoods
                OrderGoods.objects.create(
                    order=order,  # 当前商品属于的订单
                    sku=sku,  # 当前商品
                    count=sku_count,  # 当前商品的数量
                    price=sku.price,  #当前商品历史价
            )

            # 把订单总数量和总价格 添加进数据库
            order.total_amount = total_amount+10
            order.total_count = total_count
            order.save()
            # 清空购物车
        except Exception:
        # 有异常 订单就不需要了 回滚 到save_point
            transaction.savepoint_rollback(save_point)
            return JsonResponse({'code': 6, 'msg': '生成订单失败'})

        # 事务提交
        transaction.savepoint_commit(save_point)

        # 订单生成后删除购物车(hdel) 注意*sku_ids 解包
        redis_conn.hdel('cart_%s' % user.id, *sku_ids)
        # 后端 只负责订单生成
        # 成功或者失败 要去做什么 由前端来做
        return JsonResponse({'code': 0, "message": '提交成功'})
#我的订单
class UserOrdersView(LoginRequired, View):
    """用户订单页面"""
    def get(self, request, page):
        user = request.user
        # 查询当前用户所有订单
        orders = user.orderinfo_set.all().order_by("-create_time")

        for order in orders:
            # 通过字典把数字对应的汉字取出来 存到对象里
            order.status_name = OrderInfo.ORDER_STATUS[order.status]
            order.pay_method_name = OrderInfo.PAY_METHODS[order.pay_method]
            order.skus = []
            order_skus = order.ordergoods_set.all()
            for order_sku in order_skus:
                sku = order_sku.sku
                sku.count = order_sku.count
                sku.amount = order_sku.price * sku.count
                order.skus.append(sku)
        # 分页
        page = int(page)
        try:
            paginator = Paginator(orders, 3)
            page_orders = paginator.page(page)
        except EmptyPage:
            # 如果传入的页数不存在，就默认给第1页
            page_orders = paginator.page(1)
            page = 1
        # 页数
        page_list = paginator.page_range
        print(11111111111111)
        context = {
            "orders": page_orders,
            "page": page,
            "page_list": page_list,
        }

        return render(request, "user_center_order.html", context)