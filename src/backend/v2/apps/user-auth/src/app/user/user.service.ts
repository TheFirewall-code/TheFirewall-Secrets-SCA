import {
  BadRequestException,
  ConflictException,
  ForbiddenException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { CreateUserDto } from './dto/create-user.dto';
import { UpdateUserDto } from './dto/update-user.dto';
import { GetUsersQueryDto } from './dto/get-user.dto';
import { InjectRepository } from '@nestjs/typeorm';
import { User } from './entities/user.entity';
import { FindManyOptions, Like, Repository } from 'typeorm';
import { InjectPinoLogger, PinoLogger } from 'nestjs-pino';
import { Bcrypt } from '@firewall-backend/utils';
import { PaginationResponseDto } from '@firewall-backend/dto';

@Injectable()
export class UserService {
  constructor(
    @InjectRepository(User)
    private readonly userRepository: Repository<User>,
    @InjectPinoLogger(UserService.name) private readonly logger: PinoLogger
  ) {}

  async createUser(createUserDto: CreateUserDto, currentUserId: number) {
    try {
      this.logger.info({ createUserDto, currentUserId }, 'Creating new user');

      let user = await this.userRepository.findOne({
        where: { username: createUserDto.username },
      });

      if (user) {
        throw new ConflictException('Username already exists');
      }

      user = await this.userRepository.findOne({
        where: { userEmail: createUserDto.userEmail },
      });

      if (user) {
        throw new ConflictException('Email already exists');
      }

      const bcrypt = new Bcrypt();

      user = await this.userRepository.save({
        active: createUserDto.active,
        addedByUid: currentUserId,
        hashedPassword: await bcrypt.hash(createUserDto.password),
        role: createUserDto.role,
        updatedByUid: currentUserId,
        userEmail: createUserDto.userEmail,
        username: createUserDto.username,
      });

      this.logger.info({ user }, 'New User');

      return user;
    } catch (err) {
      this.logger.error(
        { err, createUserDto, currentUserId },
        'Error while creating user'
      );

      if (err?.response?.statusCode) {
        throw err;
      }

      throw new Error('Failed to create user');
    }
  }

  async getAllUsers(
    getUsersQueryDto: GetUsersQueryDto
  ): Promise<PaginationResponseDto<User>> {
    try {
      this.logger.info({ getUsersQueryDto }, 'Get users');

      const { username, page = 1, limit = 10 } = getUsersQueryDto;
      const offset = (+page - 1) * +limit;

      const findOptions: FindManyOptions<User> = {
        skip: offset,
        take: limit,
      };
      if (username) {
        findOptions.where = { username: Like(`%${username}%`) };
      }

      const users = await this.userRepository.find(findOptions);
      const totalCount = await this.userRepository.count();

      this.logger.info({ users, totalCount }, 'Users and Count');

      return {
        current_page: +page,
        current_limit: +limit,
        total_count: totalCount,
        total_pages: Math.ceil(totalCount / +limit),
        data: users,
      };
    } catch (err) {
      this.logger.error({ err, getUsersQueryDto }, 'Error while getting users');

      throw new Error('Failed to get users');
    }
  }

  async getUserById(userId: number) {
    try {
      this.logger.info({ userId }, 'Fetching user');

      const user = await this.userRepository.findOne({
        where: { id: userId },
        relations: ['addedBy', 'updatedBy'],
      });

      this.logger.info({ user }, 'User');

      if (!user) {
        throw new BadRequestException(`User not found with user id: ${userId}`);
      }

      return user;
    } catch (err) {
      this.logger.error({ err, userId }, 'Error while fetching user');

      if (err?.response?.statusCode) {
        throw err;
      }

      throw new Error('Failed to fetch user');
    }
  }

  async updateUser(
    userId: number,
    updateUserDto: UpdateUserDto,
    currentUserId: number
  ): Promise<User> {
    try {
      this.logger.info(
        { userId, updateUserDto, currentUserId },
        'Updating user'
      );

      let user = await this.userRepository.findOne({
        where: { id: userId },
      });

      this.logger.info({ user }, 'User');

      if (!user) {
        throw new BadRequestException(`User not found with user id: ${userId}`);
      }

      user = await this.userRepository.save({
        ...user,
        ...updateUserDto,
        updatedByUid: currentUserId,
      });

      this.logger.info({ user }, 'Updated user');

      return user;
    } catch (err) {
      this.logger.error(
        { err, userId, updateUserDto, currentUserId },
        'Error while updating user'
      );

      if (err?.response?.statusCode) {
        throw err;
      }

      throw new Error('Failed to update user');
    }
  }

  async deleteUser(userId: number, currentUserId: number): Promise<User> {
    try {
      this.logger.info({ userId }, 'Deleting user');

      let user = await this.userRepository.findOne({ where: { id: userId } });

      this.logger.info({ user }, 'User');

      if (!user) {
        throw new NotFoundException(`User not found with user id: ${userId}`);
      }

      if (user.username === 'admin') {
        throw new ForbiddenException('Cannot delete admin user');
      }

      user = await this.userRepository.save({
        ...user,
        active: false,
        updatedByUid: currentUserId,
      });

      this.logger.info({ user }, 'Deleted user');

      return user;
    } catch (err) {
      this.logger.error({ err, userId }, 'Error while deleting user');

      if (err?.response?.statusCode) {
        throw err;
      }

      throw new Error('Failed to delete user');
    }
  }
}
