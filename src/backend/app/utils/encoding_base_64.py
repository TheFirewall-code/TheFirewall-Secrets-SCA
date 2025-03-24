import base64


def encode_basic_token(token: str) -> str:
    return base64.b64encode(token.encode('utf-8')).decode('utf-8')
