import { BadRequestException, Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Order } from './order.entity';
import { User } from '../users/user.entity';
import { CreateOrderDto, UpdateOrderDto } from './order.dto';
import { getFaker } from '../../common/faker';

@Injectable()
export class OrdersService {
  // Handles order CRUD and faker generation tied to users.
  constructor(
    @InjectRepository(Order)
    private readonly orderRepository: Repository<Order>,
    @InjectRepository(User)
    private readonly userRepository: Repository<User>,
  ) { }

  async create(dto: CreateOrderDto) {
    // Validate user then persist a new order.
    const user = await this.userRepository.findOne({ where: { id: dto.userId } });
    if (!user) {
      throw new BadRequestException('User not found');
    }

    const totalAmount = dto.totalAmount ?? 0;

    const order = this.orderRepository.create({
      userId: dto.userId,
      status: dto.status ?? 'pending',
      totalAmount: totalAmount.toFixed(2),
    });

    return this.orderRepository.save(order);
  }

  async findAll() {
    // List orders with user and item relations.
    return this.orderRepository.find({
      relations: { user: true, items: { product: true } },
      order: { createdAt: 'DESC' },
    });
  }

  async findOne(id: string) {
    // Fetch an order by id with relations.
    const order = await this.orderRepository.findOne({
      where: { id },
      relations: { user: true, items: { product: true } },
    });
    if (!order) {
      throw new NotFoundException('Order not found');
    }
    return order;
  }

  async update(id: string, dto: UpdateOrderDto) {
    // Patch order fields and persist.
    const order = await this.findOne(id);

    if (dto.userId !== undefined) {
      const user = await this.userRepository.findOne({ where: { id: dto.userId } });
      if (!user) {
        throw new BadRequestException('User not found');
      }
      order.userId = dto.userId;
    }

    if (dto.status !== undefined) {
      order.status = dto.status ?? 'pending';
    }

    if (dto.totalAmount !== undefined) {
      order.totalAmount = dto.totalAmount.toFixed(2);
    }

    return this.orderRepository.save(order);
  }

  async remove(id: string) {
    // Remove order by id.
    const order = await this.findOne(id);
    await this.orderRepository.remove(order);
    return order;
  }

  async fakerCreate(count: number) {
    // Generate faker orders linked to existing users.
    const faker = await getFaker();
    const requested = Math.max(1, Math.min(count, 5000));
    const users = await this.userRepository.find({ select: ['id'] });
    if (users.length === 0) {
      throw new BadRequestException('No users available for faker orders');
    }

    const toCreate = Array.from({ length: requested }).map(() => {
      const user = users[Math.floor(Math.random() * users.length)];
      return this.orderRepository.create({
        userId: user.id,
        status: faker.helpers.arrayElement(['pending', 'paid', 'shipped', 'cancelled']),
        totalAmount: '0.00',
      });
    });

    const inserted = await this.orderRepository.save(toCreate);
    return {
      requested,
      inserted: inserted.length,
    };
  }
}
