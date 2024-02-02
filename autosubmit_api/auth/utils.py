from autosubmit_api.config.basicConfig import APIBasicConfig


def validate_client(client_name):
    APIBasicConfig.read()
    for allowed_client in APIBasicConfig.ALLOWED_CLIENTS:
        if (allowed_client == "*") or (allowed_client in client_name):
            return True
    return False
