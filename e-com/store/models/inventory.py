from django.db import models
from .products import Product

class Inventory(models.Model):
    product = models.OneToOneField (Product,on_delete = models.CASCADE,related_name="inventory")
    stock_count = models.PositiveIntegerField(default= 0)
    last_updated = models.DateTimeField (auto_now=True)

    def __str__(self):
        return f'{self.product} - {self.stock_count}'