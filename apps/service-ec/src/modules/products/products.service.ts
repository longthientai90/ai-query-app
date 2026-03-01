import { BadRequestException, Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Product } from './product.entity';
import { Category } from '../categories/category.entity';
import { CreateProductDto, UpdateProductDto } from './product.dto';
import { getFaker } from '../../common/faker';

@Injectable()
export class ProductsService {
  // Handles product CRUD plus faker generation tied to categories.
  constructor(
    @InjectRepository(Product)
    private readonly productRepository: Repository<Product>,
    @InjectRepository(Category)
    private readonly categoryRepository: Repository<Category>,
  ) { }

  async create(dto: CreateProductDto) {
    // Validate category (if provided) then persist a new product.
    let categoryId: string | null | undefined = dto.categoryId;
    if (categoryId) {
      const category = await this.categoryRepository.findOne({
        where: { id: categoryId },
      });
      if (!category) {
        throw new BadRequestException('Category not found');
      }
    }

    const product = this.productRepository.create({
      name: dto.name,
      categoryId: categoryId ?? null,
      adjective: dto.adjective ?? null,
      material: dto.material ?? null,
      price: dto.price.toFixed(2),
      description: dto.description ?? null,
    });

    return this.productRepository.save(product);
  }

  async findAll() {
    // List products with category relation.
    return this.productRepository.find({
      relations: { category: true },
      order: { createdAt: 'DESC' },
    });
  }

  async findOne(id: string) {
    // Fetch a single product by id.
    const product = await this.productRepository.findOne({
      where: { id },
      relations: { category: true },
    });
    if (!product) {
      throw new NotFoundException('Product not found');
    }
    return product;
  }

  async update(id: string, dto: UpdateProductDto) {
    // Patch product fields and persist.
    const product = await this.findOne(id);

    if (dto.categoryId !== undefined) {
      if (dto.categoryId) {
        const category = await this.categoryRepository.findOne({
          where: { id: dto.categoryId },
        });
        if (!category) {
          throw new BadRequestException('Category not found');
        }
        product.categoryId = dto.categoryId;
      } else {
        product.categoryId = null;
      }
    }

    if (dto.name !== undefined) {
      product.name = dto.name;
    }
    if (dto.adjective !== undefined) {
      product.adjective = dto.adjective ?? null;
    }
    if (dto.material !== undefined) {
      product.material = dto.material ?? null;
    }
    if (dto.price !== undefined) {
      product.price = dto.price.toFixed(2);
    }
    if (dto.description !== undefined) {
      product.description = dto.description ?? null;
    }

    return this.productRepository.save(product);
  }

  async remove(id: string) {
    // Remove product by id.
    const product = await this.findOne(id);
    await this.productRepository.remove(product);
    return product;
  }

  async fakerCreate(count: number) {
    // Generate faker products linked to existing categories.
    const faker = await getFaker();
    const requested = Math.max(1, Math.min(count, 5000));
    const categories = await this.categoryRepository.find({ select: ['id'] });
    if (categories.length === 0) {
      throw new BadRequestException('No categories available for faker products');
    }

    const toCreate = Array.from({ length: requested }).map(() => {
      const category = categories[Math.floor(Math.random() * categories.length)];
      return this.productRepository.create({
        name: faker.commerce.productName(),
        categoryId: category?.id ?? null,
        adjective: faker.commerce.productAdjective(),
        material: faker.commerce.productMaterial(),
        price: Number(faker.commerce.price({ min: 5, max: 5000, dec: 2 })).toFixed(2),
        description: faker.commerce.productDescription(),
      });
    });

    const inserted = await this.productRepository.save(toCreate);
    return {
      requested,
      inserted: inserted.length,
    };
  }
}
