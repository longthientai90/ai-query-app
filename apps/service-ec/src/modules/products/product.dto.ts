import {
  IsNumber,
  IsNumberString,
  IsOptional,
  IsString,
  MaxLength,
  Min,
} from 'class-validator';
import { Type } from 'class-transformer';

export class CreateProductDto {
  @IsString()
  @MaxLength(255)
  name!: string;

  @IsOptional()
  @IsNumberString()
  categoryId?: string;

  @IsOptional()
  @IsString()
  @MaxLength(255)
  adjective?: string;

  @IsOptional()
  @IsString()
  @MaxLength(255)
  material?: string;

  @Type(() => Number)
  @IsNumber()
  @Min(0)
  price!: number;

  @IsOptional()
  @IsString()
  @MaxLength(1000)
  description?: string;
}

export class UpdateProductDto {
  @IsOptional()
  @IsString()
  @MaxLength(255)
  name?: string;

  @IsOptional()
  @IsNumberString()
  categoryId?: string;

  @IsOptional()
  @IsString()
  @MaxLength(255)
  adjective?: string;

  @IsOptional()
  @IsString()
  @MaxLength(255)
  material?: string;

  @IsOptional()
  @Type(() => Number)
  @IsNumber()
  @Min(0)
  price?: number;

  @IsOptional()
  @IsString()
  @MaxLength(1000)
  description?: string;
}
