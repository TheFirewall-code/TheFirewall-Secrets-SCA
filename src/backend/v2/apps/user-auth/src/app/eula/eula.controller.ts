import { Controller, Get, Post, Body } from '@nestjs/common';
import { EulaService } from './eula.service';
import { AcceptEulaDto } from './dto/accept-eula.dto';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';

@ApiBearerAuth()
@ApiTags('EULA')
@Controller('eula')
export class EulaController {
  constructor(private readonly eulaService: EulaService) {}

  @Post()
  acceptEula(@Body() acceptEulaDto: AcceptEulaDto) {
    return this.eulaService.acceptEula(acceptEulaDto);
  }

  @Get()
  getEula() {
    return this.eulaService.getEula();
  }
}
