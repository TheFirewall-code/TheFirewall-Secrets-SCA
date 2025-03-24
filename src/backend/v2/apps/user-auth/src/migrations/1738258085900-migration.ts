import { MigrationInterface, QueryRunner } from 'typeorm';

export class Migration1738258085900 implements MigrationInterface {
  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                hashed_password VARCHAR(255),
                role VARCHAR(255) DEFAULT 'user' NOT NULL,
                user_email VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                added_by_uid INTEGER,
                updated_by_uid INTEGER,
                active BOOLEAN DEFAULT TRUE NOT NULL,
                CONSTRAINT fk_added_by FOREIGN KEY (added_by_uid) REFERENCES users(id),
                CONSTRAINT fk_updated_by FOREIGN KEY (updated_by_uid) REFERENCES users(id)
            );
        `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`DROP TABLE users;`);
  }
}
