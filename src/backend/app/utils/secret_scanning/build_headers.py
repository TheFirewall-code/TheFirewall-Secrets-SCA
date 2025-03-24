from app.utils.encoding_base_64 import encode_basic_token


def build_headers(vc_type, access_token):
    if vc_type == 'github':
        return {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    elif vc_type == 'bitbucket':
        return {
            'Authorization': f"Basic {encode_basic_token(access_token)}",
            'Accept': 'application/json'
        }
    elif vc_type == 'gitlab':
        return {
            'PRIVATE-TOKEN': access_token,
            'Accept': 'application/json'
        }
    return {}
