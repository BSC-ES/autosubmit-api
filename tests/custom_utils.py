

def custom_return_value(value=None):
    def blank_func(*args, **kwargs):
        return value
    return blank_func