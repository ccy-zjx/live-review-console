"""
批量导入器 — 支持 CSV / Excel / Word / JSON 数据导入
"""
import csv
import io
import json
from models import ViolationRule, ViolationCase, Question
from database import get_connection


class Importer:
    """批量数据导入"""

    @staticmethod
    def parse_csv(content: str):
        """解析 CSV 文本，返回列名 + 行数据列表"""
        reader = csv.DictReader(io.StringIO(content))
        rows = [dict(r) for r in reader]
        columns = list(rows[0].keys()) if rows else []
        return columns, rows

    @staticmethod
    def parse_excel_bytes(data: bytes):
        """解析 Excel 二进制数据 (需要 openpyxl)"""
        try:
            from openpyxl import load_workbook
        except ImportError:
            raise ImportError("请先安装 openpyxl: pip install openpyxl")

        wb = load_workbook(io.BytesIO(data), read_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        headers = [str(h) for h in next(rows_iter)]
        rows = []
        for row in rows_iter:
            rows.append({headers[i]: str(v) if v is not None else ""
                         for i, v in enumerate(row) if i < len(headers)})
        return headers, rows

    @staticmethod
    def parse_docx_bytes(data: bytes):
        """解析 Word 文档中的表格（飞书导出格式）"""
        try:
            from docx import Document
        except ImportError:
            raise ImportError("请先安装 python-docx: pip install python-docx")

        doc = Document(io.BytesIO(data))
        tables = doc.tables
        if not tables:
            raise ValueError("Word 文档中没有找到表格！请在飞书中用表格组织数据后再导出。")

        # 使用第一个表格
        table = tables[0]
        rows_data = []
        headers = []

        for i, row in enumerate(table.rows):
            cells = [cell.text.strip() for cell in row.cells]
            if i == 0:
                headers = cells
            else:
                if any(c for c in cells):  # 跳过全空行
                    rows_data.append({headers[j]: cells[j] if j < len(cells) else ""
                                      for j in range(len(headers))})

        return headers, rows_data

    @staticmethod
    def parse_docx_text(data: bytes):
        """解析 Word 文档中的纯文本段落（无表格时按行拆分）"""
        try:
            from docx import Document
        except ImportError:
            raise ImportError("请先安装 python-docx: pip install python-docx")

        doc = Document(io.BytesIO(data))
        lines = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            # 尝试按常见分隔符拆分
            if '\t' in text:
                lines.append(text)
            else:
                lines.append(text)

        return lines

    @staticmethod
    def import_violations(rows: list) -> tuple:
        """导入违规词"""
        imported, skipped = 0, 0
        for row in rows:
            rid = ViolationRule.create(
                keyword=row.get("keyword", ""),
                category=row.get("category", ""),
                severity=row.get("severity", "警告"),
                platform=row.get("platform", "抖音"),
                alternative=row.get("alternative", ""),
                source=row.get("source", "")
            )
            if rid:
                imported += 1
            else:
                skipped += 1
        return imported, skipped

    @staticmethod
    def import_cases(rows: list) -> int:
        """导入违规案例"""
        imported = 0
        for row in rows:
            ViolationCase.create(
                case_title=row.get("case_title", ""),
                platform=row.get("platform", "抖音"),
                brand_name=row.get("brand_name", ""),
                violation_type=row.get("violation_type", ""),
                original_content=row.get("original_content", ""),
                penalty=row.get("penalty", ""),
                lesson=row.get("lesson", ""),
                preventive_measure=row.get("preventive_measure", ""),
                occurred_date=row.get("occurred_date", ""),
                source_url=row.get("source_url", "")
            )
            imported += 1
        return imported

    @staticmethod
    def import_questions(rows: list) -> tuple:
        """导入问题库"""
        imported, updated = 0, 0
        for row in rows:
            qid = Question.create_or_update(
                question_text=row.get("question_text", ""),
                category=row.get("category", ""),
                difficulty=row.get("difficulty", "中等"),
                is_sensitive=bool(int(row.get("is_sensitive", 0)))
            )
            q = Question.get_by_id(qid)
            if q and q.get("frequency", 1) <= 1:
                imported += 1
            else:
                updated += 1
        return imported, updated

    @staticmethod
    def import_from_file(filepath: str, data_type: str) -> dict:
        """从文件自动识别格式并导入"""
        if filepath.endswith(".csv"):
            with open(filepath, "r", encoding="utf-8-sig") as f:
                columns, rows = Importer.parse_csv(f.read())
        elif filepath.endswith((".xlsx", ".xls")):
            with open(filepath, "rb") as f:
                columns, rows = Importer.parse_excel_bytes(f.read())
        elif filepath.endswith(".docx"):
            with open(filepath, "rb") as f:
                columns, rows = Importer.parse_docx_bytes(f.read())
        elif filepath.endswith(".json"):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                rows = data if isinstance(data, list) else data.get("rows", [])
                columns = list(rows[0].keys()) if rows else []
        else:
            return {"error": f"不支持的文件格式: {filepath}"}

        if data_type == "violations":
            imported, skipped = Importer.import_violations(rows)
            return {"imported": imported, "skipped": skipped, "total": len(rows)}
        elif data_type == "cases":
            imported = Importer.import_cases(rows)
            return {"imported": imported, "total": len(rows)}
        elif data_type == "questions":
            imported, updated = Importer.import_questions(rows)
            return {"imported": imported, "updated": updated, "total": len(rows)}
        else:
            return {"error": f"未知数据类型: {data_type}"}
