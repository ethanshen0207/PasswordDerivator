#!/usr/bin/env python3
import hashlib
import re
import string
import sys


def normalize_site(site: str) -> str:
    return re.sub(r'^https?://([^/?#]+).*', r'\1', site)


def is_ipv4(site: str) -> bool:
    return bool(re.fullmatch(r"(?<!\d)(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]?|0)(?:\.(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]?|0)){3}(?!\d)",site))


def derive_password(
        master_pass,
        salt,
        name,
        length=16,
        symbols=string.punctuation) -> str:
    """
    基于 SHA-256 派生一个站点专属密码。包含：大写字母、小写字母、数字、特殊字符（可选）四种类型。

    Args:
        master_pass: 母密码。
        salt: 盐。
        name: 站点标识，用于区分不同网站。**强烈建议调用前进行标准化清洗**：
            1. 转为小写；
            2. 去除协议头、端口号、路径、查询参数；
            3. 仅保留域名部分（如 example.com）。
            清洗不一致将导致生成完全不同的密码，且无法追溯。
        length: 生成的密码字符串长度，默认为16.可选范围为3（不启用特殊字符）或4（启用）~32.
        symbols: 启用特殊字符。留空使用默认符号集，或传入自定义字符集。**务必牢记自定义字符集**

    Returns:
        生成的密码字符串。
    """
    char_types_needed = 4 if symbols else 3
    total_bytes_needed = length * 4
    # 即total_bytes_needed = (char_types_needed + (length - char_types_needed) + length) * 2
    # 乘2减少模数偏差

    if not isinstance(length, int):
        raise TypeError("长度必须为整数。")

    if length < char_types_needed:
        raise ValueError("非法的长度。")

    raw = f"{name}:{master_pass}".encode("utf-8")
    salt = salt.encode("utf-8")
    iterations = 600000
    dk = hashlib.pbkdf2_hmac("sha256", raw, salt, iterations, dklen=total_bytes_needed)

    type_chars_indices = [int.from_bytes(dk[i:i + 2], byteorder='big') for i in range(0, len(dk), 2)]

    forced_type_pos_list = [i % length for i in type_chars_indices[:char_types_needed]]
    forced_type_pos_list.sort()
    remaining_type_index = [i % char_types_needed for i in type_chars_indices[char_types_needed:len(type_chars_indices) // 2]]
    chars_index = type_chars_indices[len(type_chars_indices) // 2:]

    type_forced_set = set()
    types_list = remaining_type_index
    for i in range(char_types_needed):
        while forced_type_pos_list[i] in type_forced_set:
            forced_type_pos_list[i] = (forced_type_pos_list[i] + 1) % length
        type_forced_set.add(forced_type_pos_list[i])
        types_list.insert(forced_type_pos_list[i], i)
    # print(types_list)

    chars_set = [string.ascii_uppercase, string.ascii_lowercase, string.digits]
    if symbols:
        chars_set.append(symbols)
    derive_result_list = [""] * length
    for i in range(length):
        derive_result_list[i] = chars_set[types_list[i]][chars_index[i] % len(chars_set[types_list[i]])]

    result = "".join(derive_result_list)
    return result


def main():
    import argparse
    from getpass import getpass


    parser = argparse.ArgumentParser(description="本地密码派生器")
    parser.add_argument("-s", "--salt", required=True, help="盐")
    parser.add_argument("-w", "--website", required=True, type=str, help="站点标识 (如 google.com)")
    parser.add_argument("-l", "--length", type=int, default=16, help="密码长度 (默认16)")
    parser.add_argument("--no-special", action="store_true", help="不启用特殊字符")
    parser.add_argument("--special-chars", default=string.punctuation,
                        help="自定义特殊字符，可传入自定义字符集。**请务必牢记**")
    args = parser.parse_args()

    if args.length < 8:
        print("警告：字符串过短，安全性较低！建议至少设置为8位以上。", file=sys.stderr)

    if args.no_special and args.special_chars == string.punctuation:
        print(f"提示：您禁用了生成特殊符号。", file=sys.stderr)
        args.special_chars = ""
    elif args.no_special and args.special_chars != string.punctuation:
        print(f"警告：禁用特殊符号与自定义特殊符号矛盾！程序将生成禁用符号的版本。", file=sys.stderr)
        args.special_chars = ""
    elif args.special_chars != string.punctuation:
        print(f"提示：您自定义了标点符号集，请务必牢记以下自定义内容 {args.special_chars} ", file=sys.stderr)
    else:
        print("提示：您使用了默认符号集。", file=sys.stderr)

    """域名格式的规范化"""
    args.website = args.website.lower()
    args.website = normalize_site(args.website)
    print(f"提示：我们将您输入的网址进行了规范化: {args.website}")

    if is_ipv4(args.website):
        print(f"提示：您貌似输入了一个ipv4地址：{args.website}。IP一旦变更，密码将无法复现。", file=sys.stderr)

    print(f"为站点 '{args.website}' 生成密码...")
    master = getpass("请输入主密码: ")
    confirm = getpass("请再次输入主密码: ")
    if master != confirm:
        print("两次输入不一致！")
        sys.exit(1)

    password = derive_password(
        master_pass=master,
        salt=args.salt,
        name=args.website,
        length=args.length,
        symbols=args.special_chars
    )
    print(f"\n生成的密码: {password}")

if __name__ == "__main__":
    main()