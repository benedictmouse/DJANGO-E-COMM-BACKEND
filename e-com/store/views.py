from rest_framework import viewsets, filters, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import (
    Category, Product, Inventory, Cart, CartItem, Order, OrderItem
)
from .serializers import (
    CategorySerializer, ProductSerializer, ProductDetailSerializer,
    InventorySerializer, StockUpdateSerializer, PurchaseSerializer,
    CartSerializer, CartItemSerializer, OrderSerializer, CheckoutSerializer
)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        if self.action == 'purchase':
            return PurchaseSerializer
        return ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.all()
        category = self.request.query_params.get('category')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')

        if category:
            queryset = queryset.filter(category_id=category)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        return queryset

    def perform_destroy(self, instance):
        Inventory.objects.filter(product=instance).delete()
        instance.delete()

    @action(detail=True, methods=['post'])
    def purchase(self, request, pk=None):
        product = self.get_object()
        serializer = self.get_serializer(data=request.data, context={'product': product})
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data['quantity']

        try:
            inventory = Inventory.objects.get(product=product)
        except Inventory.DoesNotExist:
            return Response({'error': 'Product is out of stock'}, status=status.HTTP_400_BAD_REQUEST)

        if inventory.stock_count < quantity:
            return Response({'error': 'Not enough stock available'}, status=status.HTTP_400_BAD_REQUEST)

        inventory.stock_count -= quantity
        inventory.save()

        product.stock = inventory.stock_count
        product.save()

        return Response({
            'status': 'success',
            'message': f'Purchased {quantity} of {product.name}',
            'remaining_stock': inventory.stock_count
        })


class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all()

    def get_serializer_class(self):
        if self.action in ['add_stock', 'remove_stock']:
            return StockUpdateSerializer
        return InventorySerializer

    @action(detail=True, methods=['post'])
    def add_stock(self, request, pk=None):
        inventory = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        inventory.stock_count += serializer.validated_data['quantity']
        inventory.save()

        product = inventory.product
        product.stock = inventory.stock_count
        product.save()

        return Response({
            'status': 'success',
            'message': f'Added stock',
            'new_stock_count': inventory.stock_count
        })

    @action(detail=True, methods=['post'])
    def remove_stock(self, request, pk=None):
        inventory = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data['quantity']

        if inventory.stock_count < quantity:
            return Response({'error': 'Not enough stock'}, status=status.HTTP_400_BAD_REQUEST)

        inventory.stock_count -= quantity
        inventory.save()

        product = inventory.product
        product.stock = inventory.stock_count
        product.save()

        return Response({'status': 'success', 'new_stock_count': inventory.stock_count})


class CartViewSet(viewsets.GenericViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def get_object(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        cart = self.get_object()
        serializer = CartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, defaults={'quantity': quantity}
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=['post'])
    def update_item(self, request):
        cart = self.get_object()
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 0))

        try:
            cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
            if quantity <= 0:
                cart_item.delete()
            else:
                cart_item.quantity = quantity
                cart_item.save()
            return Response(CartSerializer(cart).data)
        except CartItem.DoesNotExist:
            return Response({'error': 'Item not found in cart'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        cart = self.get_object()

        if not cart.items.exists():
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        checkout_serializer = CheckoutSerializer(data=request.data)
        checkout_serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            for item in cart.items.all():
                inventory = Inventory.objects.get(product=item.product)
                if inventory.stock_count < item.quantity:
                    return Response({'error': f'Not enough stock for {item.product.name}'}, status=status.HTTP_400_BAD_REQUEST)

            order = Order.objects.create(
                user=request.user,
                full_name=checkout_serializer.validated_data['full_name'],
                email=checkout_serializer.validated_data['email'],
                address=checkout_serializer.validated_data['address'],
                phone=checkout_serializer.validated_data['phone'],
                total=cart.total_price,
            )

            for item in cart.items.all():
                OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity, price=item.product.price)

                inventory = Inventory.objects.get(product=item.product)
                inventory.stock_count -= item.quantity
                inventory.save()

            cart.items.all().delete()
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status not in ['pending', 'processing']:
            return Response({'error': f'Cannot cancel order with status {order.status}'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            order.status = 'cancelled'
            order.save()

            for item in order.items.all():
                inventory, _ = Inventory.objects.get_or_create(product=item.product)
                inventory.stock_count += item.quantity
                inventory.save()

        return Response(OrderSerializer(order).data)
