import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Category } from './category.entity';
import { CreateCategoryDto, UpdateCategoryDto } from './category.dto';
import { getFaker } from '../../common/faker';

@Injectable()
export class CategoriesService {
  // Handles persistence logic for category CRUD and faker generation.
  constructor(
    @InjectRepository(Category)
    private readonly categoryRepository: Repository<Category>,
  ) {}

  async create(dto: CreateCategoryDto) {
    // Build and persist a new category from DTO payload.
    const category = this.categoryRepository.create(dto);
    return this.categoryRepository.save(category);
  }

  async findAll() {
    // Return categories ordered by newest first.
    return this.categoryRepository.find({
      order: { createdAt: 'DESC' },
    });
  }

  async findOne(id: string) {
    // Fetch a category by primary key.
    const category = await this.categoryRepository.findOne({ where: { id } });
    if (!category) {
      throw new NotFoundException('Category not found');
    }
    return category;
  }

  async update(id: string, dto: UpdateCategoryDto) {
    // Patch and persist category data.
    const category = await this.findOne(id);
    Object.assign(category, dto);
    return this.categoryRepository.save(category);
  }

  async remove(id: string) {
    // Remove a category from the database.
    const category = await this.findOne(id);
    await this.categoryRepository.remove(category);
    return category;
  }

  async fakerCreate(count: number) {
    // Generate faker categories while avoiding duplicate names.
    const faker = await getFaker();
    const requested = Math.max(1, Math.min(count, 200));
    const existing = await this.categoryRepository.find({ select: ['name'] });
    const existingNames = new Set(existing.map((item) => item.name));

    const toCreate: Category[] = [];
    const maxAttempts = requested * 5;
    let attempts = 0;

    while (toCreate.length < requested && attempts < maxAttempts) {
      attempts += 1;
      const name = faker.commerce.department();
      if (existingNames.has(name)) {
        continue;
      }
      existingNames.add(name);
      toCreate.push(
        this.categoryRepository.create({
          name,
          description: faker.commerce.productDescription(),
        }),
      );
    }

    if (toCreate.length === 0) {
      return {
        requested,
        inserted: 0,
        skippedExisting: requested,
      };
    }

    const inserted = await this.categoryRepository.save(toCreate);
    return {
      requested,
      inserted: inserted.length,
      skippedExisting: requested - inserted.length,
    };
  }
}
