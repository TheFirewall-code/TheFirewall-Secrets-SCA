import {
  Entity,
  Column,
  CreateDateColumn,
  PrimaryGeneratedColumn,
} from 'typeorm';

@Entity({ name: 'eula' })
export class EULA {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ default: false })
  accepted: boolean;

  @CreateDateColumn({ name: 'accepted_at', nullable: true })
  acceptedAt: Date;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;
}
