import random as rd

def get_random_vn_name():
    # return random name by combine first, middle and last name
    first_name = ['Khanh', 'Trung', 'Huy', 'Hien', 'Minh', 'Quang', 'Duc', 'Dung', 'Dai', 'Dinh']
    middle_name = ['Trung', 'Huy', 'Hien', 'Minh', 'Quang', 'Duc', 'Dung', 'Dai', 'Dinh']
    last_name = ['Tran', 'Nguyen', 'Le', 'Pham', 'Vo', 'Truong', 'Nguyen', 'Nguyen', 'Nguyen', 'Nguyen']
    return rd.choice(first_name) + ' ' + rd.choice(middle_name) + ' ' + rd.choice(last_name)

def get_random_phone_number():
    # return random phone number (start with zero and 10 digits)
    return '0' + ''.join(rd.sample('0123456789', 9))

def get_domain_by_name(full_name):
    # convert full name to domain: Vu Trung Nghia -> nghiavt, Nguyen Quoc Huy -> huynq, Tran Dan -> dant
    parts = full_name.split(' ')
    return parts[-1] + ''.join([part[0] for part in parts[:-1]])

def get_random_email_by_name(full_name):
    # convert full_name -> domain and add random 4-digit suffix
    domain = get_domain_by_name(full_name)
    return domain + ''.join(rd.sample('0123456789', 4)) + '@gmail.com'

def get_random_city():
    # return random city from 34 cities in Vietnam
    cities = []
    return rd.choice(cities)

def get_random_word():
    # return random word with length 3, 5, 7 by add a consonant first then some pair of (vowel + consonant)
    vowels = "aeuoi"
    consonants = "bcdfghjklmnpqrstvwxyz"
    length = rd.choice([3, 5, 7])
    word = rd.choice(consonants)
    for i in range(length - 1):
        word += rd.choice(vowels) + rd.choice(consonants)
    return word    

def get_random_post_content(min_len, max_len):
    # return random post content by combine random words
    len = rd.randint(min_len, max_len)
    return ' '.join([get_random_word() for _ in range(len)])

def get_username(full_name):
    # convert full name to domain then add random 4-digit suffix
    domain = get_domain_by_name(full_name)
    return domain + ''.join(rd.sample('0123456789', 4))

