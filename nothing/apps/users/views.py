import json
import re
import itsdangerous
from django_redis import get_redis_connection

from goods.models import GoodsSKU
from utils.views import LoginRequired
from django.contrib.auth.decorators import login_required
from django.contrib.sessions.backends import db
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.utils.decorators import classonlymethod
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from django.conf import settings
# Create your views here.
# def register(request):
#     if request.method=='GET':
#
#         return  render(request,'register.html')
#     else:
#         return HttpResponse('ouu')
from django.views.generic import View
# from pymongo.auth import authenticate
from django.contrib.auth import authenticate, login, logout
from celery_tasks.tasks import send_active_email
from users.models import User, Address
from utils.views import LoginRequired


class RegisterView(View):
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        # 获取传入的数据
        username = request.POST.get("user_name")
        psw = request.POST.get("pwd")
        allow = request.POST.get("allow")
        email = request.POST.get("email")
        # 检验数据
        # 判断是否为空
        if not all([username, psw, email]):
            return redirect(reverse('users:register'))
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'error': '邮箱格式错误 '})
        if allow != 'on':
            return render(request, 'register.html', {'err': '请勾选协议'})
        # 密码加密
        try:

            user = User.objects.create_user(username=username, email=email, password=psw)
        except db.IntegrityError:
            return render(request, 'register.html', {'error': '用户已存在 '})
        user.is_active = False
        user.save()
        # 给用户发邮件

        # 生成token  包含user.id  生成token的过程 叫签名:
        token = user.generate_active_token()

        # 给用户发送激活邮件

        # 接收邮件的人 可以有多个
        # recipient_list = [user.email] 应该发给user.email
        #  为了测试方便 就写固定了了
        recipient_list = ['18625325890@163.com']  # user.email

        # 发送邮件的方法  发邮件是耗时的  处理图片 音视频 需要异步执行
        # 通过delay调用 通知work执行任务
        send_active_email.delay(recipient_list, user.username, token)

        # 5给浏览器响应
        # return render(request, 'index.html')
        return redirect('/goods/index')
    from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
    from django.conf import settings


class ActiveView(View):
    def get(self, request, token):
        # 解析token 获取用户id数据
        # 参1 混淆用的盐  参2 过期时间
        serializer = Serializer(settings.SECRET_KEY, 360)
        try:
            result = serializer.loads(token)  # {"confirm": self.id}
        except itsdangerous.SignatureExpired:
            return HttpResponse('激活邮件已过期')

        userid = result.get('confirm')
        print(userid)
        print(11111)

        # # 根据id获取用户
        try:
            user = User.objects.get(id=userid)
        except User.DoesNotExist:
            return HttpResponse('用户不存在')

        if user.is_active:
            return HttpResponse('用户已经激活')
        print(222)

        # # 激活用户
        user.is_active = True
        user.save()  # update
        print(333)
        return redirect(request, 'users:login')


