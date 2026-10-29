"""
数据采集器 — 面向程序化调用，提供批量数据录入能力
"""
from models import (
    LiveSession, ConversionScenario, Question, ResponseScript
)
from datetime import date, datetime


class Collector:
    """直播数据录入辅助类"""

    # ---- 场次快速创建 ----
    @staticmethod
    def start_session(start_time=None, platform="抖音"):
        """开播时调用，返回 session_id"""
        if start_time is None:
            start_time = datetime.now().strftime("%H:%M")
        return LiveSession.create(
            session_date=date.today().isoformat(),
            start_time=start_time,
            platform=platform
        )

    @staticmethod
    def end_session(session_id, total_orders=0, total_gmv=0.0,
                    total_viewers=0, peak_online=0):
        """下播时调用，更新场次数据"""
        LiveSession.update(
            session_id,
            end_time=datetime.now().strftime("%H:%M"),
            total_viewers=total_viewers,
            peak_online=peak_online,
            total_orders=total_orders,
            total_gmv=total_gmv
        )

    # ---- 高转化场景快照 ----
    @staticmethod
    def capture_scenario(session_id, scenario_type, trigger_action,
                         before_orders, after_orders, chat_atmosphere="",
                         tags=""):
        """记录一个转化飙升的时刻"""
        delta = after_orders - before_orders
        return ConversionScenario.create(
            session_id=session_id,
            timestamp=datetime.now().strftime("%H:%M:%S"),
            scenario_type=scenario_type,
            trigger_action=trigger_action,
            before_orders=before_orders,
            after_orders=after_orders,
            conversion_rate_delta=delta,
            chat_atmosphere=chat_atmosphere,
            tags=tags
        )

    # ---- 问题/话术收录 ----
    @staticmethod
    def log_question(question_text, category="", difficulty="中等",
                     is_sensitive=False):
        """记录一个问题（自动去重累加频次）"""
        return Question.create_or_update(
            question_text=question_text,
            category=category,
            difficulty=difficulty,
            is_sensitive=is_sensitive
        )

    @staticmethod
    def add_script(question_id, script_text, version="v1.0",
                   script_type="标准应答", tone="专业", author="",
                   effectiveness_score=3.0, notes=""):
        """添加一条应答话术"""
        return ResponseScript.create(
            question_id=question_id,
            script_text=script_text,
            version=version,
            script_type=script_type,
            tone=tone,
            author=author,
            effectiveness_score=effectiveness_score,
            notes=notes
        )

    # ---- 批量导入（从列表） ----
    @staticmethod
    def batch_log_questions(questions_list):
        """
        questions_list: [(text, category, difficulty, is_sensitive), ...]
        返回: (imported, updated)
        """
        imported, updated = 0, 0
        for item in questions_list:
            text, cat, diff, sens = item[0], item[1] if len(item) > 1 else "", \
                                    item[2] if len(item) > 2 else "中等", \
                                    item[3] if len(item) > 3 else False
            qid = Question.create_or_update(text, cat, diff, sens)
            # 由于 create_or_update 返回已有 id 或新 id，
            # 简单判断：frequency == 1 说明是新建
            q = Question.get_by_id(qid)
            if q and q.get("frequency", 0) == 1:
                imported += 1
            else:
                updated += 1
        return imported, updated
