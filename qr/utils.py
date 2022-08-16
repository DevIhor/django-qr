import hashlib
import random
import string

import qrcode

from django.conf import settings


def generate_random_string(length):
    """
    Returns a string with `length` characters chosen from `string_set`
    """
    string_set = "".join([string.ascii_letters + string.digits])
    return ''.join(random.choice(string_set) for _ in range(length))


def salted_hash(src_string):
    return hashlib.sha256(":P".join([src_string, settings.SECRET_KEY])).hexdigest()


def make_qr_code(src_string):
    return qrcode.make(src_string, box_size=10, border=1)
