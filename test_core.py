#!/usr/bin/env python3
"""
test_core.py — 密码生成核心的单元测试与兼容性回归测试
运行方式: pytest -v tests/test_core.py
"""

import pytest
import string
from core import derive_sha256, assemble_password


# ============================================================
# 第一部分：边界情况与单元测试
# ============================================================

class TestDeriveSHA256:
    """密钥派生函数测试"""

    def test_deterministic(self):
        """相同输入必须产生相同种子"""
        s1 = derive_sha256("password", "salt", "example", iterations=1000, length=32)
        s2 = derive_sha256("password", "salt", "example", iterations=1000, length=32)
        assert s1 == s2

    def test_different_master_pass(self):
        """不同主密码产生不同种子"""
        s1 = derive_sha256("password1", "salt", "name", iterations=1000)
        s2 = derive_sha256("password2", "salt", "name", iterations=1000)
        assert s1 != s2

    def test_different_salt(self):
        """不同盐值产生不同种子"""
        s1 = derive_sha256("password", "salt1", "name", iterations=1000)
        s2 = derive_sha256("password", "salt2", "name", iterations=1000)
        assert s1 != s2

    def test_different_name(self):
        """不同标识符产生不同种子"""
        s1 = derive_sha256("password", "salt", "name1", iterations=1000)
        s2 = derive_sha256("password", "salt", "name2", iterations=1000)
        assert s1 != s2

    def test_colon_safety(self):
        """分隔符冲突修复验证：含冒号的 name 不会造成歧义"""
        # 构造一对原本可能碰撞的输入
        # name="a:b", master_pass="c"  vs  name="a", master_pass="b:c"
        s1 = derive_sha256("c", "salt", "a:b", iterations=1000)
        s2 = derive_sha256("b:c", "salt", "a", iterations=1000)
        assert s1 != s2, "长度前缀方案应该避免冒号歧义"

    def test_iterations_effect(self):
        """不同迭代次数产生不同种子"""
        s1 = derive_sha256("password", "salt", "name", iterations=1000)
        s2 = derive_sha256("password", "salt", "name", iterations=1001)
        assert s1 != s2

    def test_output_length(self):
        """输出长度符合参数要求"""
        for dklen in [16, 32, 64, 128]:
            seed = derive_sha256("p", "s", "n", iterations=1, length=dklen)
            assert len(seed) == dklen


class TestAssemblePassword:
    """密码组装函数测试"""

    # 固定一个测试用种子 (便于快速测试，与生产种子无关)
    TEST_SEED = b'\x00' * 32  # 32 字节零种子

    def test_deterministic(self):
        """相同种子和参数生成相同密码"""
        pw1 = assemble_password(self.TEST_SEED, length=16, symbols="!@#$")
        pw2 = assemble_password(self.TEST_SEED, length=16, symbols="!@#$")
        assert pw1 == pw2

    def test_different_seed(self):
        """不同种子产生不同密码"""
        seed2 = b'\x01' * 32
        pw1 = assemble_password(self.TEST_SEED, length=16)
        pw2 = assemble_password(seed2, length=16)
        assert pw1 != pw2

    def test_length(self):
        """生成密码长度正确"""
        for l in [8, 16, 32, 100]:
            pw = assemble_password(self.TEST_SEED, length=l, symbols="")
            assert len(pw) == l

    def test_min_length_with_symbols(self):
        """长度 = 4 (四种字符集) 时正常"""
        pw = assemble_password(self.TEST_SEED, length=4, symbols="!@#$")
        assert len(pw) == 4

    def test_min_length_no_symbols(self):
        """长度 = 3 (仅字母数字) 时正常"""
        pw = assemble_password(self.TEST_SEED, length=3, symbols="")
        assert len(pw) == 3

    def test_length_too_short_raises(self):
        """长度过短抛出 ValueError"""
        with pytest.raises(ValueError, match="非法的长度"):
            assemble_password(self.TEST_SEED, length=3, symbols="!@#$")  # 需要4类，只给3
        with pytest.raises(ValueError, match="非法的长度"):
            assemble_password(self.TEST_SEED, length=2, symbols="")      # 需要3类，给2

    def test_empty_symbols(self):
        """symbols="" 时密码仅包含大小写字母和数字，不含其他符号"""
        pw = assemble_password(self.TEST_SEED, length=100, symbols="")
        allowed = set(string.ascii_uppercase + string.ascii_lowercase + string.digits)
        assert all(c in allowed for c in pw)
        # 强制至少包含每种类型（此测试用长密码几乎必然通过，但仍需确认）
        assert any(c.isupper() for c in pw)
        assert any(c.islower() for c in pw)
        assert any(c.isdigit() for c in pw)

    def test_default_symbols(self):
        """默认符号集包含特殊字符"""
        pw = assemble_password(self.TEST_SEED, length=100)  # 使用默认符号集
        default_sym = set("!@#$%^&*()_+-=")
        assert any(c in default_sym for c in pw)

    def test_char_types_present(self):
        """密码必须包含所有要求的字符类型"""
        custom_symbols = "!@"
        pw = assemble_password(self.TEST_SEED, length=8, symbols=custom_symbols)
        has_upper = any(c.isupper() for c in pw)
        has_lower = any(c.islower() for c in pw)
        has_digit = any(c.isdigit() for c in pw)
        has_custom = any(c in custom_symbols for c in pw)
        assert has_upper and has_lower and has_digit and has_custom

    def test_type_check_bool_fails(self):
        """length 传入 bool 值 (True) 必须抛出 TypeError"""
        with pytest.raises(TypeError, match="长度必须为整数"):
            assemble_password(self.TEST_SEED, length=True)

    def test_type_check_float_fails(self):
        """length 传入浮点数也必须抛出 TypeError"""
        with pytest.raises(TypeError):
            assemble_password(self.TEST_SEED, length=16.0)

    def test_large_length(self):
        """能够生成极长密码 (如 1000 位)"""
        pw = assemble_password(self.TEST_SEED, length=256)
        assert len(pw) == 256

    def test_special_symbols_handling(self):
        """各种特殊字符作为符号集均能正常处理"""
        weird_sym = "\\\"'&<>{}[]()"
        pw = assemble_password(self.TEST_SEED, length=16, symbols=weird_sym)
        assert len(pw) == 16
        # 至少有一个字符来自该怪异集合
        assert any(c in weird_sym for c in pw)


