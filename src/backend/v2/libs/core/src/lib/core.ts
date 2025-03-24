import { NestFactory } from '@nestjs/core';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { Logger as PinoLogger } from 'nestjs-pino';
import { Logger, ValidationPipe } from '@nestjs/common';

/**
 * Optional config interface for customizing the swagger or other aspects.
 * Extend this as needed (e.g., adding 'title', 'description', etc.).
 */
export interface BootstrapOptions {
  swagger?: {
    title?: string;
    description?: string;
    version?: string;
    servers?: string[];
    enableBearerAuth?: boolean;
    path?: string; // e.g., '/swagger'
  };
  port?: number;
  globalPrefix?: string;
}

/**
 * Core bootstrap function for any NestJS application.
 *
 * @param module - The root application module (e.g., AppModule).
 * @param options - Optional config for swagger or other overrides.
 */
export async function bootstrapCore(module: any, options?: BootstrapOptions) {
  // Create the NestJS application
  const app = await NestFactory.create(module);

  // Adding validation pipe
  app.useGlobalPipes(
    new ValidationPipe({
      transform: true,
      whitelist: true,
      forbidNonWhitelisted: true,
      transformOptions: {
        enableImplicitConversion: true, // Enable automatic conversion
      },
    })
  );

  // Use the Pino logger
  app.useLogger(app.get(PinoLogger));

  // Enable CORS from all origins
  app.enableCors();

  // Determine port
  const port = parseInt(process.env['PORT'] || '3000');

  // Set global prefix
  const globalPrefix = `v2/${options?.globalPrefix ?? ''}`;
  app.setGlobalPrefix(globalPrefix);

  // Setup default swagger config
  const defaultTitle = options?.swagger?.title ?? 'API';
  const defaultDescription = options?.swagger?.description ?? 'API Description';
  const defaultVersion = options?.swagger?.version ?? '1.0';
  const defaultServers = options?.swagger?.servers ?? ['/'];
  const defaultSwaggerPath = `${globalPrefix}/${
    options?.swagger?.path ?? 'swagger'
  }`;

  // Build swagger config
  const builder = new DocumentBuilder()
    .setTitle(defaultTitle)
    .setDescription(defaultDescription)
    .setVersion(defaultVersion);
  // Add servers
  for (const server of defaultServers) {
    builder.addServer(server);
  }
  // Optionally add BearerAuth
  if (options?.swagger?.enableBearerAuth) {
    builder.addBearerAuth();
  }

  const swaggerConfig = builder.build();
  const document = SwaggerModule.createDocument(app, swaggerConfig);
  SwaggerModule.setup(defaultSwaggerPath, app, document);

  // Start listening
  await app.listen(port);
  Logger.log(`🚀 Application is running on: http://localhost:${port}`);
  Logger.log(
    `🚀 Swagger is running on: http://localhost:${port}/${defaultSwaggerPath}`
  );
}
