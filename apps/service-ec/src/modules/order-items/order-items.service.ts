import { BadRequestException, Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { OrderItem } from './order-item.entity';
import { Order } from '../orders/order.entity';
import { Product } from '../products/product.entity';
import { CreateOrderItemDto, UpdateOrderItemDto } from './order-item.dto';
import { getFaker } from '../../common/faker';

@Injectable()
export class OrderItemsService {
  // Handles order item CRUD and faker generation tied to orders/products.
  constructor(
    @InjectRepository(OrderItem)
    private readonly orderItemRepository: Repository<OrderItem>,
    @InjectRepository(Order)
    private readonly orderRepository: Repository<Order>,
    @InjectRepository(Product)
    private readonly productRepository: Repository<Product>,
  ) { }

  async create(dto: CreateOrderItemDto) {
    // Validate order + product then persist new order item.
    const order = await this.orderRepository.findOne({ where: { id: dto.orderId } });
    if (!order) {
      throw new BadRequestException('Order not found');
    }

    const product = await this.productRepository.findOne({
      where: { id: dto.productId },
    });
    if (!product) {
      throw new BadRequestException('Product not found');
    }

    const item = this.orderItemRepository.create({
      orderId: dto.orderId,
      productId: dto.productId,
      quantity: dto.quantity,
      unitPrice: dto.unitPrice.toFixed(2),
    });

    const saved = await this.orderItemRepository.save(item);

    // Update order total after creating a new item.
    const orderTotal = Number(order.totalAmount);
    const nextTotal = orderTotal + dto.unitPrice * dto.quantity;
    order.totalAmount = nextTotal.toFixed(2);
    await this.orderRepository.save(order);

    return saved;
  }

  async findAll() {
    // List order items with related order and product.
    return this.orderItemRepository.find({
      relations: { order: true, product: true },
      order: { createdAt: 'DESC' },
    });
  }

  async findOne(id: string) {
    // Fetch an order item by id.
    const item = await this.orderItemRepository.findOne({
      where: { id },
      relations: { order: true, product: true },
    });
    if (!item) {
      throw new NotFoundException('Order item not found');
    }
    return item;
  }

  async update(id: string, dto: UpdateOrderItemDto) {
    // Patch order item fields and persist.
    const item = await this.findOne(id);

    if (dto.orderId !== undefined) {
      const order = await this.orderRepository.findOne({
        where: { id: dto.orderId },
      });
      if (!order) {
        throw new BadRequestException('Order not found');
      }
      item.orderId = dto.orderId;
    }

    if (dto.productId !== undefined) {
      const product = await this.productRepository.findOne({
        where: { id: dto.productId },
      });
      if (!product) {
        throw new BadRequestException('Product not found');
      }
      item.productId = dto.productId;
    }

    if (dto.quantity !== undefined) {
      item.quantity = dto.quantity;
    }

    if (dto.unitPrice !== undefined) {
      item.unitPrice = dto.unitPrice.toFixed(2);
    }

    return this.orderItemRepository.save(item);
  }

  async remove(id: string) {
    // Remove order item by id.
    const item = await this.findOne(id);
    await this.orderItemRepository.remove(item);
    return item;
  }

  async fakerCreate(count: number, maxItemsPerOrder = 4) {
    // Generate faker order items and update order totals.
    const faker = await getFaker();
    const requested = Math.max(1, Math.min(count, 5000));
    const orderLimit = Math.max(1, Math.min(maxItemsPerOrder, 10));

    const orders = await this.orderRepository.find({ select: ['id', 'totalAmount'] });
    const products = await this.productRepository.find({ select: ['id', 'price'] });

    if (orders.length === 0) {
      throw new BadRequestException('No orders available for faker order items');
    }

    if (products.length === 0) {
      throw new BadRequestException('No products available for faker order items');
    }

    const totals = new Map<string, number>();
    orders.forEach((order) => {
      totals.set(order.id, Number(order.totalAmount));
    });

    const toCreate: OrderItem[] = [];
    let remaining = requested;

    for (const order of orders) {
      if (remaining <= 0) {
        break;
      }

      const itemCount = faker.number.int({
        min: 1,
        max: Math.min(orderLimit, remaining),
      });

      for (let i = 0; i < itemCount; i += 1) {
        const product = products[Math.floor(Math.random() * products.length)];
        const quantity = faker.number.int({ min: 1, max: 5 });
        const unitPrice = Number(product.price);

        toCreate.push(
          this.orderItemRepository.create({
            orderId: order.id,
            productId: product.id,
            quantity,
            unitPrice: unitPrice.toFixed(2),
          }),
        );

        totals.set(order.id, (totals.get(order.id) ?? 0) + unitPrice * quantity);
      }

      remaining -= itemCount;
    }

    const inserted = await this.orderItemRepository.save(toCreate);

    const ordersToUpdate = orders.map((order) =>
      this.orderRepository.create({
        id: order.id,
        totalAmount: (totals.get(order.id) ?? 0).toFixed(2),
      }),
    );

    await this.orderRepository.save(ordersToUpdate);

    return {
      requested,
      inserted: inserted.length,
    };
  }
}
