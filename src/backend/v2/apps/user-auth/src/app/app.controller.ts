import { Controller, Get } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';

@ApiTags('Health')
@Controller()
export class AppController {
  @Get()
  ready() {
    return { status: 'OK' };
  }

  @Get('/health')
  health() {
    return { status: 'OK' };
  }
}
