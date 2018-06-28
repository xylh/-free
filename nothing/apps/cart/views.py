import json

from django.http import JsonResponse, response
from django.shortcuts import render

# Create your views here.
from django.views.generic import View
from django_redis import get_redis_connection

from goods.models import GoodsSKU


class AddCartView(View):
    """添加购物车"""

    def post(self, request):

        # 用户信息user
        # 应该接收的数据 skuid  数量count

        # 接收传来数据方法里的参数
        user = request.user

        # 需求后来让产品改了 不登录也能添加
        # if not user.is_authenticated():  # 必须登录后才能添加
        #
        #     return JsonResponse({'code': 5, 'msg': '用户没登录'})
        # 商品的skuid

        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 对数据校验(比如这个数据为空, 和这个数据乱传的清况, 通过判断和捕获异常的形式)
        if not all([sku_id, count]):
            return JsonResponse({'code': 1, 'mes': '参数不全'})

        # 验证商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'code': 2, 'mes': '商品不存在'})

        try:
            # 验证数量
            count = int(count)
        except Exception:
            return JsonResponse({'code': 3, 'mes': '数量不对'})

        # 数量不能超过库存
        if count > sku.stock:
            return JsonResponse({'code': 4, 'mes': '库存不足'})
        print(11111)
        # 如果用户登录 存到redis
        if user.is_authenticated():
            # 把数据存到redis   cart_userid: {'skuid1':10,'skuid2':3 ....}

            # 获取redis的链接实例
            redis_conn = get_redis_connection('default')
            # 判断当前的商品 是否已经存在于redis里

            # 获取商品之前的数量
            origin_count = redis_conn.hget('cart_%s' % user.id, sku_id)
            if origin_count is not None:
                # 已经存在 最后保存的数量 = 之前的数量+当前的数量
                # 注意redis里是string 要强转
                count += int(origin_count)
            # else:
            #     # 不存在   最后保存的数量 = 当前的数量
            # 保存到数据库
            redis_conn.hset('cart_%s' % user.id, sku_id, count)
        else:
            #  用户未登录 存到cookie中

            # 获取商品之前的数量
            # cart  ：  '{'skuid1':10,' skuid2':3 ....}'
            # 如果用户之前就没操作过购物车 获取的就是None
            cart_json = request.COOKIES.get('cart')
            if cart_json is not None:
                # 把字符串转为字典
                cart_dict = json.loads(cart_json)
            else:
                # 如果之前没操作过购物车 就生成一个空字典 方便后面使用
                cart_dict = {}

            # 判断当前商品是否保存过
            if sku_id in cart_dict:
                # 获取商品之前的数量
                origin_count = cart_dict.get(sku_id)
                count += origin_count

            # cart_dict :{'skuid1':10,' skuid2':3 ....}
            # 把添加后的数量 存到字典里
            print(222)
            cart_dict[sku_id] = count

        cart_num = 0
        # 如果登录 从redis查询购物车的数量
        if user.is_authenticated():
            # 查询购物车的数量
            # 获取用户
            user = request.user
            # 从redis中获取购物车信息
            redis_conn = get_redis_connection("default")
            # 如果redis中不存在，会返回None
            cart_dict = redis_conn.hgetall("cart_%s" % user.id)
            # else:
            # {'skuid1': 10, 'skuid2': 3....}
            # 没有登录 从cookie里获取  但是 获取的是旧的数据 新的数据已经在cart_dict里了
            # cart_json = request.COOKIES.get('cart')
            # cart_dict = json.loads(cart_json)
        print(3333)
        # 循环获取总的数量
        for val in cart_dict.values():
            cart_num += int(val)
        print(444)
        response = JsonResponse({'code': 0, 'mes': '添加购物车成功', 'cart_num': cart_num})
        print(555)
        print(cart_dict)
        if not user.is_authenticated():
            # 未登录 保存到cookie
            #  把字典转为字符串
            cart_json = json.dumps(cart_dict)
            # 保存到cookie中
            response.set_cookie('cart', cart_json)
        print(666)
        # {'code':3,'msg':'添加购物车失败'}   code 0 ：添加成功  代表状态码 一般0是成功
        return response


