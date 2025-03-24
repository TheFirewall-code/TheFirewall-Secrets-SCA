import { Module } from '@nestjs/common';
import { SsoModule } from './sso/sso.module';
import { ConfigModule } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { SsoConfig } from './sso/entities/sso-config.entity';
import { LoggerModule } from 'nestjs-pino';
import { User } from './user/entities/user.entity';
import { UserModule } from './user/user.module';
import { AuthModule } from './auth/auth.module';
import { EulaModule } from './eula/eula.module';
import { EULA } from './eula/entities/eula.entity';
import { AppController } from './app.controller';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
    }),
    LoggerModule.forRoot(),
    TypeOrmModule.forRoot({
      type: 'postgres',
      host: process.env.DB_HOST,
      port: +process.env.DB_PORT,
      username: process.env.DB_USER,
      password: process.env.DB_PASS,
      database: process.env.DB_NAME,
      entities: [User, SsoConfig, EULA],
      synchronize: process.env.TYPEORM_SYNC === 'true',
      ssl: false,
    }),
    SsoModule,
    UserModule,
    AuthModule,
    EulaModule,
  ],
  controllers: [AppController],
  providers: [],
})
export class AppModule {}
