"""
分析引擎 — 话术对比、场景分析、排名统计
"""
from models import (
    Question, ResponseScript, ConversionScenario, ScriptABTest, ViolationRule
)
from database import get_connection


class Analyzer:
    """数据分析引擎"""

    # ---- 问题分析 ----

    @staticmethod
    def top_questions(limit=20, category=None):
        """高频问题排行榜"""
        questions = Question.get_all(
            order="frequency DESC",
            limit=limit,
            category=category
        )
        return questions

    @staticmethod
    def question_trend():
        """问题趋势：各分类占比"""
        cats = Question.categories()
        total = sum(c["cnt"] for c in cats)
        for c in cats:
            c["percentage"] = round(c["cnt"] / total * 100, 1) if total > 0 else 0
        return cats

    @staticmethod
    def sensitive_questions():
        """敏感问题列表"""
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM questions WHERE is_sensitive=1 ORDER BY frequency DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ---- 话术分析 ----

    @staticmethod
    def top_scripts(limit=10):
        """最佳话术排行"""
        return ResponseScript.top_rated(limit)

    @staticmethod
    def compare_scripts_for_question(question_id):
        """对比同一问题的所有话术版本"""
        scripts = ResponseScript.get_by_question(question_id)
        if len(scripts) < 2:
            return {"scripts": scripts, "best": scripts[0] if scripts else None,
                    "analysis": "需要至少2个版本才能对比"}

        # 综合评分 = effectiveness_score * (1 + avg_conversion_boost/10) * (1 + usage_count/100)
        scored = []
        for s in scripts:
            boost = s.get("avg_conversion_boost", 0) or 0
            usage = s.get("usage_count", 0) or 0
            score = s["effectiveness_score"] * (1 + boost / 10) * (1 + usage / 100)
            scored.append({**s, "composite_score": round(score, 2)})

        scored.sort(key=lambda x: x["composite_score"], reverse=True)

        return {
            "scripts": scored,
            "best": scored[0] if scored else None,
            "analysis": _generate_comparison_text(scored)
        }

    @staticmethod
    def script_effectiveness_ranking():
        """话术效果排名（所有话术）"""
        scripts = ResponseScript.get_all(order="effectiveness_score DESC", limit=50)
        return [
            {**s, "score": round(
                s["effectiveness_score"] * (1 + (s.get("avg_conversion_boost", 0) or 0) / 10),
                2
            )}
            for s in scripts
        ]

    # ---- 场景分析 ----

    @staticmethod
    def top_scenarios(limit=10):
        """最高转化场景"""
        return ConversionScenario.top_by_conversion(limit)

    @staticmethod
    def scenarios_by_type():
        """按场景类型分组统计"""
        conn = get_connection()
        rows = conn.execute(
            """SELECT scenario_type, COUNT(*) as count,
                      AVG(conversion_rate_delta) as avg_delta
               FROM conversion_scenarios
               GROUP BY scenario_type
               ORDER BY avg_delta DESC"""
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def best_trigger_actions(limit=10):
        """最有效的触发动作排名"""
        conn = get_connection()
        rows = conn.execute(
            """SELECT scenario_type, trigger_action,
                      AVG(conversion_rate_delta) as avg_delta,
                      COUNT(*) as count
               FROM conversion_scenarios
               WHERE trigger_action != ''
               GROUP BY trigger_action
               ORDER BY avg_delta DESC
               LIMIT ?""",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ---- A/B 测试分析 ----

    @staticmethod
    def ab_test_summary():
        """A/B 测试汇总"""
        stats = ScriptABTest.stats()
        recent = ScriptABTest.get_all(limit=10)
        return {"stats": stats, "recent_tests": recent}

    @staticmethod
    def winning_patterns():
        """话术获胜模式分析"""
        tests = ScriptABTest.get_all(limit=100)
        patterns = {
            "A胜": [],
            "B胜": [],
            "平": []
        }
        for t in tests:
            winner = t.get("winner", "")
            if winner in patterns:
                a_text = (t.get("script_a_text") or "")[:80]
                b_text = (t.get("script_b_text") or "")[:80]
                patterns[winner].append({
                    "question": t.get("question_text", ""),
                    "winner_text": a_text if winner == "A" else b_text,
                    "conclusion": t.get("conclusion", "")
                })
        return patterns

    # ---- 违规词统计 ----

    @staticmethod
    def violation_stats():
        """违规词分类统计"""
        cats = ViolationRule.categories()
        severity_order = "封禁,限流,警告"
        return {
            "categories": cats,
            "total": ViolationRule.count()
        }

    # ---- 仪表盘概览 ----

    @staticmethod
    def dashboard_overview():
        """首页仪表盘汇总数据"""
        question_trend = Analyzer.question_trend()
        top_scripts = Analyzer.top_scripts(5)
        top_scenarios = Analyzer.top_scenarios(5)
        scenario_types = Analyzer.scenarios_by_type()
        ab_summary = Analyzer.ab_test_summary()

        return {
            "question_trend": question_trend,
            "top_scripts": top_scripts,
            "top_scenarios": top_scenarios,
            "scenario_types": scenario_types,
            "ab_summary": ab_summary
        }


def _generate_comparison_text(scored_scripts):
    """生成话术对比分析文本"""
    if not scored_scripts or len(scored_scripts) < 2:
        return "数据不足，无法分析"

    best = scored_scripts[0]
    worst = scored_scripts[-1]
    lines = [
        f"最佳话术版本 {best.get('version','?')}（综合评分 {best['composite_score']}）",
        f"  - 效果评分: {best['effectiveness_score']}/5",
        f"  - 使用次数: {best.get('usage_count',0)}",
        f"  - 类型: {best.get('script_type','未知')} / 语气: {best.get('tone','未知')}",
        "",
        f"与最差版本 {worst.get('version','?')} 差距: {abs(best['composite_score'] - worst['composite_score'])} 分",
    ]

    # 分析特征
    if best.get("script_type") == worst.get("script_type") and best.get("script_type"):
        lines.append(f"提示: 同属 '{best['script_type']}' 类型，差异来自具体表达和语气")
    if best.get("tone") != worst.get("tone"):
        lines.append(f"发现: 语气 '{best.get('tone', '')}' 优于 '{worst.get('tone', '')}'")

    return "\n".join(lines)
