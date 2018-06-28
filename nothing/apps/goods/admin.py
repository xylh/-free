from django.contrib import admin

# Register your models here.
from django.core.cache import cache

from goods.models import GoodsCategory, Goods, GoodsSKU, IndexGoodsBanner, IndexCategoryGoodsBanner, \
    IndexPromotionBanner
from celery_tasks.tasks import generate_static_index


class BaseAdmin(admin.ModelAdmin):
    # request请求对象 obj就是操作的model的实例化对象，原始的数据form，change表示是添加还是更新
    def save_model(self, request, obj, form, change):
        # 运营人员添加或更新数据时会走的方法
        obj.save()
        # 数据一旦改变 就要生成新的静态页面
        generate_static_index .delay()
        cache.delete('indexpage_static_cache')
    def delete_model(self, request, obj):
        # 运营人员删除数据时会走的方法
        obj.delete()
        # 数据一旦改变 就要生成新的静态页面
        generate_static_index.delay()
        cache.delete('indexpage_static_cache')

class GoodsAdmin(BaseAdmin):
    pass


class GoodsCategoryAdmin(BaseAdmin):
    pass


class GoodsSKUAdmin(BaseAdmin):
    pass


class IndexGoodsBannerAdmin(BaseAdmin):
    pass


class IndexCategoryGoodsBannerAdmin(BaseAdmin):
    pass

class IndexPromotionBannerAdmin(BaseAdmin):
    pass


admin.site.register(GoodsCategory, GoodsCategoryAdmin)
admin.site.register(Goods, GoodsAdmin)
admin.site.register(GoodsSKU, GoodsSKUAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexCategoryGoodsBanner, IndexCategoryGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
