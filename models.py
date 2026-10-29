"""
数据模型层 — 各表的 CRUD 封装
"""
from database import get_connection
from datetime import date


# ==================== Live Sessions ====================

class LiveSession:
    @staticmethod
    def create(session_date=None, start_time=None, end_time=None,
               platform="抖音", host_name="", total_viewers=0, peak_online=0,
               total_orders=0, total_gmv=0.0, notes=""):
        if session_date is None:
            session_date = date.today().isoformat()
        conn = get_connection()
        cur = conn.execute(
            """INSERT INTO live_sessions
               (session_date, start_time, end_time, platform, host_name,
                total_viewers, peak_online, total_orders, total_gmv, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (session_date, start_time, end_time, platform, host_name,
             total_viewers, peak_online, total_orders, total_gmv, notes)
        )
        conn.commit()
        conn.close()
        return cur.lastrowid

    @staticmethod
    def update(sid, **kwargs):
        if not kwargs:
            return
        conn = get_connection()
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [sid]
        conn.execute(f"UPDATE live_sessions SET {sets} WHERE id=?", vals)
        conn.commit()
        conn.close()

    @staticmethod
    def get_all(order="session_date DESC"):
        conn = get_connection()
        rows = conn.execute(
            f"SELECT * FROM live_sessions ORDER BY {order}"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_by_id(sid):
        conn = get_connection()
        row = conn.execute("SELECT * FROM live_sessions WHERE id=?", (sid,)).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def delete(sid):
        conn = get_connection()
        conn.execute("DELETE FROM live_sessions WHERE id=?", (sid,))
        conn.commit()
        conn.close()

    @staticmethod
    def stats_today():
        conn = get_connection()
        today = date.today().isoformat()
        row = conn.execute(
            """SELECT COUNT(*) as count,
                      COALESCE(SUM(total_orders),0) as orders,
                      COALESCE(SUM(total_gmv),0) as gmv
               FROM live_sessions WHERE session_date=?""",
            (today,)
        ).fetchone()
        conn.close()
        return dict(row) if row else {"count": 0, "orders": 0, "gmv": 0}


# ==================== Conversion Scenarios ====================

class ConversionScenario:
    @staticmethod
    def create(session_id, timestamp=None, scenario_type="",
               trigger_action="", before_orders=0, after_orders=0,
               conversion_rate_delta=0.0, chat_atmosphere="",
               screen_record_path="", tags="", script_id=None):
        conn = get_connection()
        cur = conn.execute(
            """INSERT INTO conversion_scenarios
               (session_id, script_id, timestamp, scenario_type, trigger_action,
                before_orders, after_orders, conversion_rate_delta,
                chat_atmosphere, screen_record_path, tags)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (session_id, script_id, timestamp, scenario_type, trigger_action,
             before_orders, after_orders, conversion_rate_delta,
             chat_atmosphere, screen_record_path, tags)
        )
        conn.commit()
        conn.close()
        return cur.lastrowid

    @staticmethod
    def update(cid, **kwargs):
        if not kwargs:
            return
        conn = get_connection()
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [cid]
        conn.execute(f"UPDATE conversion_scenarios SET {sets} WHERE id=?", vals)
        conn.commit()
        conn.close()

    @staticmethod
    def get_all(order="id DESC", limit=50):
        conn = get_connection()
        rows = conn.execute(
            f"""SELECT cs.*, ls.session_date
                FROM conversion_scenarios cs
                LEFT JOIN live_sessions ls ON cs.session_id = ls.id
                ORDER BY cs.{order}
                LIMIT ?"""
        , (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_by_id(cid):
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM conversion_scenarios WHERE id=?", (cid,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_by_session(session_id):
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM conversion_scenarios WHERE session_id=? ORDER BY id",
            (session_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def delete(cid):
        conn = get_connection()
        conn.execute("DELETE FROM conversion_scenarios WHERE id=?", (cid,))
        conn.commit()
        conn.close()

    @staticmethod
    def top_by_conversion(limit=10):
        conn = get_connection()
        rows = conn.execute(
            """SELECT cs.*, ls.session_date
               FROM conversion_scenarios cs
               LEFT JOIN live_sessions ls ON cs.session_id = ls.id
               ORDER BY cs.conversion_rate_delta DESC
               LIMIT ?""",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]


# ==================== Questions ====================

class Question:
    @staticmethod
    def create_or_update(question_text, category="", difficulty="中等",
                         is_sensitive=False):
        today = date.today().isoformat()
        conn = get_connection()
        existing = conn.execute(
            "SELECT id, frequency FROM questions WHERE question_text=?",
            (question_text,)
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE questions SET frequency=frequency+1, last_seen=?
                   WHERE id=?""",
                (today, existing["id"])
            )
            qid = existing["id"]
        else:
            cur = conn.execute(
                """INSERT INTO questions
                   (question_text, category, frequency, difficulty,
                    is_sensitive, first_seen, last_seen)
                   VALUES (?,?,1,?,?,?,?)""",
                (question_text, category, int(is_sensitive), difficulty,
                 today, today)
            )
            qid = cur.lastrowid
        conn.commit()
        conn.close()
        return qid

    @staticmethod
    def update(qid, **kwargs):
        if not kwargs:
            return
        conn = get_connection()
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [qid]
        conn.execute(f"UPDATE questions SET {sets} WHERE id=?", vals)
        conn.commit()
        conn.close()

    @staticmethod
    def get_all(order="frequency DESC", limit=100, category=None):
        conn = get_connection()
        if category:
            rows = conn.execute(
                f"""SELECT * FROM questions WHERE category=?
                    ORDER BY {order} LIMIT ?""",
                (category, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM questions ORDER BY {order} LIMIT ?",
                (limit,)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_by_id(qid):
        conn = get_connection()
        row = conn.execute("SELECT * FROM questions WHERE id=?", (qid,)).fetchone()
        # 附带所有关联话术
        scripts = conn.execute(
            "SELECT * FROM response_scripts WHERE question_id=? ORDER BY version DESC",
            (qid,)
        ).fetchall()
        conn.close()
        result = dict(row) if row else None
        if result:
            result["scripts"] = [dict(s) for s in scripts]
        return result

    @staticmethod
    def search(keyword, limit=30):
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM questions WHERE question_text LIKE ? ORDER BY frequency DESC LIMIT ?",
            (f"%{keyword}%", limit)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def categories():
        conn = get_connection()
        rows = conn.execute(
            "SELECT category, COUNT(*) as cnt FROM questions GROUP BY category ORDER BY cnt DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def delete(qid):
        conn = get_connection()
        conn.execute("DELETE FROM questions WHERE id=?", (qid,))
        conn.commit()
        conn.close()


# ==================== Response Scripts ====================

class ResponseScript:
    @staticmethod
    def create(question_id, script_text, version="v1.0",
               script_type="标准应答", tone="专业", author="",
               effectiveness_score=3.0, notes=""):
        today = date.today().isoformat()
        conn = get_connection()
        cur = conn.execute(
            """INSERT INTO response_scripts
               (question_id, version, script_text, script_type, tone,
                author, created_date, effectiveness_score, notes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (question_id, version, script_text, script_type, tone,
             author, today, effectiveness_score, notes)
        )
        conn.commit()
        conn.close()
        return cur.lastrowid

    @staticmethod
    def update(sid, **kwargs):
        if not kwargs:
            return
        conn = get_connection()
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [sid]
        conn.execute(f"UPDATE response_scripts SET {sets} WHERE id=?", vals)
        conn.commit()
        conn.close()

    @staticmethod
    def get_all(order="effectiveness_score DESC", limit=100):
        conn = get_connection()
        rows = conn.execute(
            f"""SELECT rs.*, q.question_text, q.category as question_category
                FROM response_scripts rs
                LEFT JOIN questions q ON rs.question_id = q.id
                ORDER BY {order} LIMIT ?""",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_by_id(sid):
        conn = get_connection()
        row = conn.execute(
            """SELECT rs.*, q.question_text
               FROM response_scripts rs
               LEFT JOIN questions q ON rs.question_id = q.id
               WHERE rs.id=?""",
            (sid,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_by_question(qid):
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM response_scripts WHERE question_id=? ORDER BY version DESC",
            (qid,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def increment_usage(sid):
        conn = get_connection()
        conn.execute(
            "UPDATE response_scripts SET usage_count=usage_count+1 WHERE id=?",
            (sid,)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def top_rated(limit=10):
        conn = get_connection()
        rows = conn.execute(
            """SELECT rs.*, q.question_text
               FROM response_scripts rs
               LEFT JOIN questions q ON rs.question_id = q.id
               ORDER BY rs.effectiveness_score DESC, rs.usage_count DESC
               LIMIT ?""",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def delete(sid):
        conn = get_connection()
        conn.execute("DELETE FROM response_scripts WHERE id=?", (sid,))
        conn.commit()
        conn.close()


# ==================== Script AB Tests ====================

class ScriptABTest:
    @staticmethod
    def create(question_id, script_a_id, script_b_id, winner="",
               metric_a=0.0, metric_b=0.0, conclusion="",
               test_date=None, session_id=None):
        if test_date is None:
            test_date = date.today().isoformat()
        conn = get_connection()
        cur = conn.execute(
            """INSERT INTO script_ab_tests
               (question_id, script_a_id, script_b_id, test_date,
                session_id, winner, metric_a, metric_b, conclusion)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (question_id, script_a_id, script_b_id, test_date,
             session_id, winner, metric_a, metric_b, conclusion)
        )
        conn.commit()
        conn.close()
        return cur.lastrowid

    @staticmethod
    def get_all(limit=50):
        conn = get_connection()
        rows = conn.execute(
            """SELECT ab.*,
                      q.question_text,
                      a.script_text as script_a_text,
                      b.script_text as script_b_text
               FROM script_ab_tests ab
               LEFT JOIN questions q ON ab.question_id = q.id
               LEFT JOIN response_scripts a ON ab.script_a_id = a.id
               LEFT JOIN response_scripts b ON ab.script_b_id = b.id
               ORDER BY ab.test_date DESC
               LIMIT ?""",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def stats():
        conn = get_connection()
        row = conn.execute(
            """SELECT COUNT(*) as total,
                      SUM(CASE WHEN winner='A' THEN 1 ELSE 0 END) as a_wins,
                      SUM(CASE WHEN winner='B' THEN 1 ELSE 0 END) as b_wins,
                      SUM(CASE WHEN winner='平' THEN 1 ELSE 0 END) as ties
               FROM script_ab_tests"""
        ).fetchone()
        conn.close()
        return dict(row) if row else {}


# ==================== Violation Rules ====================

class ViolationRule:
    @staticmethod
    def create(keyword, category="", severity="警告", platform="抖音",
               alternative="", source="", added_date=None):
        if added_date is None:
            added_date = date.today().isoformat()
        conn = get_connection()
        try:
            cur = conn.execute(
                """INSERT INTO violation_rules
                   (keyword, category, severity, platform, alternative, source, added_date)
                   VALUES (?,?,?,?,?,?,?)""",
                (keyword, category, severity, platform, alternative, source, added_date)
            )
            conn.commit()
            conn.close()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            conn.close()
            return None  # 重复关键词

    @staticmethod
    def get_all(order="severity DESC, id DESC", limit=200, category=None):
        conn = get_connection()
        if category:
            rows = conn.execute(
                f"SELECT * FROM violation_rules WHERE category=? ORDER BY {order} LIMIT ?",
                (category, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM violation_rules ORDER BY {order} LIMIT ?",
                (limit,)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def check_text(text):
        """检查文本中的违规词，返回命中的所有规则"""
        conn = get_connection()
        all_rules = conn.execute("SELECT * FROM violation_rules").fetchall()
        conn.close()
        hits = []
        for rule in all_rules:
            r = dict(rule)
            if r["keyword"] in text:
                hits.append(r)
        # 按严重度排序
        severity_order = {"封禁": 0, "限流": 1, "警告": 2}
        hits.sort(key=lambda x: severity_order.get(x["severity"], 3))
        return hits

    @staticmethod
    def search(keyword, limit=30):
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM violation_rules WHERE keyword LIKE ? ORDER BY severity LIMIT ?",
            (f"%{keyword}%", limit)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def delete(vid):
        conn = get_connection()
        conn.execute("DELETE FROM violation_rules WHERE id=?", (vid,))
        conn.commit()
        conn.close()

    @staticmethod
    def categories():
        conn = get_connection()
        rows = conn.execute(
            "SELECT category, COUNT(*) as cnt FROM violation_rules GROUP BY category ORDER BY cnt DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def count():
        conn = get_connection()
        row = conn.execute("SELECT COUNT(*) as cnt FROM violation_rules").fetchone()
        conn.close()
        return row["cnt"] if row else 0


# ==================== Violation Cases ====================

class ViolationCase:
    @staticmethod
    def create(case_title, platform="抖音", brand_name="", violation_type="",
               original_content="", penalty="", lesson="",
               preventive_measure="", occurred_date="", source_url=""):
        conn = get_connection()
        cur = conn.execute(
            """INSERT INTO violation_cases
               (case_title, platform, brand_name, violation_type,
                original_content, penalty, lesson, preventive_measure,
                occurred_date, source_url)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (case_title, platform, brand_name, violation_type,
             original_content, penalty, lesson, preventive_measure,
             occurred_date, source_url)
        )
        conn.commit()
        conn.close()
        return cur.lastrowid

    @staticmethod
    def get_all(limit=50):
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM violation_cases ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def search(keyword, limit=30):
        conn = get_connection()
        rows = conn.execute(
            """SELECT * FROM violation_cases
               WHERE case_title LIKE ? OR original_content LIKE ? OR lesson LIKE ?
               ORDER BY id DESC LIMIT ?""",
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def delete(vid):
        conn = get_connection()
        conn.execute("DELETE FROM violation_cases WHERE id=?", (vid,))
        conn.commit()
        conn.close()


# ==================== 复盘分析 ====================

class Review:
    """业务复盘专用查询"""

    @staticmethod
    def session_timeline(session_id):
        """获取指定场次的完整复盘时间线"""
        conn = get_connection()
        session = conn.execute(
            "SELECT * FROM live_sessions WHERE id=?", (session_id,)
        ).fetchone()
        scenarios = conn.execute(
            """SELECT cs.*, rs.script_text, rs.effectiveness_score, rs.version
               FROM conversion_scenarios cs
               LEFT JOIN response_scripts rs ON cs.script_id = rs.id
               WHERE cs.session_id=?
               ORDER BY cs.id""",
            (session_id,)
        ).fetchall()
        conn.close()
        return {
            "session": dict(session) if session else None,
            "scenarios": [dict(s) for s in scenarios],
        }

    @staticmethod
    def cheat_sheet():
        """场景类型 → 最佳话术速查表（复盘优化后用）"""
        conn = get_connection()
        # 每个场景类型取平均转化最高的前2个trigger_action
        rows = conn.execute(
            """SELECT scenario_type, trigger_action,
                      COUNT(*) as cnt, AVG(conversion_rate_delta) as avg_delta
               FROM conversion_scenarios
               WHERE trigger_action != ''
               GROUP BY scenario_type, trigger_action
               ORDER BY scenario_type, avg_delta DESC"""
        ).fetchall()
        conn.close()

        # 按场景类型分组
        groups = {}
        for r in rows:
            stype = r["scenario_type"] or "其他"
            if stype not in groups:
                groups[stype] = []
            groups[stype].append(dict(r))

        return groups

    @staticmethod
    def daily_report():
        """今日日报"""
        today = date.today().isoformat()
        conn = get_connection()
        sessions = conn.execute(
            "SELECT * FROM live_sessions WHERE session_date=? ORDER BY id DESC", (today,)
        ).fetchall()
        scenarios = conn.execute(
            """SELECT cs.*, ls.session_date FROM conversion_scenarios cs
               LEFT JOIN live_sessions ls ON cs.session_id = ls.id
               WHERE ls.session_date=? ORDER BY cs.conversion_rate_delta DESC""", (today,)
        ).fetchall()
        # 汇总
        total_orders = sum(s["total_orders"] or 0 for s in sessions)
        total_gmv = sum(s["total_gmv"] or 0 for s in sessions)
        total_viewers = sum(s["total_viewers"] or 0 for s in sessions)
        conn.close()
        return {
            "date": today,
            "sessions": [dict(s) for s in sessions],
            "scenarios": [dict(s) for s in scenarios],
            "total_orders": total_orders,
            "total_gmv": total_gmv,
            "total_viewers": total_viewers,
        }

    @staticmethod
    def host_stats(limit=30):
        """主播表现统计"""
        conn = get_connection()
        rows = conn.execute(
            """SELECT host_name,
                      COUNT(*) as session_count,
                      SUM(total_orders) as total_orders,
                      SUM(total_gmv) as total_gmv,
                      AVG(total_viewers) as avg_viewers,
                      AVG(peak_online) as avg_peak
               FROM live_sessions
               WHERE host_name != ''
               GROUP BY host_name
               ORDER BY total_gmv DESC
               LIMIT ?""", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def script_best_by_scenario():
        """每种话术类型下评分最高的话术"""
        conn = get_connection()
        rows = conn.execute(
            """SELECT rs.*, q.question_text
               FROM response_scripts rs
               LEFT JOIN questions q ON rs.question_id = q.id
               WHERE rs.effectiveness_score >= 4.0
               ORDER BY rs.script_type, rs.effectiveness_score DESC"""
        ).fetchall()
        conn.close()
        groups = {}
        for r in rows:
            stype = r["script_type"] or "其他"
            if stype not in groups:
                groups[stype] = []
            if len(groups[stype]) < 3:
                groups[stype].append(dict(r))
        return groups


# ==================== 全局搜索 ====================

def global_search(keyword):
    """跨表搜索：问题 + 话术 + 违规词 + 场景 + 案例"""
    results = {
        "questions": Question.search(keyword, limit=10),
        "violation_rules": ViolationRule.search(keyword, limit=10),
        "violation_cases": ViolationCase.search(keyword, limit=10),
    }
    conn = get_connection()
    scripts = conn.execute(
        """SELECT rs.*, q.question_text
           FROM response_scripts rs
           LEFT JOIN questions q ON rs.question_id = q.id
           WHERE rs.script_text LIKE ? OR q.question_text LIKE ?
           ORDER BY rs.effectiveness_score DESC LIMIT 10""",
        (f"%{keyword}%", f"%{keyword}%")
    ).fetchall()
    conn.close()
    results["response_scripts"] = [dict(s) for s in scripts]
    return results