# ============================================================
# 第二部分：兼容性回归测试向量（固定输入输出）
# ============================================================
#
# ⚠️ 使用说明：
# 1. 首先运行 generate_vectors() 函数（见本文件末尾）生成真实输出
# 2. 将打印出的字典填入下面的 COMPATIBILITY_VECTORS 列表中
# 3. 然后运行 pytest，这些向量将永久固化，任何修改都必须通过这些测试
# ============================================================

COMPATIBILITY_VECTORS = [
    {
        "description": "标准配置（中文标识）",
        "master_pass": "Don't forget me",
        "salt": "Don't forget my heartbeat on my right",
        "name": "Re1999-大号",
        "iterations": 600000,
        "length": 16,
        "symbols": "!@#$%^&*()_+-=",
        "expected_password": "v7E3286x(Ms@ps2L"   # 待填入
    },
    {
        "description": "无特殊符号",
        "master_pass": "P@ssw0rd!",
        "salt": "my_salt",
        "name": "google.com",
        "iterations": 600000,
        "length": 20,
        "symbols": "",
        "expected_password": "Rze610xSh998243as9Vz"   # 待填入
    },
    {
        "description": "较短迭代(快速测试用)",
        "master_pass": "short",
        "salt": "short_salt",
        "name": "github",
        "iterations": 600000,        # 仅用于快速回归，不代表生产安全
        "length": 12,
        "symbols": "@#$",
        "expected_password": "T8#wF@5#6$ly"   # 待填入
    },
    {
        "description": "长密码+自定义符号",
        "master_pass": "I've read some research that proposes that human fingers evolved to facilitate hand-holding. Nonsense, they obviously evolved to grasp tools ... What kind of corny researcher came up with that?",
        "salt": "hissabeth",
        "name": "laplace",
        "iterations": 600000,
        "length": 32,
        "symbols": "{}[]()<>?!",
        "expected_password": "R]d{E{5}P6ITd5j0VETc0p{n)e?2()!x"   # 待填入
    },
    {
        "description": "最小长度4类字符",
        "master_pass": "minlen",
        "salt": "minsalt",
        "name": "a.b.c",
        "iterations": 600000,
        "length": 4,
        "symbols": "!@",
        "expected_password": "2m!H"   # 待填入
    }
]


@pytest.mark.slow  # 标记为慢速测试，可通过 pytest -m "not slow" 跳过
class TestCompatibilityVectors:
    @pytest.mark.parametrize("vec", COMPATIBILITY_VECTORS, ids=lambda v: v["description"])
    def test_vector(self, vec):
        if not vec["expected_password"]:
            pytest.skip("兼容性向量尚未填入真实值，请运行 generate_vectors() 生成。")
        seed = derive_sha256(vec["master_pass"], vec["salt"], vec["name"],
                             iterations=vec["iterations"], length=256)
        pw = assemble_password(seed, vec["length"], vec["symbols"])
        assert pw == vec["expected_password"], \
            f"与已固化的密码不匹配！若为故意修改，请更新向量。"


# ============================================================
# 辅助工具：生成兼容性向量真实值
# ============================================================
def generate_vectors():
    """
    运行此函数打印出需要填入测试文件中的完整向量字典。
    用法:
        python -c "from tests.test_core import generate_vectors; generate_vectors()"
    """
    import pprint
    filled = []
    for v in COMPATIBILITY_VECTORS:
        seed = derive_sha256(v["master_pass"], v["salt"], v["name"],
                             iterations=v["iterations"], length=256)
        pw = assemble_password(seed, v["length"], v["symbols"])
        new_v = v.copy()
        new_v["expected_password"] = pw
        filled.append(new_v)
    print("请将以下列表粘贴到 test_core.py 的 COMPATIBILITY_VECTORS 中：\n")
    pprint.pprint(filled, sort_dicts=False, width=120)


if __name__ == "__main__":
    generate_vectors()