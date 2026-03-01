import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { appConfig } from './configs/app.config';
import { validateEnv } from './configs/env.validation';

async function bootstrap() {
  // Validate environment variables before app starts.
  validateEnv();
  const app = await NestFactory.create(AppModule);
  // Prefix all routes with /api.
  app.setGlobalPrefix('api');
  // Enforce DTO validation for all incoming requests.
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      transform: true,
      forbidNonWhitelisted: true,
    }),
  );
  // Use centralized app config.
  await app.listen(appConfig.port);
}

bootstrap();
