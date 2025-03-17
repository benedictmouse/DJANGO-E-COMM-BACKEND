from django.db import models
from .category import Category
from users.models import CustomUser


class Product(models.Model):
    name = models.CharField(max_length = 255)
    description = models.TextField ()
    price = models.DecimalField (max_digits = 10 , decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='products/')
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.name