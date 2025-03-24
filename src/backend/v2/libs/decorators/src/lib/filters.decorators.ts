import {
  registerDecorator,
  ValidationOptions,
  ValidationArguments,
} from 'class-validator';

export function IsPrimitive(validationOptions?: ValidationOptions) {
  return function (object: object, propertyName: string) {
    registerDecorator({
      name: 'isPrimitive',
      target: object.constructor,
      propertyName: propertyName,
      options: validationOptions,
      validator: {
        validate(value) {
          if (value === null || value === undefined) {
            return false;
          }

          const type = typeof value;
          // Allow primitives
          if (type === 'string' || type === 'number' || type === 'boolean') {
            return true;
          }

          // Reject all other objects and arrays
          return false;
        },
        defaultMessage(args: ValidationArguments) {
          return `${args.property} must be a string, number, or boolean`;
        },
      },
    });
  };
}