class LoginView(View):
    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        # 接收数据
        username = request.POST.get('username')
        psw = request.POST.get('pwd')
        print(username)
        print(psw)
        # 校验数据
        if not all([username, psw]):
            return redirect(reverse('users:login'))

        # 数据库获取用户

        # django提供的验证方法 成功返回user对象 不成功返回none

        user = authenticate(username=username, password=psw)
        if user is None:
            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})
        #
        # # 判断是否激活
        if not user.is_active:
            return render(request, 'login.html', {'errmsg': '用户未激活'})

        # # django提供的 用来保存用户信息 到session里 实现比如十天不用登录等功能
        login(request, user)
        #
        # # 获取是否记住用户
        remembered = request.POST.get('remembered')
        if remembered != 'on':
            request.session.set_expiry(0)
        else:
            request.session.set_expiry(None)
        # 在页面跳转之前，将cookie中和redis中的购物车数据合并
        # 从cookie中获取购物车数据
        cart_json = request.COOKIES.get('cart')
        if cart_json is not None:
            cart_dict_cookie = json.loads(cart_json)
        else:
            cart_dict_cookie = {}

        # 从redis中获取购物车数据
        redis_conn = get_redis_connection('default')
        cart_dict_redis = redis_conn.hgetall('cart_%s' % user.id)

        # 进行购物车商品数量合并:将cookie中购物车数量合并到redis中
        for sku_id, count in cart_dict_cookie.items():
            # 提示：由于redis中的键与值都是bytes类型，cookie中的sku_id是字符串类型
            # 需要将cookie中的sku_id字符串转成bytes
            sku_id = sku_id.encode()

            if sku_id in cart_dict_redis:
                # 如果cookie中的购物车商品在redis中也有，就取出来累加到redis中
                # 提示：redis中的count是bytes,cookie中的count是整数，无法求和,所以，转完数据类型在求和
                origin_count = cart_dict_redis[sku_id]
                count += int(origin_count)

            # 如果cookie中的商品在redis中有，就累加count赋值。反之，直接赋值cookie中的count
            cart_dict_redis[sku_id] = count

        # 将合并后的redis数据，设置到redis中:redis_conn.hmset()不能传入空字典
        if cart_dict_redis:
            redis_conn.hmset('cart_%s' % user.id, cart_dict_redis)

        next = request.GET.get('next')
        if next is None:

            response=redirect(reverse('goods:index'))

        else:


             response=redirect(next)
        response.delete_cookie('cart')
        return response


class LogoutView(View):
    def get(self, request):
        # 清楚登陆的信息
        logout(request)
        # 返回主页
        return redirect(reverse('goods:index'))


class AddrView(LoginRequired, View):
    def get(self, request):
        # 如果用户登陆后就是User的对象
        # user=request.user
        # if not user.is_authenticated():
        user = request.user
        try:
            address = user.address_set.latest('create_time')
        except Address.DoesNotExist:
            address = None

        con = {'add': address, }

        return render(request, 'user_center_site.html', con)

    def post(self, request):
        """修改地址信息"""
        user = request.user
        # 获取地址信息
        recv_name = request.POST.get("recv_name")
        addr = request.POST.get("addr")
        zip_code = request.POST.get("zip_code")
        recv_mobile = request.POST.get("recv_mobile")
        # 判断不为空
        if all([recv_name, addr, zip_code, recv_mobile]):
            # address = Address(
            #     user=user,
            #     receiver_name=recv_name,
            #     detail_addr=addr,
            #     zip_code=zip_code,
            #     receiver_mobile=recv_mobile
            # )
            # address.save()

            # 创建好一个地址信息 保存到数据库 insert
            Address.objects.create(
                user=user,
                receiver_name=recv_name,
                detail_addr=addr,
                zip_code=zip_code,
                receiver_mobile=recv_mobile
            )

        return redirect(reverse("users:address"))


class UserInfoView(LoginRequired, View):
    def get(self, request):
        user = request.user
        # 排序获取最近添加的地址 只会返回一个值
        try:
            address = request.user.address_set.latest('create_time')
        except Address.DoesNotExist:
            # 没有获取到地址
            address = None
        print('-------------------------------------------------')
        # 获取浏览记录
        # 存在redis  string 列表 集合 有序集合 hash   key-value

        # 存的是  ‘history_userid’ : [sku1.id,sku2.id,sku3.id,sku4.idsku5.id]
        # 获取redis链接shili
        con = get_redis_connection('default')
        # 获取钱5 个的数据yadan

        sku_ids = con.lrange('history_%s' % user.id, 0, 4)
        print(sku_ids)
        # ids=GoodsSKU.objects.filter(id__in = sku_ids)
        list = []
        for sku in sku_ids:
            # 查询每一件商品的sku

            id = GoodsSKU.objects.get(id=sku)
            list.append(id)

        context = {
            "address": address,
            'skus':list,
        }
        return render(request, 'user_center_info.html', context)
