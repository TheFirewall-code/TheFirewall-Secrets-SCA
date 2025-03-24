import random
import string


def generate_secret(length=32):
    if length <= 0:
        raise ValueError("Length must be a positive integer")

    characters = string.ascii_letters + string.digits
    secret = ''.join(random.choice(characters) for _ in range(length))
    return secret
