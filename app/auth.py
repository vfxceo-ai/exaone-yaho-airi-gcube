import hmac


def is_authorized(api_key: str, authorization: str | None) -> bool:
    if authorization is None:
        return False

    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token:
        return False

    return hmac.compare_digest(api_key, token)
