import { UserRole } from '@firewall-backend/enums';
import { User } from '../entities/user.entity';

export const mockUser: User = {
  id: 1,
  username: 'test-user',
  hashedPassword: 'hashed-password',
  role: UserRole.User,
  userEmail: 'testuser@example.com',
  createdAt: new Date(),
  updatedAt: new Date(),
  addedByUid: null,
  addedBy: null,
  updatedByUid: null,
  updatedBy: null,
  active: true,
};
