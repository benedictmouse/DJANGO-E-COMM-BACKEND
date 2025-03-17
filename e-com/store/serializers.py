from rest_framework import serializers
from .models import Category, Product, Inventory, Cart, CartItem, Order, OrderItem

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_at']

class InventorySerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    
    class Meta:
        model = Inventory
        fields = ['id', 'product', 'product_name', 'stock_count', 'last_updated']
    
    def update(self, instance, validated_data):
        new_stock_count = validated_data.get('stock_count', instance.stock_count)
        instance.stock_count = new_stock_count
        instance.save()
        product = instance.product
        product.stock = new_stock_count
        product.save()
        return instance

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'category', 'category_name', 'stock', 'image', 'created_at']
    
    def create(self, validated_data):
        product = Product.objects.create(**validated_data)
        Inventory.objects.create(product=product, stock_count=product.stock)
        return product
    
    def update(self, instance, validated_data):
        stock = validated_data.get('stock', instance.stock)
        instance = super().update(instance, validated_data)
        inventory, created = Inventory.objects.get_or_create(product=instance)
        inventory.stock_count = stock
        inventory.save()
        return instance

class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    inventory = InventorySerializer(read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'category', 'stock', 'image', 'created_at', 'inventory']

class StockUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)

class PurchaseSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
    
    def validate(self, data):
        product = self.context.get('product')
        if not product:
            raise serializers.ValidationError("Product not provided")
        try:
            inventory = Inventory.objects.get(product=product)
            if inventory.stock_count < data['quantity']:
                raise serializers.ValidationError(f"Not enough stock. Available: {inventory.stock_count}")
        except Inventory.DoesNotExist:
            raise serializers.ValidationError("Inventory not found for this product")
        return data

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), write_only=True, source='product')
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'subtotal', 'added_at']
    
    def validate(self, data):
        product = data['product']
        quantity = data['quantity']
        try:
            inventory = Inventory.objects.get(product=product)
            if inventory.stock_count < quantity:
                raise serializers.ValidationError(f"Not enough stock available. Only {inventory.stock_count} items left.")
        except Inventory.DoesNotExist:
            raise serializers.ValidationError("Product has no inventory record.")
        return data

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price', 'total_items', 'created_at', 'updated_at']
        read_only_fields = ['user']

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'subtotal']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'user', 'full_name', 'email', 'address', 'phone', 'total', 'status', 'items', 'created_at', 'updated_at']
        read_only_fields = ['user', 'total', 'status']

class CheckoutSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    address = serializers.CharField()
    phone = serializers.CharField(max_length=20)
