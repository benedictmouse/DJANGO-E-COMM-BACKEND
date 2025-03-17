from django.contrib import admin
from .models import Product , Category , Inventory , CartItem , Cart , Order , OrderItem 
# from .models.category import Category
# from .models.inventory import Inventory



# Register your models here.
admin.site.register (Product)
admin.site.register (Category)
admin.site.register(Inventory)
admin.site.register(CartItem)
admin.site.register(Cart)
admin.site.register(Order)
admin.site.register(OrderItem)
