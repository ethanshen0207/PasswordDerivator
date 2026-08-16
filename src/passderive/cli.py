import argparse
import gettext
import ipaddress
import json
import os
import sys
import time
from getpass import getpass

import pyperclip

from .core import assemble_password, derive_sha256

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCALE_DIR = os.path.join(BASE_DIR, "locale")
DOMAIN = "passderive"

_UNSET = object()

DEFAULT_LENGTH = 16
PUNCTATION = "!@#$%^&*()_+-="


def _setup_translation():
    languages = None
    if not any(os.environ.get(v) for v in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")):
        try:
            import locale
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                lang = locale.getdefaultlocale()[0]
            if lang and lang != "C":
                languages = [lang]
        except Exception:
            languages = None
    try:
        return gettext.translation(DOMAIN, localedir=LOCALE_DIR, languages=languages, fallback=True).gettext
    except Exception:
        return gettext.gettext


_ = _setup_translation()


def looks_like_url(site: str) -> bool:
    return "://" in site or site.startswith("www.") or any(c in site for c in "/?#")


def looks_like_ip(site: str) -> bool:
    try:
        ipaddress.ip_address(site)
        return True
    except ValueError:
        return False


def config_path():
    override = os.environ.get("PASSDERIVE_CONFIG")
    if override:
        return override
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "config.json")
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    elif sys.platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    return os.path.join(base, "passderive", "config.json")


