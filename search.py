"""
全局搜索 + 违规词检查
"""
from models import ViolationRule, Question, global_search as gs


class Search:
    """全局检索"""

    @staticmethod
    def all(keyword):
        """跨表搜索所有内容"""
        return gs(keyword)

    @staticmethod
    def check_violations(text):
        """检查文本中的违规词，返回命中的规则 + 替代建议"""
        hits = ViolationRule.check_text(text)

        # 生成修正建议
        suggestion = text
        for hit in hits:
            keyword = hit["keyword"]
            alternative = hit.get("alternative", "")
            if alternative and "(禁止" not in alternative:
                suggestion = suggestion.replace(keyword, alternative)
            elif "(禁止" in str(alternative):
                # 用 [已移除] 标记
                suggestion = suggestion.replace(keyword, "***")

        return {
            "original": text,
            "hits": hits,
            "hit_count": len(hits),
            "suggestion": suggestion,
            "is_safe": len(hits) == 0,
            "severity_level": _max_severity(hits)
        }

    @staticmethod
    def find_script_for_question(keyword):
        """根据关键词查找问题 → 返回最匹配的问题和话术"""
        questions = Question.search(keyword, limit=5)
        results = []
        for q in questions:
            qid = q["id"]
            from models import ResponseScript
            scripts = ResponseScript.get_by_question(qid)
            results.append({
                "question": q,
                "scripts": scripts
            })
        return results


def _max_severity(hits):
    """返回命中的最高严重级别"""
    if not hits:
        return "安全"
    severity_order = {"封禁": 3, "限流": 2, "警告": 1}
    max_sev = max(severity_order.get(h.get("severity", ""), 0) for h in hits)
    for k, v in severity_order.items():
        if v == max_sev:
            return k
    return "未知"
