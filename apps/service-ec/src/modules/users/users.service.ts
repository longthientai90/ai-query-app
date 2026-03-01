import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User } from './user.entity';
import { CreateUserDto, UpdateUserDto } from './user.dto';
import { getFaker } from '../../common/faker';

@Injectable()
export class UsersService {
  // Handles user CRUD and faker generation.
  constructor(
    @InjectRepository(User)
    private readonly userRepository: Repository<User>,
  ) { }

  async create(dto: CreateUserDto) {
    // Build and persist a new user.
    const user = this.userRepository.create({
      email: dto.email,
      passwordHash: dto.passwordHash,
      firstName: dto.firstName ?? null,
      lastName: dto.lastName ?? null,
      phone: dto.phone ?? null,
      isActive: dto.isActive ?? true,
    });
    return this.userRepository.save(user);
  }

  async findAll() {
    // List users ordered by newest first.
    return this.userRepository.find({ order: { createdAt: 'DESC' } });
  }

  async findOne(id: string) {
    // Fetch a user by id.
    const user = await this.userRepository.findOne({ where: { id } });
    if (!user) {
      throw new NotFoundException('User not found');
    }
    return user;
  }

  async update(id: string, dto: UpdateUserDto) {
    // Patch user fields and persist.
    const user = await this.findOne(id);

    if (dto.email !== undefined) {
      user.email = dto.email;
    }
    if (dto.passwordHash !== undefined) {
      user.passwordHash = dto.passwordHash;
    }
    if (dto.firstName !== undefined) {
      user.firstName = dto.firstName ?? null;
    }
    if (dto.lastName !== undefined) {
      user.lastName = dto.lastName ?? null;
    }
    if (dto.phone !== undefined) {
      user.phone = dto.phone ?? null;
    }
    if (dto.isActive !== undefined) {
      user.isActive = dto.isActive;
    }

    return this.userRepository.save(user);
  }

  async remove(id: string) {
    // Remove user by id.
    const user = await this.findOne(id);
    await this.userRepository.remove(user);
    return user;
  }

  async fakerCreate(count: number) {
    // Generate faker users with unique-ish emails.
    const faker = await getFaker();
    const requested = Math.max(1, Math.min(count, 2000));
    const toCreate = Array.from({ length: requested }).map((_, index) =>
      this.userRepository.create({
        email: `user${index + 1}-${faker.string.alphanumeric(6)}@example.com`,
        passwordHash: faker.internet.password(),
        firstName: faker.person.firstName(),
        lastName: faker.person.lastName(),
        phone: faker.phone.number(),
        isActive: faker.helpers.arrayElement([true, false]),
      }),
    );

    const inserted = await this.userRepository.save(toCreate);
    return {
      requested,
      inserted: inserted.length,
    };
  }
}
