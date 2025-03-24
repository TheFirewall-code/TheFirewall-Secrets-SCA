import { Module } from '@nestjs/common';
import { SsoService } from './sso.service';
import { SsoController } from './sso.controller';
import { TypeOrmModule } from '@nestjs/typeorm';
import { SsoConfig } from './entities/sso-config.entity';
import { User } from '../user/entities/user.entity';
import { defaultModuleImports } from '@firewall-backend/utils';
import { EULA } from '../eula/entities/eula.entity';

@Module({
  imports: [
    ...defaultModuleImports(),
    TypeOrmModule.forFeature([User, SsoConfig, EULA]),
  ],
  controllers: [SsoController],
  providers: [SsoService],
})
export class SsoModule {}
