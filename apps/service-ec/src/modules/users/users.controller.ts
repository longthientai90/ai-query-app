import { Body, Controller, Delete, Get, Param, Patch, Post, Query } from '@nestjs/common';
import { UsersService } from './users.service';
import { CreateUserDto, UpdateUserDto } from './user.dto';

@Controller('users')
export class UsersController {
  // Exposes HTTP endpoints for user CRUD and faker operations.
  constructor(private readonly usersService: UsersService) {}

  @Post()
  create(@Body() dto: CreateUserDto) {
    // Create a new user.
    return this.usersService.create(dto);
  }

  @Get()
  findAll() {
    // List users.
    return this.usersService.findAll();
  }

  @Get(':id')
  findOne(@Param('id') id: string) {
    // Fetch user by id.
    return this.usersService.findOne(id);
  }

  @Patch(':id')
  update(@Param('id') id: string, @Body() dto: UpdateUserDto) {
    // Update user by id.
    return this.usersService.update(id, dto);
  }

  @Delete(':id')
  remove(@Param('id') id: string) {
    // Delete user by id.
    return this.usersService.remove(id);
  }

  @Post('faker')
  faker(@Query('count') count = '20') {
    // Generate faker users.
    return this.usersService.fakerCreate(Number(count));
  }
}
