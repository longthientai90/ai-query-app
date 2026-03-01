import { Body, Controller, Delete, Get, Param, Patch, Post, Query } from '@nestjs/common';
import { OrderItemsService } from './order-items.service';
import { CreateOrderItemDto, UpdateOrderItemDto } from './order-item.dto';

@Controller('order-items')
export class OrderItemsController {
  // Exposes HTTP endpoints for order item CRUD and faker operations.
  constructor(private readonly orderItemsService: OrderItemsService) {}

  @Post()
  create(@Body() dto: CreateOrderItemDto) {
    // Create a new order item.
    return this.orderItemsService.create(dto);
  }

  @Get()
  findAll() {
    // List order items.
    return this.orderItemsService.findAll();
  }

  @Get(':id')
  findOne(@Param('id') id: string) {
    // Fetch order item by id.
    return this.orderItemsService.findOne(id);
  }

  @Patch(':id')
  update(@Param('id') id: string, @Body() dto: UpdateOrderItemDto) {
    // Update order item by id.
    return this.orderItemsService.update(id, dto);
  }

  @Delete(':id')
  remove(@Param('id') id: string) {
    // Delete order item by id.
    return this.orderItemsService.remove(id);
  }

  @Post('faker')
  faker(
    @Query('count') count = '30',
    @Query('maxItemsPerOrder') maxItemsPerOrder = '4',
  ) {
    // Generate faker order items.
    return this.orderItemsService.fakerCreate(
      Number(count),
      Number(maxItemsPerOrder),
    );
  }
}
