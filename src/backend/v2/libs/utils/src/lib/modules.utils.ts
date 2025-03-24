import { JwtModule } from '@nestjs/jwt';
import { ConfigModule, ConfigService } from '@nestjs/config';

export function defaultModuleImports() {
  return [
    ConfigModule,
    JwtModule.registerAsync({
      imports: [ConfigModule],
      useFactory: async (configService: ConfigService) => ({
        secret: configService.get<string>('SECRET_KEY'),
        signOptions: {
          expiresIn:
            configService.get<string>('ACCESS_TOKEN_EXPIRE_MINUTES') || '1d',
        },
      }),
      inject: [ConfigService],
    }),
  ];
}
