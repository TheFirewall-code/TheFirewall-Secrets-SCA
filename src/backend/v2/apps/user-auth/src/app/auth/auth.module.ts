import { Module } from '@nestjs/common';
import { AuthService } from './auth.service';
import { AuthController } from './auth.controller';
import { defaultModuleImports } from '@firewall-backend/utils';
import { TypeOrmModule } from '@nestjs/typeorm';
import { User } from '../user/entities/user.entity';
import { EULA } from '../eula/entities/eula.entity';

@Module({
  imports: [...defaultModuleImports(), TypeOrmModule.forFeature([User, EULA])],
  controllers: [AuthController],
  providers: [AuthService],
})
export class AuthModule {}