class CartInfoView(View):
    # 获取购物车数据
    def get(self, request):
        # 查询购物车的数据
        # 如果从redis中获取
        if request.user.is_authenticated():
            # 创建redis 链接对象
            redis_con = get_redis_connection('default')
            user_id = request.user.id
            # 获取所有的数据
            cart_dict = redis_con.hgetall('cart_%s' % user_id)

        else:
            # 未登录模式 从cook中获取
            cart_json = request.COOKIES.get('cart')

            # 判断用户数据库是否有数据
            if cart_json is not None:
                cart_dict = json.loads(cart_json)
            else:
                cart_dict = {}
        # 保存遍历出来的sku
        skus = []
        # 金额
        total_amount = 0
        # 总数量
        total_count = 0
        # 遍历cart_dict ,获取模板需要的数据
        for sku_id, count in cart_dict.items():
            # 获取商品的sku
            try:
                sku = GoodsSKU.objects.get(id=sku_id)
            except GoodsSKU.DoesNotExist:
                continue
            # redis 去处的是字符串,count许需要转化成int
            count = int(count)
            # 总价
            print(count)
            amount = sku.price * count

            sku.amount = amount
            sku.count = count
            # 生成模型类列表
            skus.append(sku)
            # 计:算总金额

            total_amount += amount
            total_count += count
        context = {
            'skus': skus,
            'total_amount': total_amount,
            'total_count': total_count,

        }
        # print(context)
        return render(request, 'cart.html', context)


class UpdateCartView(View):
    def post(self, request):
        # 获取参数：sku_id, count
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        # 校验参数all()
        if not all([sku_id, count]):
            return JsonResponse({'code': 1, 'message': '参数不对'})

        # 判断商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'code': 2, 'message': '商品不存在'})

        # 判断count是否是整数
        try:
            count = int(count)
        except Exception:
            return JsonResponse({'code': 3, 'message': '数量格式不对'})

        # 判断库存
        if count > sku.stock:
            return JsonResponse({'code': 4, 'message': '超过库存'})

        print(11111)
        # 判断用户是否登陆
        if request.user.is_authenticated():
            print(99999999)
            # 如果用户登陆，将修改的购物车数据存储到redis中
            redis_conn = get_redis_connection("default")
            user_id = request.user.id
            print(sku_id)
            redis_conn.hset('cart_%s' % user_id, sku_id, count)

            return JsonResponse({'code': 0, 'message': '保存成功'})
        # 如果用户未登陆，将修改的购物车数据存储到cookie中
        else:
            cart_json = request.COOKIES.get('cart')
            if cart_json is not None:
                cart_dict = json.loads(cart_json)
            else:
                cart_dict = {}
            print(2222)
            cart_dict[sku_id] = count
            # 将购物车字典转化为json字符串格式
            new_cart_dict = json.dumps(cart_dict)

            # 响应结果

            response = JsonResponse({'code': 0, 'message': '保存成功'})

            # 保存到cook中
            response.set_cookie('cart', new_cart_dict)

        return response


class DeleteCartView(View):
    def post(self, request):
        # 接收参数
        sku_id = request.POST.get('sku_id')
        # 判断参数是否为空
        if not sku_id:
            return JsonResponse({'code': 1, 'message': '参数为空'})
        # 判读用户是否登陆
        if request.user.is_authenticated():
            # 删除购物车数据
            redis_conn = get_redis_connection('default')

            user_id = request.user.id
            # 商品不存在可忽略
            redis_conn.hdel('cart_%s' % user_id, sku_id)
        else:
            # 未登录的状态
            cart_json = request.COOKIES.get('cart')
            if cart_json is not None:
                cart_dict = json.loads(cart_json)
                # 判断要删除的数据在字典中
                if sku_id in cart_dict:
                    del cart_dict[sku_id]
                    response = JsonResponse({'code': 0, "message": '删除成功'})
                    response.set_cookie('cart', json.dumps(cart_dict))
                    return response
        # 当删除成功或者没有要删除的都提示用户成功
        return JsonResponse({'code': 0, 'message': '删除成功'})