class Config:
    def __init__(self, path):
        self.path = path
        self.data = self._load()

    def _load(self):
        data = None
        try:
            with open(self.path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            data = None
        if not data or not isinstance(data.get("presets"), list) or not data["presets"]:
            data = {"version": 1, "presets": [
                {"id": 0, "name": "default", "length": DEFAULT_LENGTH, "special_chars": PUNCTATION}
            ]}
            self._save(data)
        return data

    def _save(self, data):
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def save(self):
        self._save(self.data)

    def presets(self):
        return self.data["presets"]

    def get_preset(self, ref):
        presets = self.data["presets"]
        if ref is None:
            target = 0
        else:
            try:
                target = int(str(ref))
            except (TypeError, ValueError):
                name = str(ref).strip().lower()
                return next((p for p in presets if p["name"].strip().lower() == name), None)
        return next((p for p in presets if p["id"] == target), None)

    def find_by_name(self, name):
        target = name.strip().lower()
        return next((p for p in self.data["presets"] if p["name"].strip().lower() == target), None)

    def next_id(self):
        ids = [p["id"] for p in self.data["presets"]]
        return (max(ids) + 1) if ids else 0


def _validate_name(cfg, name):
    if not name:
        return _("Preset name must not be empty.")
    if name.isdigit():
        return _("Preset name must not be numeric.")
    if name.lower() == "default":
        return _("Preset name 'default' is reserved.")
    if cfg.find_by_name(name) is not None:
        return _("Preset name already exists: {name}").format(name=name)
    return None


def _validate_length(length, special_chars):
    minimum = 4 if special_chars else 3
    if length < minimum:
        return _("Length too short: need at least {minimum} characters.").format(minimum=minimum)
    return None


def cmd_derive(args, cfg):
    if args.show:
        print(_("Warning: You have chosen to print your password; "
                "please ensure you are in a secure environment!"), file=sys.stderr)

    preset = cfg.get_preset(args.preset)
    if preset is None:
        print(_("Preset not found: {ref}").format(ref=args.preset), file=sys.stderr)
        sys.exit(1)

    length = args.length if args.length is not None else preset["length"]

    if args.no_special and args.special_chars is not None:
        print(_("Warning: Disabling special characters conflicts with custom special characters! "
                "The programme will generate a version with special characters disabled."), file=sys.stderr)
        special_chars = ""
    elif args.no_special:
        special_chars = ""
    elif args.special_chars is not None:
        special_chars = args.special_chars
    else:
        special_chars = preset["special_chars"]

    if length < 8:
        print(_("Warning: Your password is too short and is not secure! "
                "We recommend setting it to at least 8 characters."), file=sys.stderr)

    if args.special_chars is not None and args.special_chars not in ("", PUNCTATION):
        print(_("Note: Please ensure you remember your own set of special characters {chars}")
              .format(chars=special_chars), file=sys.stderr)

    if special_chars:
        print(_("Using preset {id} '{name}' (length {length}, symbols {symbols})")
              .format(id=preset["id"], name=preset["name"], length=length, symbols=special_chars), file=sys.stderr)
    else:
        print(_("Using preset {id} '{name}' (length {length}, no symbols)")
              .format(id=preset["id"], name=preset["name"], length=length), file=sys.stderr)

    site = args.site.strip().lower()
    note = args.note.strip().lower()
    identifier = f"{site}|{note}" if note else site

    if looks_like_url(site):
        print(_("Warning: It looks like you have entered a URL as the identifier: {site}. "
                "For stability, please use a short, memorable name instead.")
              .format(site=site), file=sys.stderr)

    if looks_like_ip(site):
        print(_("Warning: It looks like you have entered an IP address as the identifier: {site}. "
                "If the address is private or changes, the password will no longer be retrievable.")
              .format(site=site), file=sys.stderr)

    if site != args.site or note != args.note:
        print(_("Note: We have standardised the identifier you entered: {identifier}")
              .format(identifier=identifier), file=sys.stderr)

    print(_("Generating a password for the identifier “{identifier}”...")
          .format(identifier=identifier), file=sys.stderr)

    if not args.fast:
        attempts = 0
        while True:
            master = getpass(_("Enter the password:"))
            master_confirm = getpass(_("Enter the confirm password:"))
            if master == master_confirm:
                break
            attempts += 1
            if attempts > 2:
                print(_("The programme will exit."), file=sys.stderr)
                sys.exit(1)
            print(_("The two entries do not match!") + " " + _("Try again! {time}/3").format(time=attempts),
                  file=sys.stderr)
        attempts = 0
        while True:
            salt = getpass(_("Enter the salt:"))
            salt_confirm = getpass(_("Enter the confirm salt:"))
            if salt == salt_confirm:
                break
            attempts += 1
            if attempts > 2:
                print(_("The programme will exit."), file=sys.stderr)
                sys.exit(1)
            print(_("The two entries do not match!") + " " + _("Try again! {time}/3").format(time=attempts),
                  file=sys.stderr)
    else:
        master = getpass(_("Enter the password:"))
        salt = getpass(_("Enter the salt:"))

    dk = derive_sha256(master, salt, identifier)
    del master, salt
    password = bytearray(assemble_password(dk, length, special_chars).encode())
    del dk

    if args.show:
        print(_("\nPassword generated:"), file=sys.stderr)
        print(password.decode())
        for i in range(len(password)):
            password[i] = 0
        del password
        print(_("Please clear the screen promptly."), file=sys.stderr)
    else:
        pyperclip.copy(password.decode())
        for i in range(len(password)):
            password[i] = 0
        del password
        print(_("\nThe password has been copied to the clipboard and will be cleared in 10 seconds."),
              file=sys.stderr)
        time.sleep(10)
        print(_("The password has been reset. Please generate a new one."), file=sys.stderr)
        pyperclip.copy(_("The password has been reset. Please generate a new one."))


def cmd_config_add(args, cfg):
    name = args.name.strip()
    length = args.length if args.length is not None else DEFAULT_LENGTH
    if args.no_special:
        special_chars = ""
    elif args.special_chars is not None:
        special_chars = args.special_chars
    else:
        special_chars = PUNCTATION

    err = _validate_name(cfg, name)
    if err:
        print(err, file=sys.stderr)
        sys.exit(1)
    err = _validate_length(length, special_chars)
    if err:
        print(err, file=sys.stderr)
        sys.exit(1)

    preset = {"id": cfg.next_id(), "name": name, "length": length, "special_chars": special_chars}
    cfg.data["presets"].append(preset)
    cfg.save()
    print(_("Added preset {id} '{name}'.").format(id=preset["id"], name=preset["name"]))


def cmd_config_list(args, cfg):
    print(_("Presets:"))
    for p in cfg.presets():
        sym = p["special_chars"] if p["special_chars"] else _("(no symbols)")
        mark = _("(default)") if p["id"] == 0 else ""
        line = f"  {p['id']}  {p['name']}  length={p['length']}  symbols={sym}"
        if mark:
            line += f"  {mark}"
        print(line)


def cmd_config_remove(args, cfg):
    preset = cfg.get_preset(args.ref)
    if preset is None:
        print(_("Preset not found: {ref}").format(ref=args.ref), file=sys.stderr)
        sys.exit(1)
    if preset["id"] == 0:
        print(_("Cannot remove the default preset (0 'default')."), file=sys.stderr)
        sys.exit(1)
    cfg.data["presets"].remove(preset)
    cfg.save()
    print(_("Removed preset {id} '{name}'.").format(id=preset["id"], name=preset["name"]))


def cmd_config_edit(args, cfg):
    preset = cfg.get_preset(args.ref)
    if preset is None:
        print(_("Preset not found: {ref}").format(ref=args.ref), file=sys.stderr)
        sys.exit(1)

    name = args.name.strip() if args.name is not None else None
    length = args.length
    if args.no_special:
        special_chars = ""
    elif args.special_chars is not None:
        special_chars = args.special_chars
    else:
        special_chars = _UNSET

    if name is not None and name != preset["name"]:
        err = _validate_name(cfg, name)
        if err:
            print(err, file=sys.stderr)
            sys.exit(1)

    effective_special = special_chars if special_chars is not _UNSET else preset["special_chars"]
    if length is not None:
        err = _validate_length(length, effective_special)
        if err:
            print(err, file=sys.stderr)
            sys.exit(1)

    if name is not None:
        preset["name"] = name
    if length is not None:
        preset["length"] = length
    if special_chars is not _UNSET:
        preset["special_chars"] = special_chars
    cfg.save()
    print(_("Updated preset {id} '{name}'.").format(id=preset["id"], name=preset["name"]))


def build_parser():
    parser = argparse.ArgumentParser(description=_("local password generator"))
    subparsers = parser.add_subparsers(dest="command")

    p_derive = subparsers.add_parser("derive", help=_("Derive a password."))
    p_derive.add_argument("-s", "--site-name", dest="site", required=True, type=str,
                          help=_("Identifier (e.g. 'google', 'xiaohongshu' etc.)"))
    p_derive.add_argument("-n", "--notes", dest="note", type=str, default="",
                          help=_("Note (e.g. 'work', 'alt account' etc.), none by default"))
    p_derive.add_argument("-c", "--config", dest="preset", type=str, default=None,
                          help=_("Preset ID or name to use."))
    p_derive.add_argument("-l", "--length", type=int, default=None,
                          help=_("Password length (temporary override)."))
    p_derive.add_argument("-f", "--fast", action="store_true",
                          help=_("Fast mode: only enter the password and salt once"))
    p_derive.add_argument("--no-special", action="store_true",
                          help=_("Disable special characters"))
    p_derive.add_argument("--special-chars", default=None,
                          help=_("Custom special characters (temporary override)."))
    p_derive.add_argument("--show", action="store_true",
                          help=_("Print the password directly. **Dangerous!**"))
    p_derive.set_defaults(func=cmd_derive)

    p_config = subparsers.add_parser("config", help=_("Manage the non-secret parameter presets."))
    config_subs = p_config.add_subparsers(dest="config_command")

    p_add = config_subs.add_parser("add", help=_("Add a new preset."))
    p_add.add_argument("name", help=_("Preset name."))
    p_add.add_argument("-l", "--length", type=int, default=None, help=_("Password length."))
    p_add.add_argument("--no-special", action="store_true", help=_("Disable special characters"))
    p_add.add_argument("--special-chars", default=None, help=_("Custom special characters."))
    p_add.set_defaults(func=cmd_config_add)

    p_list = config_subs.add_parser("list", help=_("List all presets."))
    p_list.set_defaults(func=cmd_config_list)

    p_remove = config_subs.add_parser("remove", help=_("Remove a preset."))
    p_remove.add_argument("ref", help=_("Preset ID or name."))
    p_remove.set_defaults(func=cmd_config_remove)

    p_edit = config_subs.add_parser("edit", help=_("Edit an existing preset."))
    p_edit.add_argument("ref", help=_("Preset ID or name."))
    p_edit.add_argument("-n", "--name", default=None, help=_("New preset name."))
    p_edit.add_argument("-l", "--length", type=int, default=None, help=_("Password length."))
    p_edit.add_argument("--no-special", action="store_true", help=_("Disable special characters"))
    p_edit.add_argument("--special-chars", default=None, help=_("Custom special characters."))
    p_edit.set_defaults(func=cmd_config_edit)

    return parser, p_config


def main(argv=None):
    parser, p_config = build_parser()
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        parser.print_help()
        return
    if argv[0] in ("-h", "--help"):
        parser.print_help()
        return
    if argv[0] not in ("derive", "config"):
        argv = ["derive"] + argv

    args = parser.parse_args(argv)

    if args.command == "config" and args.config_command is None:
        p_config.print_help()
        return

    cfg = Config(config_path())
    args.func(args, cfg)


if __name__ == "__main__":
    main()
