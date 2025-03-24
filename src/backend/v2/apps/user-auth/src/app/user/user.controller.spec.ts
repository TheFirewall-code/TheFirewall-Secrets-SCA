import { Test, TestingModule } from '@nestjs/testing';
import { UserController } from './user.controller';
import { UserService } from './user.service';
import { CreateUserDto } from './dto/create-user.dto';
import { UpdateUserDto } from './dto/update-user.dto';
import { GetUsersQueryDto } from './dto/get-user.dto';
import { UserRole } from '@firewall-backend/enums';
import { Request } from 'express';
import { getLoggerToken } from 'nestjs-pino';
import { JwtService } from '@nestjs/jwt';
import { mockUser } from './mock/user.mock';

describe('UserController', () => {
  const mockUserService = {
    createUser: jest.fn(),
    getAllUsers: jest.fn(),
    getUserById: jest.fn(),
    updateUser: jest.fn(),
    deleteUser: jest.fn(),
  };

  const mockLogger = {
    info: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    debug: jest.fn(),
  };

  let controller: UserController;
  let service: UserService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [UserController],
      providers: [
        {
          provide: UserService,
          useValue: mockUserService,
        },
        {
          provide: getLoggerToken(UserController.name),
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

    controller = module.get<UserController>(UserController);
    service = module.get<UserService>(UserService);
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
  });

  describe('createNewUser', () => {
    it('should create a new user', async () => {
      const createUserDto: CreateUserDto = {
        username: 'test-user',
        userEmail: 'test@example.com',
        password: 'password',
        role: UserRole.User,
        active: true,
      };
      const req = { user: { user_id: 1 } } as Request;

      jest.spyOn(service, 'createUser').mockResolvedValue(mockUser);

      expect(await controller.createNewUser(createUserDto, req)).toEqual(
        mockUser
      );
      expect(service.createUser).toHaveBeenCalledWith(
        createUserDto,
        req.user.user_id
      );
    });
  });

  describe('getUsers', () => {
    it('should return all users', async () => {
      const query: GetUsersQueryDto = {
        username: 'test-user',
        page: 1,
        limit: 10,
      };
      const result = {
        current_page: 1,
        current_limit: 10,
        total_count: 1,
        total_pages: 1,
        data: [mockUser],
      };

      jest.spyOn(service, 'getAllUsers').mockResolvedValue(result);

      expect(await controller.getUsers(query)).toEqual(result);
      expect(service.getAllUsers).toHaveBeenCalledWith(query);
    });
  });

  describe('getSelfUser', () => {
    it('should return the current user', async () => {
      const req = { user: { user_id: 1 } } as Request;

      jest.spyOn(service, 'getUserById').mockResolvedValue(mockUser);

      expect(await controller.getSelfUser(req)).toEqual(mockUser);
      expect(service.getUserById).toHaveBeenCalledWith(req.user.user_id);
    });
  });

  describe('readUser', () => {
    it('should return a user by id', async () => {
      const params = { user_id: 1 };

      jest.spyOn(service, 'getUserById').mockResolvedValue(mockUser);

      expect(await controller.readUser(params)).toEqual(mockUser);
      expect(service.getUserById).toHaveBeenCalledWith(params.user_id);
    });
  });

  describe('updateExistingUser', () => {
    it('should update a user', async () => {
      const params = { user_id: 1 };
      const updateUserDto: UpdateUserDto = { role: UserRole.Admin };
      const req = { user: { user_id: 1 } } as Request;

      jest.spyOn(service, 'updateUser').mockResolvedValue(mockUser);

      expect(
        await controller.updateExistingUser(params, updateUserDto, req)
      ).toEqual(mockUser);
      expect(service.updateUser).toHaveBeenCalledWith(
        params.user_id,
        updateUserDto,
        req.user.user_id
      );
    });
  });

  describe('softDeleteUser', () => {
    it('should soft delete a user', async () => {
      const params = { user_id: 1 };
      const req = { user: { user_id: 1 } } as Request;

      jest.spyOn(service, 'deleteUser').mockResolvedValue(mockUser);

      expect(await controller.softDeleteUser(params, req)).toEqual(mockUser);
      expect(service.deleteUser).toHaveBeenCalledWith(
        params.user_id,
        req.user.user_id
      );
    });
  });
});
