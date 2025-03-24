import { Test, TestingModule } from '@nestjs/testing';
import { EulaService } from './eula.service';

describe('EulaService', () => {
  let service: EulaService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [EulaService],
    }).compile();

    service = module.get<EulaService>(EulaService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });
});
