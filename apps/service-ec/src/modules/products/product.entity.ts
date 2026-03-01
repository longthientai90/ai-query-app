import {
  Column,
  CreateDateColumn,
  Entity,
  JoinColumn,
  ManyToOne,
  PrimaryGeneratedColumn,
  UpdateDateColumn,
} from 'typeorm';
import { Category } from '../categories/category.entity';

@Entity({ name: 'products' })
export class Product {
  @PrimaryGeneratedColumn({ type: 'bigint' })
  id!: string;

  @Column({ length: 255 })
  name!: string;

  @Column({ name: 'category_id', type: 'bigint', nullable: true })
  categoryId?: string | null;

  @ManyToOne(() => Category, (category) => category.products, {
    nullable: true,
    onDelete: 'SET NULL',
  })
  @JoinColumn({ name: 'category_id' })
  category?: Category | null;

  @Column({ type: 'varchar', length: 255, nullable: true })
  adjective?: string | null;

  @Column({ type: 'varchar', length: 255, nullable: true })
  material?: string | null;

  @Column({ type: 'numeric', precision: 12, scale: 2 })
  price!: string;

  @Column({ type: 'text', nullable: true })
  description?: string | null;

  @CreateDateColumn({ name: 'created_at', type: 'timestamp' })
  createdAt!: Date;

  @UpdateDateColumn({ name: 'updated_at', type: 'timestamp' })
  updatedAt!: Date;
}
