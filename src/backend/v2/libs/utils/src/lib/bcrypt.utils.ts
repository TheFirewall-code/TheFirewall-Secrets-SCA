import * as bcrypt from 'bcryptjs';

export class Bcrypt {
  async hash(str: string): Promise<string> {
    const saltRounds = process.env['BCRYPT_SALT_ROUNDS']
      ? parseInt(process.env['BCRYPT_SALT_ROUNDS'])
      : 11;
    return await bcrypt.hash(str, saltRounds);
  }

  async compare(str: string, hash: string): Promise<boolean> {
    return await bcrypt.compare(str, hash);
  }
}
