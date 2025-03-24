import { Test, TestingModule } from '@nestjs/testing';
import { UserService } from './user.service';
import { getRepositoryToken } from '@nestjs/typeorm';
import { User } from './entities/user.entity';
import { Repository } from 'typeorm';
import { getLoggerToken } from 'nestjs-pino';
import { CreateUserDto } from './dto/create-user.dto';
import { UpdateUserDto } from './dto/update-user.dto';
import { GetUsersQueryDto } from './dto/get-user.dto';
import { UserRole } from '@firewall-backend/enums';
import { Bcrypt } from '@firewall-backend/utils';
import { JwtService } from '@nestjs/jwt';
import {
  BadRequestException,
  ConflictException,
  ForbiddenException,
  NotFoundException,
} from '@nestjs/common';
import { mockUser } from './mock/user.mock';

describe('UserService', () => {
  const mockLogger = {
    info: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    debug: jest.fn(),
  };

  const mockUserRepository = {
    findOne: jest.fn().mockImplementation(() => mockUser),
    findOneBy: jest.fn().mockImplementation(() => mockUser),
    save: jest.fn().mockImplementation(() => mockUser),
    find: jest.fn().mockImplementation(() => [mockUser]),
    count: jest.fn().mockImplementation(() => 1),
  };

  let service: UserService;
  let userRepository: Repository<User>;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        UserService,
        {
          provide: getRepositoryToken(User),
          useValue: mockUserRepository,
        },
        {
          provide: getLoggerToken(UserService.name),
          useValue: mockLogger,
        },
        {
          provide: JwtService,
          useValue: {
            sign: jest.fn(),
            verify: jest.fn(),
          },
        },
      ],
    }).compile();

    service = module.get<UserService>(UserService);
    userRepository = module.get<Repository<User>>(getRepositoryToken(User));
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });

  describe('createUser', () => {
    it('should create a new user', async () => {
      const createUserDto: CreateUserDto = {
        username: 'test-user',
        userEmail: 'test@example.com',
        password: 'password',
        role: UserRole.User,
        active: true,
      };
      const currentUserId = 1;
      const hashedPassword = 'hashed_password';

      jest.spyOn(userRepository, 'findOne').mockResolvedValueOnce(null);
      jest.spyOn(userRepository, 'findOne').mockResolvedValueOnce(null);
      jest.spyOn(Bcrypt.prototype, 'hash').mockResolvedValue(hashedPassword);
      jest.spyOn(userRepository, 'save').mockResolvedValue(mockUser);

      expect(await service.createUser(createUserDto, currentUserId)).toEqual(
        mockUser
      );
      expect(userRepository.findOne).toHaveBeenCalledTimes(2);
      expect(Bcrypt.prototype.hash).toHaveBeenCalledWith(
        createUserDto.password
      );
      expect(userRepository.save).toHaveBeenCalledWith({
        active: createUserDto.active,
        addedByUid: currentUserId,
        hashedPassword,
        role: createUserDto.role,
        updatedByUid: currentUserId,
        userEmail: createUserDto.userEmail,
        username: createUserDto.username,
      });
    });

    it('should throw ConflictException if username already exists', async () => {
      const createUserDto: CreateUserDto = {
        username: 'test-user',
        userEmail: 'test@example.com',
        password: 'password',
        role: UserRole.User,
        active: true,
      };
      const currentUserId = 1;

      jest.spyOn(userRepository, 'findOne').mockResolvedValueOnce(mockUser);

      await expect(
        service.createUser(createUserDto, currentUserId)
      ).rejects.toThrow(ConflictException);
      expect(userRepository.findOne).toHaveBeenCalledWith({
        where: { username: createUserDto.username },
      });
    });

    it('should throw ConflictException if email already exists', async () => {
      const createUserDto: CreateUserDto = {
        username: 'test-user',
        userEmail: 'test-user@example.com',
        password: 'password',
        role: UserRole.User,
        active: true,
      };
      const currentUserId = 1;

      jest.spyOn(userRepository, 'findOne').mockResolvedValueOnce(null);
      jest.spyOn(userRepository, 'findOne').mockResolvedValueOnce(mockUser);

      await expect(
        service.createUser(createUserDto, currentUserId)
      ).rejects.toThrow(ConflictException);
    });
  });

  describe('getAllUsers', () => {
    it('should return all users', async () => {
      const getUsersQueryDto: GetUsersQueryDto = {
        username: 'test-user',
        page: 1,
        limit: 10,
      };
      const totalCount = 1;

      jest.spyOn(userRepository, 'find').mockResolvedValue([mockUser]);
      jest.spyOn(userRepository, 'count').mockResolvedValue(totalCount);

      expect(await service.getAllUsers(getUsersQueryDto)).toEqual({
        current_page: 1,
        current_limit: 10,
        total_count: totalCount,
        total_pages: 1,
        data: [mockUser],
      });
      expect(userRepository.count).toHaveBeenCalled();
    });
  });

  describe('getUserById', () => {
    it('should return a user by id', async () => {
      const userId = 1;

      jest.spyOn(userRepository, 'findOne').mockResolvedValue(mockUser);

      expect(await service.getUserById(userId)).toEqual(mockUser);
    });

    it('should throw BadRequestException if user not found', async () => {
      const userId = 1;

      jest.spyOn(userRepository, 'findOne').mockResolvedValue(null);

      await expect(service.getUserById(userId)).rejects.toThrow(
        BadRequestException
      );
      expect(userRepository.findOne).toHaveBeenCalledWith({
        where: { id: userId },
        relations: ['addedBy', 'updatedBy'],
      });
    });
  });

  describe('updateUser', () => {
    it('should update a user', async () => {
      const userId = 1;
      const updateUserDto: UpdateUserDto = { role: UserRole.User };
      const currentUserId = 1;
      const updatedUser = { ...mockUser, role: UserRole.User };

      jest.spyOn(userRepository, 'findOne').mockResolvedValue(mockUser);
      jest.spyOn(userRepository, 'save').mockResolvedValue(updatedUser);

      expect(
        await service.updateUser(userId, updateUserDto, currentUserId)
      ).toEqual(updatedUser);
    });

    it('should throw BadRequestException if user not found', async () => {
      const userId = 1;
      const updateUserDto: UpdateUserDto = { role: UserRole.User };
      const currentUserId = 1;

      jest.spyOn(userRepository, 'findOne').mockResolvedValue(null);

      await expect(
        service.updateUser(userId, updateUserDto, currentUserId)
      ).rejects.toThrow(BadRequestException);
      expect(userRepository.findOne).toHaveBeenCalledWith({
        where: { id: userId },
      });
    });
  });

  describe('deleteUser', () => {
    it('should soft delete a user', async () => {
      const userId = 1;
      const currentUserId = 1;
      const deletedUser = { ...mockUser, active: false };

      jest.spyOn(userRepository, 'findOne').mockResolvedValue(mockUser);
      jest.spyOn(userRepository, 'save').mockResolvedValue(deletedUser);

      expect(await service.deleteUser(userId, currentUserId)).toEqual(
        deletedUser
      );
      expect(userRepository.findOne).toHaveBeenCalledWith({
        where: { id: userId },
      });
    });

    it('should throw NotFoundException if user not found', async () => {
      const userId = 1;
      const currentUserId = 1;

      jest.spyOn(userRepository, 'findOne').mockResolvedValue(null);

      await expect(service.deleteUser(userId, currentUserId)).rejects.toThrow(
        NotFoundException
      );
      expect(userRepository.findOne).toHaveBeenCalledWith({
        where: { id: userId },
      });
    });

    it('should throw ForbiddenException if trying to delete admin user', async () => {
      const userId = 1;
      const currentUserId = 1;
      const user = {
        ...mockUser,
        username: 'admin',
      };

      jest.spyOn(userRepository, 'findOne').mockResolvedValue(user);

      await expect(service.deleteUser(userId, currentUserId)).rejects.toThrow(
        ForbiddenException
      );
      expect(userRepository.findOne).toHaveBeenCalledWith({
        where: { id: userId },
      });
    });
  });
});
