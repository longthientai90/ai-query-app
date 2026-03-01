import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Category } from '../modules/categories/category.entity';
import { Product } from '../modules/products/product.entity';
import { User } from '../modules/users/user.entity';
import { Order } from '../modules/orders/order.entity';
import { OrderItem } from '../modules/order-items/order-item.entity';

// Centralized database configuration.
export const DatabaseModule = TypeOrmModule.forRootAsync({
  imports: [ConfigModule],
  inject: [ConfigService],
  useFactory: (config: ConfigService) => ({
    type: 'postgres',
    host: config.get<string>('DB_HOST'),
    port: Number(config.get<string>('DB_PORT')),
    username: config.get<string>('DB_USER'),
    password: config.get<string>('DB_PASSWORD'),
    database: config.get<string>('DB_NAME'),
    entities: [Category, Product, User, Order, OrderItem],
    synchronize: config.get<string>('DB_SYNC') === 'true',
    logging: config.get<string>('DB_LOGGING') === 'true',
    ssl:
      config.get<string>('DB_SSL') === 'true'
        ? { rejectUnauthorized: false }
        : undefined,
  }),
});
