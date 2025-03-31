import sys

if __name__ == '__main__':
    if len(sys.argv) > 1:
        print(f'Arguments passed: {sys.argv[1:]}')
    else:
        print('No arguments were passed.')