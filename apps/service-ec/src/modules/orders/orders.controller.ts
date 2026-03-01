import { Body, Controller, Delete, Get, Param, Patch, Post, Query } from '@nestjs/common';
import { OrdersService } from './orders.service';
import { CreateOrderDto, UpdateOrderDto } from './order.dto';

@Controller('orders')
export class OrdersController {
  // Exposes HTTP endpoints for order CRUD and faker operations.
  constructor(private readonly ordersService: OrdersService) {}

  @Post()
  create(@Body() dto: CreateOrderDto) {
    // Create a new order.
    return this.ordersService.create(dto);
  }

  @Get()
  findAll() {
    // List orders.
    return this.ordersService.findAll();
  }

  @Get(':id')
  findOne(@Param('id') id: string) {
    // Fetch order by id.
    return this.ordersService.findOne(id);
  }

  @Patch(':id')
  update(@Param('id') id: string, @Body() dto: UpdateOrderDto) {
    // Update order by id.
    return this.ordersService.update(id, dto);
  }

  @Delete(':id')
  remove(@Param('id') id: string) {
    // Delete order by id.
    return this.ordersService.remove(id);
  }

  @Post('faker')
  faker(@Query('count') count = '10') {
    // Generate faker orders.
    return this.ordersService.fakerCreate(Number(count));
  }
}
