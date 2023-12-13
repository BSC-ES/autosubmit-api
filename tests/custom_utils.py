from http import HTTPStatus


def dummy_response(*args, **kwargs):
    return "Hello World!", HTTPStatus.OK


def custom_return_value(value=None):
    def blank_func(*args, **kwargs):
        return value

    return blank_func
