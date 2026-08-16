#!/usr/bin/env python3
import hashlib
import string
import hmac


def derive_sha256(master_pass: str, salt: str, name: str, iterations: int = 600000, length: int = 256) -> bytes:
    raw = bytearray(f"{len(name)}:{name}:{len(master_pass)}:{master_pass}".encode("utf-8"))
    salt = bytearray(salt.encode("utf-8"))
    try:
        return hashlib.pbkdf2_hmac("sha256", raw, salt, iterations, dklen=length)
    finally:
        for i in range(len(raw)): raw[i] = 0
        for i in range(len(salt)): salt[i] = 0
        del raw, salt


def assemble_password(seed: bytes,
                      length: int = 16,
                      symbols: str = "!@#$%^&*()_+-=") -> str:

    def hmac_new(key: bytes, counter: int):
        return hmac.new(key, f"counter:{counter}".encode("utf-8"), hashlib.sha256).digest()

    chars_set = [string.ascii_uppercase, string.ascii_lowercase, string.digits]
    if symbols:
        chars_set.append(symbols)
    needed_char_types = len(chars_set)

    if type(length) is not int:
        raise TypeError("长度必须为整数。")

    if length < needed_char_types:
        raise ValueError("非法的长度。")

    counter = 0
    type_forced_chars_pos = {}
    bytes_iter = iter(hmac_new(seed, counter))

    def get_chars(set_len: int) -> int:
        nonlocal bytes_iter, counter
        limit = 256 - (256 % set_len)
        while True:
            try:
                b = next(bytes_iter)
                if b < limit:
                    return int(b) % set_len
            except StopIteration:
                counter += 1
                bytes_iter = iter(hmac_new(seed, counter))

    while len(type_forced_chars_pos) < needed_char_types:
        next_pos = get_chars(length)
        next_type = get_chars(needed_char_types)
        if (next_pos not in type_forced_chars_pos.keys()) and (next_type not in type_forced_chars_pos.values()):
            type_forced_chars_pos[next_pos] = next_type
    # print(type_forced_chars_pos)

    type_list = [get_chars(needed_char_types) for _ in range(length)]
    for i, j in type_forced_chars_pos.items():
        type_list[i] = j

    result_list = [chars_set[type_list[i]][get_chars(len(chars_set[type_list[i]]))] for i in range(length)]

    result = "".join(result_list)
    return result


if __name__ == '__main__':
    dk = derive_sha256("minlen", "minsalt", "a.b.c")
    print(dk)
    print(assemble_password(dk, 4, symbols="!@"))