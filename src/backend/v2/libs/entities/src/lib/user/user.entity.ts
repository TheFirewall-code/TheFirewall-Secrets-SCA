import { UserRole } from '@firewall-backend/enums';
import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
  UpdateDateColumn,
  ManyToOne,
  JoinColumn,
} from 'typeorm';

@Entity('users')
export class User {
  @PrimaryGeneratedColumn()
  id!: number;

  @Column({ unique: true })
  username!: string;

  @Column({ name: 'hashed_password', nullable: true })
  hashedPassword!: string;

  @Column({ type: 'enum', enum: UserRole, default: UserRole.User })
  role!: UserRole;

  @Column({ name: 'user_email', unique: true })
  userEmail!: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt!: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt!: Date;

  @Column({ name: 'added_by_uid', nullable: true })
  addedByUid?: number;

  @ManyToOne(() => User)
  @JoinColumn({ name: 'added_by_uid' })
  addedBy?: User;

  @Column({ name: 'updated_by_uid', nullable: true })
  updatedByUid?: number;

  @ManyToOne(() => User)
  @JoinColumn({ name: 'updated_by_uid' })
  updatedBy?: User;

  @Column({ default: true })
  active!: boolean;
}
