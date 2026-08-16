#!/usr/bin/env python3
"""Compile the simplified .po catalogs under locale/ into binary GNU .mo files.

Usage: python compile_locale.py
"""
import os
import re
import struct

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCALE_DIR = os.path.join(BASE_DIR, "src", "passderive", "locale")

MAGIC = 0x950412DE

HEADER = (
    "Project-Id-Version: passderive 2.1.0a0\n"
    "Content-Type: text/plain; charset=UTF-8\n"
    "Content-Transfer-Encoding: 8bit\n"
)

ENTRY_RE = re.compile(r'msgid "((?:[^"\\]|\\.)*)"\s*\nmsgstr "((?:[^"\\]|\\.)*)"')


def unescape(value):
    mapping = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}
    out = []
    i = 0
    while i < len(value):
        char = value[i]
        if char == "\\" and i + 1 < len(value):
            out.append(mapping.get(value[i + 1], value[i + 1]))
            i += 2
        else:
            out.append(char)
            i += 1
    return "".join(out)


def parse_po(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    entries = []
    for match in ENTRY_RE.finditer(text):
        entries.append((unescape(match.group(1)), unescape(match.group(2))))
    return entries


def compile_mo(po_path):
    entries = parse_po(po_path)
    entries = [("", HEADER)] + entries
    entries.sort(key=lambda item: item[0].encode("utf-8"))

    count = len(entries)
    header_size = 28
    original_table = header_size
    translated_table = header_size + count * 8
    data_offset = header_size + count * 16

    original = []
    translated = []
    payload = bytearray()
    offset = data_offset

    for msgid, _msgstr in entries:
        data = msgid.encode("utf-8") + b"\x00"
        original.append((len(msgid.encode("utf-8")), offset))
        payload += data
        offset += len(data)

    for _msgid, msgstr in entries:
        data = msgstr.encode("utf-8") + b"\x00"
        translated.append((len(msgstr.encode("utf-8")), offset))
        payload += data
        offset += len(data)

    buffer = bytearray()
    buffer += struct.pack("<7I", MAGIC, 0, count, original_table, translated_table, 0, 0)
    for length, off in original:
        buffer += struct.pack("<2I", length, off)
    for length, off in translated:
        buffer += struct.pack("<2I", length, off)
    buffer += payload

    mo_path = po_path[:-3] + ".mo" if po_path.endswith(".po") else po_path + ".mo"
    with open(mo_path, "wb") as fh:
        fh.write(buffer)
    return mo_path


def main():
    for root, _dirs, files in os.walk(LOCALE_DIR):
        for name in sorted(files):
            if name.endswith(".po"):
                print(f"compiled {os.path.join(root, name)} -> {compile_mo(os.path.join(root, name))}")


if __name__ == "__main__":
    main()
