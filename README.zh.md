# 本地密码派生工具

[English](README.md)

> **⚠️ 本版本生成的密码与前序版本（`v1.x`）不再兼容！**

一个简单的**确定性密码派生工具**，根据主密码、盐和站点标识生成站点专属的强密码。无需存储密码数据库，只需记住主密码、盐和标识名即可离线复现所有密码。

- 版本：**v2.1-alpha**
  - `alpha` 表示测试版本。
  - `2` 代表核心算法主版本，相同主版本的密码可互相兼容；本版本生成的密码与 `v1.x` **不兼容**。
  - `1` 代表该主版本下的迭代次数。

---

## 特性

- **确定性**：相同输入永远生成相同密码。
- 生成的密码一定包含大写字母、小写字母、数字和特殊字符（除非 `--no-special`）各至少一个。
- **参数预设**（`config`）：以命名预设的方式存储和管理非秘密参数（长度、符号集）。
- **标识规范化**：只做小写化和去首尾空格，不做域名抽取。
- **URL / IP 警告**：对类似 URL 或 IP 的输入给出警告（但不静默改写）。
- **国际化**：内置英文，附带简体中文。
- 剪切板自动复制（10 秒后自动清除），或使用 `--show` 直接打印。

---

## 依赖

- Python 3.8 或更高版本。
- 标准库（`argparse`、`getpass`、`hashlib`、`hmac`、`ipaddress`、`json`、`string`、`sys`、`time` 等）。
- 第三方包：`pyperclip`（版本任意）。

---

## 安装

- 从 PyPI 安装：

  ```bash
  pip install passderive
  ```

- 或从源码构建安装：

  ```bash
  pip install .
  ```


---

## 用法

```bash
passderive derive -s <site> [-n <note>] [-c <id|name>] [-l <length>] [--no-special] [--special-chars <chars>] [-f] [--show]
```

`derive` 是默认子命令，因此简写形式同样有效：

```bash
passderive -s <site> ...
```

从源码目录运行（未安装时）使用 `python -m passderive.cli`。

- `-s` 填写登录站点的标识（如 `google`、`小红书`）。
- `-n` 为可选备注，用于区分同一站点的多个账号（如 `工作`、`小号`），默认无。填写后派生输入变为 `标识|备注`（如 `google|工作`）。

运行后会提示输入主密码和盐。未开启 `-f` 时会各确认一次，不一致则要求重新输入（三次后退出）；开启 `-f` 则无确认环节。

默认情况下生成的密码会复制到剪切板，10 秒后被替换。使用 `--show` 则直接打印密码——请务必在安全环境中使用。

### 参数预设（`config`）

以命名预设的方式管理非秘密参数（长度与符号集）。每个预设带一个数字 ID 和一个名字；默认预设为 ID `0`、名字 `default`（可编辑、不可删除）。预设保存在用户配置目录下的 `config.json` 中（Windows：`%APPDATA%\passderive`；Linux：`~/.config/passderive`；macOS：`~/Library/Application Support/passderive`）；便携版可执行文件则保存在可执行文件旁。可通过环境变量 `PASSDERIVE_CONFIG` 覆盖路径。

```bash
passderive config list
passderive config add <name> [-l <length>] [--no-special | --special-chars <chars>]
passderive config remove <id|name>
passderive config edit <id|name> [-n <name>] [-l <length>] [--no-special | --special-chars <chars>]
```

在 `derive` 中，`-l` 与 `--special-chars` 只作临时覆盖。生效参数按以下优先级解析：

1. 显式的 `-l` / `--special-chars`（临时）
2. 通过 `-c <id|name>` 选中的预设
3. 默认预设（ID `0`）

派生前总会打印实际生效的预设与参数（例如 `使用预设 1 'strong'（长度 20，符号 @#$）`），以便在出错前及时察觉选错。

### 命令行参数（`derive`）

| 参数            | 简写 | 必选 | 说明                                       |
|-----------------|------|------|--------------------------------------------|
| --site-name     | -s   | 是   | 站点标识（如 'google'、'小红书'）。        |
| --notes         | -n   | 否   | 备注，用于区分同一站点的多个账号；默认无。 |
| --config        | -c   | 否   | 要使用的预设 ID 或名字。                   |
| --length        | -l   | 否   | 密码长度（临时覆盖预设）。                 |
| --fast          | -f   | 否   | 快速模式，密码和盐只填写一次。             |
| --no-special    |      | 否   | 不启用特殊字符。                           |
| --special-chars |      | 否   | 自定义特殊字符（临时覆盖预设）。           |
| --show          |      | 否   | 直接打印密码。**危险！**                   |

### 示例

```bash
# 为标识 'google.com' 生成不含符号的密码，快速模式，输出到控制台。
passderive -s google.com -f --no-special --show
```

```text
使用预设 0 'default'（长度 16，无符号）
为标识 'google.com' 生成密码...
请输入主密码：
请输入盐：

已生成密码：
# 你的密码
请及时清空屏幕。
```

```bash
# 为标识 'tiktok-运营号' 生成 20 位、含默认符号集的密码。
passderive -s tiktok-运营号 -l 20
```

---

## 国际化

源代码字符串为英文，简体中文（`zh_CN`）打包在 `locale/` 目录下。界面语言通过环境变量（`LANGUAGE` / `LC_ALL` / `LC_MESSAGES` / `LANG`）选择；未设置时使用系统区域，否则回退为英文。

更新或新增翻译时，编辑 `src/passderive/locale/zh_CN/LC_MESSAGES/passderive.po` 后运行：

```bash
python compile_locale.py
```

---

## 安全须知

- 请记牢标识名，使用容易记住的构造方法。
- 盐必须保密，且区别于他人，与主密码同等对待。
- 使用高熵、易记忆的长主密码，避免常见词汇。
- 离线使用：本工具完全离线运行，不会上传或记录任何数据。请在可信的本地环境中执行。
- 确定性风险：如果主密码和盐同时泄露，所有站点密码可被准确计算。务必保护好这两个秘密。
- 符号集修改警告：如果修改了 `--special-chars`，之后必须使用完全相同的符号集（包括顺序）才能重现密码。

---

## 说明

- 版本 `v2.1-alpha` —— 核心功能已完成，但可能存在边界问题，输入/输出接口仍有调整可能。**不建议用于生产环境。**
- 未经过严格测试。
- 下一步计划：
  - 优化 CLI 使用体验。
  - 引入新的哈希算法。

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源。
