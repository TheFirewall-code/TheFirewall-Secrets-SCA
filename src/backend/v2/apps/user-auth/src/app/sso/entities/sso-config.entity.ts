import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
  UpdateDateColumn,
  ManyToOne,
  JoinColumn,
} from 'typeorm';
import { User } from '../../user/entities/user.entity';
import { SsoConfigType } from '../enums/sso-config-type.enum';

@Entity({ name: 'sso_config' })
export class SsoConfig {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  name: string;

  @Column({ type: 'enum', enum: SsoConfigType })
  type: SsoConfigType;

  @Column()
  issuer: string;

  @Column({ name: 'authorization_url' })
  authorizationUrl: string;

  @Column({ name: 'token_url' })
  tokenUrl: string;

  @Column({ name: 'user_info_url' })
  userInfoUrl: string;

  @Column({ name: 'jwks_uri', nullable: true })
  jwksUri?: string;

  @Column({ name: 'client_id' })
  clientId: string;

  @Column({ name: 'client_secret' })
  clientSecret: string;

  @Column({ name: 'callback_url' })
  callbackUrl: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;

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
}
