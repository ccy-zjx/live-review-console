"""
直播中控数据库 — SQLite 初始化 + 建表 + 预设数据
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "live_db.sqlite")


def get_connection():
    """获取数据库连接（启用 WAL 模式 + 外键）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def create_tables(conn=None):
    """建表（幂等，已存在的表不重复创建）"""
    if conn is None:
        conn = get_connection()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS live_sessions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        session_date    TEXT    NOT NULL,
        start_time      TEXT,
        end_time        TEXT,
        platform        TEXT    DEFAULT '抖音',
        host_name       TEXT    DEFAULT '',
        total_viewers   INTEGER DEFAULT 0,
        peak_online     INTEGER DEFAULT 0,
        total_orders    INTEGER DEFAULT 0,
        total_gmv       REAL    DEFAULT 0.0,
        notes           TEXT
    );

    CREATE TABLE IF NOT EXISTS conversion_scenarios (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id            INTEGER REFERENCES live_sessions(id) ON DELETE CASCADE,
        script_id             INTEGER REFERENCES response_scripts(id) ON DELETE SET NULL,
        timestamp             TEXT,
        scenario_type         TEXT,
        trigger_action        TEXT,
        before_orders         INTEGER DEFAULT 0,
        after_orders          INTEGER DEFAULT 0,
        conversion_rate_delta REAL    DEFAULT 0.0,
        chat_atmosphere       TEXT,
        screen_record_path    TEXT,
        tags                  TEXT
    );

    -- migration: add script_id (safe, ignores if exists)
    """)
    # 安全迁移：忽略已存在列的错误
    try:
        conn.execute(
            "ALTER TABLE conversion_scenarios ADD COLUMN script_id INTEGER REFERENCES response_scripts(id) ON DELETE SET NULL"
        )
    except sqlite3.OperationalError:
        pass  # 列已存在
    conn.executescript("""

    CREATE TABLE IF NOT EXISTS questions (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text  TEXT    UNIQUE NOT NULL,
        category       TEXT,
        frequency      INTEGER DEFAULT 1,
        difficulty     TEXT    DEFAULT '中等',
        is_sensitive   INTEGER DEFAULT 0,
        first_seen     TEXT,
        last_seen      TEXT
    );

    CREATE TABLE IF NOT EXISTS response_scripts (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id           INTEGER REFERENCES questions(id) ON DELETE CASCADE,
        version               TEXT    DEFAULT 'v1.0',
        script_text           TEXT    NOT NULL,
        script_type           TEXT    DEFAULT '标准应答',
        tone                  TEXT    DEFAULT '专业',
        author                TEXT,
        created_date          TEXT,
        effectiveness_score   REAL    DEFAULT 3.0,
        usage_count           INTEGER DEFAULT 0,
        avg_conversion_boost  REAL    DEFAULT 0.0,
        notes                 TEXT
    );

    CREATE TABLE IF NOT EXISTS script_ab_tests (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id   INTEGER REFERENCES questions(id) ON DELETE CASCADE,
        script_a_id   INTEGER REFERENCES response_scripts(id) ON DELETE SET NULL,
        script_b_id   INTEGER REFERENCES response_scripts(id) ON DELETE SET NULL,
        test_date     TEXT,
        session_id    INTEGER REFERENCES live_sessions(id) ON DELETE SET NULL,
        winner        TEXT,
        metric_a      REAL,
        metric_b      REAL,
        conclusion    TEXT
    );

    CREATE TABLE IF NOT EXISTS violation_rules (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword     TEXT    UNIQUE NOT NULL,
        category    TEXT,
        severity    TEXT    DEFAULT '警告',
        platform    TEXT    DEFAULT '抖音',
        alternative TEXT,
        source      TEXT,
        added_date  TEXT
    );

    CREATE TABLE IF NOT EXISTS violation_cases (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        case_title          TEXT,
        platform            TEXT    DEFAULT '抖音',
        brand_name          TEXT,
        violation_type      TEXT,
        original_content    TEXT,
        penalty             TEXT,
        lesson              TEXT,
        preventive_measure  TEXT,
        occurred_date       TEXT,
        source_url          TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_questions_freq ON questions(frequency DESC);
    CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category);
    CREATE INDEX IF NOT EXISTS idx_scripts_question ON response_scripts(question_id);
    CREATE INDEX IF NOT EXISTS idx_violations_keyword ON violation_rules(keyword);
    CREATE INDEX IF NOT EXISTS idx_violations_category ON violation_rules(category);
    """)

    conn.commit()
    return conn


# ============================================================
# 抖音平台预设违规词（50 条，基于巨量百应规范）
# ============================================================

DOUYIN_VIOLATIONS = [
    # ---- 极限词 ----
    ("第一", "极限词", "封禁", "抖音", "领先/前列", "《广告法》第九条"),
    ("最好", "极限词", "封禁", "抖音", "很好/非常好", "《广告法》第九条"),
    ("最佳", "极限词", "封禁", "抖音", "出色/优质", "《广告法》第九条"),
    ("唯一", "极限词", "封禁", "抖音", "仅有/独有", "《广告法》第九条"),
    ("全网第一", "极限词", "封禁", "抖音", "广受好评", "《广告法》第九条"),
    ("全国第一", "极限词", "封禁", "抖音", "深受欢迎", "《广告法》第九条"),
    ("顶级", "极限词", "封禁", "抖音", "高品质/高端", "《广告法》第九条"),
    ("极品", "极限词", "封禁", "抖音", "优质/精品", "《广告法》第九条"),
    ("最高级", "极限词", "封禁", "抖音", "高级/高端", "《广告法》第九条"),
    ("最先进", "极限词", "封禁", "抖音", "先进/领先", "《广告法》第九条"),
    ("最便宜", "极限词", "警告", "抖音", "实惠/划算", "《广告法》第九条"),
    ("全网最低价", "极限词", "封禁", "抖音", "很实惠的价格", "《广告法》第九条"),
    ("绝对", "极限词", "警告", "抖音", "确实/的确", "《广告法》第九条"),
    ("100%", "极限词", "警告", "抖音", "高比例/绝大多数", "《广告法》第九条"),
    ("永不", "极限词", "警告", "抖音", "持久/长效", "《广告法》第九条"),

    # ---- 虚假宣传 ----
    ("无效退款", "虚假宣传", "封禁", "抖音", "支持退换", "抖音电商规则"),
    ("保证效果", "虚假宣传", "封禁", "抖音", "效果因人而异", "抖音电商规则"),
    ("包治", "虚假宣传", "封禁", "抖音", "有助于缓解", "《广告法》第十七条"),
    ("根治", "虚假宣传", "封禁", "抖音", "改善/缓解", "《广告法》第十七条"),
    ("立竿见影", "虚假宣传", "警告", "抖音", "效果明显", "抖音电商规则"),
    ("马上见效", "虚假宣传", "警告", "抖音", "持续使用可见效", "抖音电商规则"),
    ("神奇", "虚假宣传", "警告", "抖音", "独特/特别", "《广告法》"),
    ("万能", "虚假宣传", "封禁", "抖音", "多功能/多用途", "《广告法》"),

    # ---- 医疗/功效宣称 ----
    ("杀菌", "医疗宣称", "封禁", "抖音", "净化/清新", "《广告法》第十七条"),
    ("消毒", "医疗宣称", "封禁", "抖音", "清洁/净化", "《广告法》第十七条"),
    ("治疗", "医疗宣称", "封禁", "抖音", "改善/缓解", "《广告法》第十七条"),
    ("抗菌", "医疗宣称", "封禁", "抖音", "清新/洁净", "《广告法》第十七条"),
    ("除甲醛", "医疗宣称", "封禁", "抖音", "净化空气/去异味", "《广告法》"),
    ("抗癌", "医疗宣称", "封禁", "抖音", "(禁止此类宣称)", "《广告法》第十七条"),

    # ---- 政治/敏感 ----
    ("国家推荐", "政治敏感", "封禁", "抖音", "广受认可", "抖音社区规范"),
    ("政府指定", "政治敏感", "封禁", "抖音", "受认可产品", "抖音社区规范"),
    ("领导人", "政治敏感", "封禁", "抖音", "(禁止提及)", "抖音社区规范"),

    # ---- 平台禁词 ----
    ("加微信", "平台禁词", "限流", "抖音", "联系客服", "抖音电商规则"),
    ("微信号", "平台禁词", "限流", "抖音", "联系方式", "抖音电商规则"),
    ("二维码", "平台禁词", "限流", "抖音", "详情页查看", "抖音电商规则"),
    ("刷单", "平台禁词", "封禁", "抖音", "(禁止讨论)", "抖音电商规则"),
    ("差评", "平台禁词", "限流", "抖音", "反馈/建议", "抖音电商规则"),
    ("返现", "平台禁词", "限流", "抖音", "优惠/福利", "抖音电商规则"),
    ("好评返现", "平台禁词", "封禁", "抖音", "(禁止此类活动)", "抖音电商规则"),
    ("引导好评", "平台禁词", "警告", "抖音", "感谢支持", "抖音电商规则"),

    # ---- 竞品/对比 ----
    ("比某某好", "恶意对比", "警告", "抖音", "我们的优势是", "《广告法》第十三条"),
    ("碾压同行", "恶意对比", "警告", "抖音", "表现优异", "《广告法》第十三条"),
    ("吊打", "恶意对比", "警告", "抖音", "显著优于", "《广告法》第十三条"),
    ("完爆", "恶意对比", "警告", "抖音", "好于", "《广告法》第十三条"),

    # ---- 诱导互动 ----
    ("转发", "诱导互动", "限流", "抖音", "分享给朋友", "抖音社区规范"),
    ("点赞过万", "诱导互动", "限流", "抖音", "觉得不错点个赞", "抖音社区规范"),
    ("关注我", "诱导互动", "限流", "抖音", "可以关注一下", "抖音社区规范"),
    ("扣1", "诱导互动", "限流", "抖音", "想要的告诉我", "抖音社区规范"),
]


def seed_violations(conn=None):
    """预置抖音违规词"""
    if conn is None:
        conn = get_connection()
    from datetime import date
    today = date.today().isoformat()
    for keyword, category, severity, platform, alternative, source in DOUYIN_VIOLATIONS:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO violation_rules
                   (keyword, category, severity, platform, alternative, source, added_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (keyword, category, severity, platform, alternative, source, today)
            )
        except Exception:
            pass
    conn.commit()
    print(f"[+] 已预置 {len(DOUYIN_VIOLATIONS)} 条抖音违规词")
    return conn


# ============================================================
# 初始化入口
# ============================================================

def init_database():
    """首次运行：建表 + 预置数据"""
    if os.path.exists(DB_PATH):
        print(f"[*] 数据库已存在: {DB_PATH}")
    else:
        print(f"[+] 创建数据库: {DB_PATH}")

    conn = get_connection()
    conn = create_tables(conn)
    conn = seed_violations(conn)
    conn.close()
    print("[+] 数据库初始化完成")


if __name__ == "__main__":
    init_database()
