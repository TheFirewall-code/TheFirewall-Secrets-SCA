import {
  BadRequestException,
  ForbiddenException,
  Injectable,
  NotFoundException,
  UnauthorizedException,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { User } from '../user/entities/user.entity';
import { Repository } from 'typeorm';
import { JwtService } from '@nestjs/jwt';
import { InjectPinoLogger, PinoLogger } from 'nestjs-pino';
import { Bcrypt } from '@firewall-backend/utils';
import { ResetPasswordDto } from './dto/auth.dto';
import { LoginDto } from './dto/auth.dto';
import { EULA } from '../eula/entities/eula.entity';

@Injectable()
export class AuthService {
  constructor(
    @InjectRepository(User)
    private readonly userRepository: Repository<User>,
    @InjectRepository(EULA)
    private readonly eulaRepository: Repository<EULA>,
    private readonly jwtService: JwtService,
    @InjectPinoLogger(AuthService.name) private readonly logger: PinoLogger
  ) {}

  async checkIfFirstLogin() {
    try {
      this.logger.info('Checking if first login');

      const user = await this.userRepository.findOneBy({ username: 'admin' });

      this.logger.info({ user }, 'User');
      if (!user) {
        return false;
      }

      const bcrypt = new Bcrypt();
      return await bcrypt.compare('admin', user.hashedPassword);
    } catch (err) {
      this.logger.error({ err }, 'Error while checking if first login');

      throw new Error('Failed to check if first login');
    }
  }

  async updateUserPassword(
    userId: number,
    newPassword: string,
    currentUserId: number
  ): Promise<User> {
    try {
      this.logger.info(
        { userId, newPassword, currentUserId },
        'Updating user password'
      );

      let user = await this.userRepository.findOneBy({ id: userId });

      this.logger.info({ user }, 'User');
      if (!user) {
        throw new NotFoundException('User not found');
      }

      const bcrypt = new Bcrypt();
      const hashedPassword = await bcrypt.hash(newPassword);

      user = await this.userRepository.save({
        ...user,
        hashedPassword,
        updatedByUid: currentUserId,
      });

      this.logger.info({ user }, 'Updated user');

      return user;
    } catch (err) {
      this.logger.error(
        { err, userId, newPassword, currentUserId },
        'Error while updating user password'
      );

      if (err?.response?.statusCode) {
        throw err;
      }

      throw new Error('Failed to update user password');
    }
  }

  async resetAdminPassword(resetPasswordDto: ResetPasswordDto): Promise<User> {
    try {
      this.logger.info({ resetPasswordDto }, 'Resetting admin password');

      const firstLogin = await this.checkIfFirstLogin();

      this.logger.info({ firstLogin }, 'First login');
      if (!firstLogin) {
        throw new BadRequestException('Admin password already updated');
      }

      let user = await this.userRepository.findOneBy({ username: 'admin' });

      this.logger.info({ user }, 'User');
      if (!user) {
        throw new NotFoundException('User not found');
      }

      user = await this.updateUserPassword(
        user.id,
        resetPasswordDto.newPassword,
        new User().id
      );

      this.logger.info({ user }, 'Updated user');

      return user;
    } catch (err) {
      this.logger.error(
        { err, resetPasswordDto },
        'Error while resetting admin password'
      );

      if (err?.response?.statusCode) {
        throw err;
      }

      throw new Error('Failed to reset admin password');
    }
  }

  async authenticateUser(loginDto: LoginDto) {
    try {
      this.logger.info({ loginDto }, 'Authenticating user');

      const user = await this.userRepository.findOne({
        where: {
          username: loginDto.username,
        },
      });

      this.logger.info({ user }, 'User');
      if (!user) {
        throw new NotFoundException('User not found');
      }

      const bcrypt = new Bcrypt();
      const isPasswordValid = await bcrypt.compare(
        loginDto.password,
        user.hashedPassword
      );

      this.logger.info({ isPasswordValid }, 'Is Password valid');
      if (!isPasswordValid) {
        throw new UnauthorizedException('Incorrect username or password');
      }

      if (!user.active) {
        throw new BadRequestException(
          'Cant login in active user, contact admin'
        );
      }

      const eula = await this.eulaRepository.findOne({ where: { id: 1 } });

      if (!eula.accepted) {
        throw new ForbiddenException('EULA is not accepted');
      }

      const payload = {
        user_id: user.id,
        username: user.username,
        role: user.role,
      };

      this.logger.info({ payload }, 'Payload');

      return {
        access_token: await this.jwtService.signAsync(payload),
      };
    } catch (err) {
      this.logger.error({ err, loginDto }, 'Error while authenticating user');

      if (err?.response?.statusCode) {
        throw err;
      }

      throw new Error('Failed to authenticate user');
    }
  }

  async resetPassword(
    userId: number,
    resetPasswordDto: ResetPasswordDto,
    currentUserId: number
  ): Promise<User> {
    try {
      this.logger.info({ userId, resetPasswordDto }, 'Resetting user password');

      let user = await this.userRepository.findOneBy({ id: userId });

      this.logger.info({ user }, 'User');
      if (!user) {
        throw new NotFoundException('User not found');
      }

      user = await this.updateUserPassword(
        user.id,
        resetPasswordDto.newPassword,
        currentUserId
      );

      this.logger.info({ user }, 'Updated user');

      return user;
    } catch (err) {
      this.logger.error(
        { err, userId, resetPasswordDto },
        'Error while resetting user password'
      );

      if (err?.response?.statusCode) {
        throw err;
      }

      throw new Error('Failed to reset user password');
    }
  }
}
