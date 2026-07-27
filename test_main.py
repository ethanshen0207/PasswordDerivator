"""
测试 derive_password 函数的完整脚本。

使用方法：
1. 将本文件放在与 derive_password 所在模块相同的项目中。
2. 在 PyCharm 中直接运行本文件，或使用 pytest 命令行执行。
3. 注意：由于 PBKDF2 迭代次数为 600,000，单次调用较慢，
   运行全部测试可能需要几分钟。建议先运行标记为 slow 的用例，
   或根据需要选择执行。

测试重点：
- 输出长度正确（含边界值 3、4、32）。
- 必须包含大写、小写、数字、特殊字符（若启用）。
- 所有字符均来自允许的字符集。
- 确定性：相同输入产生相同输出。
- 差异输入产生不同输出。
- 边界输入：最小/最大长度、非法类型/值。
- 自定义符号集行为。
"""

import string
import pytest

# 请根据你的实际模块名修改导入路径
from main import derive_password   # 替换为实际模块名

# 常量，减少重复
MASTER = "MySecureMaster123!"
SALT = "global_salt_value"
SITE = "example.com"


# ==================== 输出长度测试 ====================
@pytest.mark.parametrize("length, symbols", [
    (3, ""),                     # 无符号最小长度
    (4, string.punctuation),     # 有符号最小长度
    (8, ""),
    (12, "!@#$"),
    (16, string.punctuation),
    (20, "()"),
    (32, string.punctuation),    # 最大长度
])
def test_output_length(length, symbols):
    """验证派生密码长度等于请求的长度"""
    pwd = derive_password(MASTER, SALT, SITE, length=length, symbols=symbols)
    assert len(pwd) == length


# ==================== 字符类型包含测试（核心） ====================
@pytest.mark.parametrize("length, symbols, desc", [
    (4, string.punctuation, "最小长度+默认符号"),
    (8, "", "无符号"),
    (12, "!@#", "自定义符号"),
    (16, string.punctuation, "默认符号"),
    (32, "()", "最大长度+自定义符号"),
    (6, "", "无符号短密码"),
])
def test_required_char_types_present(length, symbols, desc):
    """验证密码包含所有必需的字符类型"""
    pwd = derive_password(MASTER, SALT, SITE, length=length, symbols=symbols)
    # 必须包含大写、小写、数字
    assert any(c.isupper() for c in pwd), f"{desc}: 缺少大写字母"
    assert any(c.islower() for c in pwd), f"{desc}: 缺少小写字母"
    assert any(c.isdigit() for c in pwd), f"{desc}: 缺少数字"
    if symbols:
        assert any(c in symbols for c in pwd), f"{desc}: 缺少特殊字符"
    else:
        # 无符号时确保没有默认特殊字符
        assert not any(c in string.punctuation for c in pwd), f"{desc}: 不应包含特殊字符"


# ==================== 字符集合法性测试 ====================
@pytest.mark.parametrize("length, symbols", [
    (4, string.punctuation),
    (10, "!@#$%"),
    (20, ""),
])
def test_characters_from_allowed_sets(length, symbols):
    """验证所有字符均来自允许的字符集"""
    pwd = derive_password(MASTER, SALT, SITE, length=length, symbols=symbols)
    allowed = set(string.ascii_uppercase + string.ascii_lowercase + string.digits + symbols)
    assert all(c in allowed for c in pwd)


# ==================== 确定性测试 ====================
@pytest.mark.parametrize("master, salt, site, length, symbols", [
    (MASTER, SALT, SITE, 12, string.punctuation),
    ("abc", "xyz", "test.com", 8, "!@#"),
])
def test_deterministic(master, salt, site, length, symbols):
    """相同输入必须产生相同输出"""
    pwd1 = derive_password(master, salt, site, length=length, symbols=symbols)
    pwd2 = derive_password(master, salt, site, length=length, symbols=symbols)
    assert pwd1 == pwd2


# ==================== 差异输入产生不同密码 ====================
def test_different_master_yields_different_password():
    pwd1 = derive_password("pass1", SALT, SITE, length=12)
    pwd2 = derive_password("pass2", SALT, SITE, length=12)
    assert pwd1 != pwd2

def test_different_site_yields_different_password():
    pwd1 = derive_password(MASTER, SALT, "a.com", length=12)
    pwd2 = derive_password(MASTER, SALT, "b.com", length=12)
    assert pwd1 != pwd2

def test_different_salt_yields_different_password():
    pwd1 = derive_password(MASTER, "salt1", SITE, length=12)
    pwd2 = derive_password(MASTER, "salt2", SITE, length=12)
    assert pwd1 != pwd2

def test_different_length_yields_different_password():
    pwd1 = derive_password(MASTER, SALT, SITE, length=10)
    pwd2 = derive_password(MASTER, SALT, SITE, length=11)
    # 长度不同，派生结果不可能相同
    assert pwd1 != pwd2


# ==================== 边界输入 & 错误处理 ====================
def test_non_integer_length_raises_type_error():
    with pytest.raises(TypeError):
        derive_password(MASTER, SALT, SITE, length="16")

def test_length_too_small_raises_value_error():
    # 无符号时最小长度应为3
    with pytest.raises(ValueError):
        derive_password(MASTER, SALT, SITE, length=2, symbols="")
    # 有符号时最小长度应为4
    with pytest.raises(ValueError):
        derive_password(MASTER, SALT, SITE, length=3, symbols=string.punctuation)

def test_zero_length_raises_value_error():
    with pytest.raises(ValueError):
        derive_password(MASTER, SALT, SITE, length=0)

def test_negative_length_raises_value_error():
    with pytest.raises(ValueError):
        derive_password(MASTER, SALT, SITE, length=-1)


# ==================== 自定义符号集特殊测试 ====================
def test_custom_symbols_only_used():
    """自定义符号集时，密码中只包含自定义符号，不包含默认标点"""
    custom = "()"
    pwd = derive_password(MASTER, SALT, SITE, length=12, symbols=custom)
    assert any(c in custom for c in pwd)
    # 不应出现默认符号集中但不在自定义符号集中的字符
    for c in pwd:
        if c in string.punctuation:
            assert c in custom, f"密码中出现了非预期的特殊字符: {c}"

def test_empty_symbols_disables_special():
    """空字符串 symbols 应完全禁止特殊字符"""
    pwd = derive_password(MASTER, SALT, SITE, length=10, symbols="")
    assert not any(c in string.punctuation for c in pwd)


# 如果你是直接运行本脚本（而非通过 pytest 命令行），可加上：
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])