export class Base64 {
  encode(str: string): string {
    return Buffer.from(str).toString('base64');
  }

  decode(base64: string): string {
    return Buffer.from(base64, 'base64').toString('utf-8');
  }
}