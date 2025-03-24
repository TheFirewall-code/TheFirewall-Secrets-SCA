import { AppModule } from './app/app.module';
import { bootstrapCore } from '@firewall-backend/core';

async function bootstrap() {
  await bootstrapCore(AppModule, {
    port: parseInt(process.env.PORT) || 4000,
    globalPrefix: 'user-auth',
    swagger: {
      title: 'Auth Service',
      description: 'Provides APIs for SSO login and setup.',
      version: '1.0',
      enableBearerAuth: true,
      path: 'swagger', // final path => /swagger
    },
  });
}

bootstrap();
