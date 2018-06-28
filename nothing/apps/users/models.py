from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser

# from apps.goods.models import GoodsSKU
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from django.conf import settings

# Create your models here.

from utils.models import BaseModel



class User(AbstractUser, BaseModel):
    """用户"""
    class Meta:
        db_table = "df_users"

    #生成token
    def generate_active_token(self):
        """生成激活令牌"""
        # 参1 混淆用的盐  参2 过期时间
        serializer = Serializer(settings.SECRET_KEY, 3600)

        # dumps 通过算法 把用户id 转码 生成token  fdsfdsfdsfjldsfjjsdl
        token = serializer.dumps({"confirm": self.id})  # 返回bytes类型
        return token.decode()


class Address(BaseModel):
    """地址"""
    user = models.ForeignKey(User, verbose_name="所属用户")
    receiver_name = models.CharField(max_length=20, verbose_name="收件人")
    receiver_mobile = models.CharField(max_length=11, verbose_name="联系电话")
    detail_addr = models.CharField(max_length=256, verbose_name="详细地址")
    zip_code = models.CharField(max_length=6, verbose_name="邮政编码")

    class Meta:
        db_table = "df_address"



