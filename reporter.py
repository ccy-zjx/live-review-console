"""
报表导出 — CSV / Excel 导出功能
"""
import csv
import io
from database import get_connection

EXPORT_COLUMNS = {
    "sessions": [
        ("id", "ID"), ("session_date", "日期"), ("start_time", "开始时间"),
        ("end_time", "结束时间"), ("platform", "平台"), ("total_viewers", "观看人数"),
        ("peak_online", "峰值在线"), ("total_orders", "订单数"),
        ("total_gmv", "GMV"), ("notes", "备注")
    ],
    "scenarios": [
        ("id", "ID"), ("session_id", "场次ID"), ("session_date", "场次日期"),
        ("timestamp", "时间"), ("scenario_type", "场景类型"),
        ("trigger_action", "触发动作"), ("before_orders", "前订单"),
        ("after_orders", "后订单"), ("conversion_rate_delta", "转化提升"),
        ("chat_atmosphere", "弹幕氛围"), ("tags", "标签")
    ],
    "questions": [
        ("id", "ID"), ("question_text", "问题"), ("category", "分类"),
        ("frequency", "频次"), ("difficulty", "难度"),
        ("is_sensitive", "敏感"), ("first_seen", "首次出现"),
        ("last_seen", "最近出现")
    ],
    "scripts": [
        ("id", "ID"), ("question_id", "问题ID"), ("question_text", "关联问题"),
        ("version", "版本"), ("script_text", "话术内容"),
        ("script_type", "类型"), ("tone", "语气"), ("author", "作者"),
        ("effectiveness_score", "效果评分"), ("usage_count", "使用次数"),
        ("avg_conversion_boost", "转化提升"), ("notes", "备注")
    ],
    "violations": [
        ("id", "ID"), ("keyword", "违规词"), ("category", "分类"),
        ("severity", "严重度"), ("platform", "平台"),
        ("alternative", "替代说法"), ("source", "来源"), ("added_date", "收录日期")
    ],
    "cases": [
        ("id", "ID"), ("case_title", "案例标题"), ("platform", "平台"),
        ("brand_name", "品牌"), ("violation_type", "违规类型"),
        ("original_content", "违规原文"), ("penalty", "处罚"),
        ("lesson", "教训"), ("preventive_measure", "预防措施"),
        ("occurred_date", "发生日期"), ("source_url", "来源链接")
    ],
}

TABLE_MAP = {
    "sessions": "live_sessions",
    "scenarios": "conversion_scenarios",
    "questions": "questions",
    "scripts": "response_scripts",
    "violations": "violation_rules",
    "cases": "violation_cases",
}


def export_to_csv(data_type):
    """导出指定数据表为 CSV（返回 BytesIO buffer）"""
    if data_type not in TABLE_MAP:
        return None

    table = TABLE_MAP[data_type]
    columns = EXPORT_COLUMNS.get(data_type)

    conn = get_connection()
    if data_type == "scenarios":
        rows = conn.execute(
            """SELECT cs.*, ls.session_date
               FROM conversion_scenarios cs
               LEFT JOIN live_sessions ls ON cs.session_id = ls.id
               ORDER BY cs.id DESC"""
        ).fetchall()
    elif data_type == "scripts":
        rows = conn.execute(
            """SELECT rs.*, q.question_text
               FROM response_scripts rs
               LEFT JOIN questions q ON rs.question_id = q.id
               ORDER BY rs.id DESC"""
        ).fetchall()
    else:
        rows = conn.execute(f"SELECT * FROM {table} ORDER BY id DESC").fetchall()
    conn.close()

    buffer = io.StringIO()
    buffer.write("﻿")  # BOM for Excel Chinese support

    if columns:
        writer = csv.writer(buffer)
        writer.writerow([c[1] for c in columns])
        for row in rows:
            r = dict(row)
            writer.writerow([r.get(c[0], "") for c in columns])

    buffer.seek(0)
    return buffer
