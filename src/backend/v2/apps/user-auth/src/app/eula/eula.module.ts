import { Module } from '@nestjs/common';
import { EulaService } from './eula.service';
import { EulaController } from './eula.controller';
import { defaultModuleImports } from '@firewall-backend/utils';
import { TypeOrmModule } from '@nestjs/typeorm';
import { EULA } from './entities/eula.entity';

@Module({
  imports: [...defaultModuleImports(), TypeOrmModule.forFeature([EULA])],
  controllers: [EulaController],
  providers: [EulaService],
})
export class EulaModule {}
