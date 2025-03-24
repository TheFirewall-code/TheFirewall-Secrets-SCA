import { Test, TestingModule } from '@nestjs/testing';
import { EulaController } from './eula.controller';
import { EulaService } from './eula.service';

describe('EulaController', () => {
  let controller: EulaController;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [EulaController],
      providers: [EulaService],
    }).compile();

    controller = module.get<EulaController>(EulaController);
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
  });
});
