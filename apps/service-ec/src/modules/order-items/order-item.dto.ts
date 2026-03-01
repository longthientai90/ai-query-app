import {
  IsInt,
  IsNumber,
  IsNumberString,
  IsOptional,
  Min,
} from 'class-validator';
import { Type } from 'class-transformer';

export class CreateOrderItemDto {
  @IsNumberString()
  orderId!: string;

  @IsNumberString()
  productId!: string;

  @Type(() => Number)
  @IsInt()
  @Min(1)
  quantity!: number;

  @Type(() => Number)
  @IsNumber()
  @Min(0)
  unitPrice!: number;
}

export class UpdateOrderItemDto {
  @IsOptional()
  @IsNumberString()
  orderId?: string;

  @IsOptional()
  @IsNumberString()
  productId?: string;

  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  quantity?: number;

  @IsOptional()
  @Type(() => Number)
  @IsNumber()
  @Min(0)
  unitPrice?: number;
}
