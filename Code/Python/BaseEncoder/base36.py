import string

def int_to_base36(num):
    if num == 0:
        return '0'

    base36_chars = string.digits + string.ascii_lowercase  # "0123456789abcdefghijklmnopqrstuvwxyz"
    result = ''
    
    while num:
        num, remainder = divmod(num, 36)
        result = base36_chars[remainder] + result

    return result

# Example
num = 4728210
base36_str = int_to_base36(num)
print(base36_str)  # Output: 21i3v9
