import sys
from core import assemble_password, derive_sha256
import argparse
from getpass import getpass
import re
import pyperclip
import time


PUNCTATION = "!@#$%^&*()_+-="

def is_ipv4(site: str) -> bool:
    return bool(re.fullmatch(r"(?<!\d)(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]?|0)(?:\.(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9][0-9]?|0)){3}(?!\d)",site))


def main():
    parser = argparse.ArgumentParser(description="本地密码派生器")
    parser.add_argument("-s", "--site-name", required=True, type=str, help="标识 (如 'google'、'小红书-大号'等)")
    parser.add_argument("-l", "--length", type=int, default=16, help="密码长度 (默认16)")
    parser.add_argument('-f', '--fast', action='store_true', help='启动快速模式，只用填写一次密码和盐')
    parser.add_argument("--no-special", action="store_true", help="不启用特殊字符")
    parser.add_argument("--special-chars", default=PUNCTATION,
                        help="自定义特殊字符，可传入自定义字符集。**请务必牢记**")
    parser.add_argument("--show", action="store_true", help="直接打印密码。**危险！**")
    args = parser.parse_args()

    if args.length < 8:
        print("警告：字符串过短，安全性较低！建议至少设置为8位以上。", file=sys.stderr)

    if args.show:
        print("警告：你选择了打印密码，请注意环境安全！", file=sys.stderr)

    if args.no_special and args.special_chars == PUNCTATION:
        print(f"提示：您禁用了生成特殊符号。", file=sys.stderr)
        args.special_chars = ""
    elif args.no_special and args.special_chars != PUNCTATION:
        print(f"警告：禁用特殊符号与自定义特殊符号矛盾！程序将生成禁用符号的版本。", file=sys.stderr)
        args.special_chars = ""
    elif args.special_chars != PUNCTATION:
        print(f"提示：您自定义了标点符号集，请务必牢记以下自定义内容 {args.special_chars} ", file=sys.stderr)
    else:
        print("提示：您使用了默认符号集。", file=sys.stderr)

    """域名格式的规范化"""
    args.site_name = args.site_name.lower()
    print(f"提示：我们将您输入的标识进行了规范化: {args.site_name}")

    if is_ipv4(args.site_name):
        print(f"提示：您貌似输入了一个ipv4地址作为标识：{args.site_name}。IP一旦变更，密码将无法复现。", file=sys.stderr)

    print(f"为标识 '{args.site_name}' 生成密码...")
    if not args.fast:
        while True:
            master = getpass("请输入主密码：")
            master_confirm = getpass("请再次输入主密码：")
            if master == master_confirm:
                break
            else:
                print("两次输入不一致！", file=sys.stderr)
        while True:
            salt = getpass("请输入盐：")
            salt_confirm = getpass("请再次输入盐：")
            if salt == salt_confirm:
                break
            else:
                print("两次输入不一致！", file=sys.stderr)
    else:
        master = getpass("请输入主密码：")
        salt = getpass("请输入盐：")


    dk = derive_sha256(master, salt, args.site_name)
    del master, salt
    password = bytearray(assemble_password(dk, args.length, args.special_chars).encode())
    del dk

    if args.show:
        print("\n已生成密码：", file=sys.stderr)
        print(password.decode())
        for i in range(len(password)): password[i] = 0
        del password
        print("请及时清空屏幕。", file=sys.stderr)
    else:
        pyperclip.copy(password.decode())
        for i in range(len(password)): password[i] = 0
        del password
        print("\n密码已生成在剪切板，10秒内清除。", file=sys.stderr)
        time.sleep(10)
        print("密码已经被清除。请重新生成。", file=sys.stderr)
        pyperclip.copy("密码已经被清除。请重新生成。")

if __name__ == "__main__":
    main()