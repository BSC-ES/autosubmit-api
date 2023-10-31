

def custom_return_value(value):
    def blank_func(*args, **kwargs):
        return value
    return blank_func