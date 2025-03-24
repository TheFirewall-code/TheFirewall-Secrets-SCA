import { Injectable } from '@nestjs/common';
import { AcceptEulaDto } from './dto/accept-eula.dto';
import { InjectRepository } from '@nestjs/typeorm';
import { EULA } from './entities/eula.entity';
import { InjectPinoLogger, PinoLogger } from 'nestjs-pino';
import { Repository } from 'typeorm';

@Injectable()
export class EulaService {
  constructor(
    @InjectRepository(EULA)
    private readonly eulaRepository: Repository<EULA>,
    @InjectPinoLogger(EulaService.name) private readonly logger: PinoLogger
  ) {}

  async acceptEula(acceptEulaDto: AcceptEulaDto) {
    try {
      this.logger.info({ acceptEulaDto }, 'Accepting EULA');

      if (acceptEulaDto.accepted) {
        await this.eulaRepository.query(
          `
          UPDATE eula
          SET accepted = true, accepted_at = CURRENT_TIMESTAMP
          WHERE id = $1
        `,
          [1]
        );
      } else {
        await this.eulaRepository.update({ id: 1 }, { accepted: false });
      }

      return await this.eulaRepository.findOne({ where: { id: 1 } });
    } catch (err) {
      this.logger.error({ acceptEulaDto }, 'Error creating EULA');

      throw err;
    }
  }

  async getEula() {
    try {
      const eula = await this.eulaRepository.findOne({ where: { id: 1 } });

      this.logger.info({ eula }, 'Fetched EULA');

      return eula;
    } catch (err) {
      this.logger.error('Error fetching EULA by user id');

      throw err;
    }
  }
}
