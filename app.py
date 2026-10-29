"""
直播中控台 — Flask Web 主应用
启动: python app.py
本地: http://localhost:5000
局域网: http://你的IP:5000 (同事可访问)
"""
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, session
from datetime import date
from functools import wraps
import io, csv, socket

from database import init_database, get_connection
from models import (
    LiveSession, ConversionScenario, Question, ResponseScript,
    ScriptABTest, ViolationRule, ViolationCase, Review, global_search
)
from config import ACCESS_PASSWORD

app = Flask(__name__)
app.secret_key = "live_ctrl_secret_2026"

# ---- 初始化数据库 ----
init_database()


# ==================== 认证 ====================

def login_required(f):
    """如果设置了密码则要求登录，否则直接放行"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not ACCESS_PASSWORD:
            return f(*args, **kwargs)
        if session.get("logged_in"):
            return f(*args, **kwargs)
        return redirect(url_for("login_page"))
    return decorated

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if not ACCESS_PASSWORD:
        return redirect(url_for("index"))
    error = ""
    if request.method == "POST":
        if request.form.get("password") == ACCESS_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "密码错误"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


# ==================== 网络状态 ====================

def get_lan_ip():
    """获取局域网 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

@app.route("/mobile")
def mobile_page():
    """手机版快速录入页面"""
    return render_template("mobile.html")

@app.route("/review/<int:sid>")
def review_session(sid):
    """场次复盘页面"""
    data = Review.session_timeline(sid)
    if not data["session"]:
        return redirect(url_for("sessions_list"))
    # 获取所有话术用于关联选择
    scripts = ResponseScript.get_all(order="effectiveness_score DESC", limit=100)
    return render_template("review.html",
        session=data["session"], scenarios=data["scenarios"], scripts=scripts)

@app.route("/cheatsheet")
def cheat_sheet():
    """速查表"""
    scenarios = Review.cheat_sheet()
    scripts = Review.script_best_by_scenario()
    return render_template("cheatsheet.html", scenarios=scenarios, scripts=scripts)

@app.route("/daily")
def daily_report():
    """今日日报"""
    data = Review.daily_report()
    hosts = Review.host_stats()
    return render_template("daily.html", data=data, hosts=hosts)

@app.route("/status")
def status_page():
    """网络状态页 — 查看本机 IP，方便同事连接"""
    lan_ip = get_lan_ip()
    has_password = bool(ACCESS_PASSWORD)
    return render_template("status.html", lan_ip=lan_ip, has_password=has_password)

# ---- 全局认证检查 ----

@app.before_request
def check_auth():
    """所有页面（除 login/status/static）都需要认证"""
    if not ACCESS_PASSWORD:
        return None
    if request.endpoint in ("login_page", "logout", "status_page"):
        return None
    if request.path.startswith("/static"):
        return None
    if not session.get("logged_in"):
        return redirect(url_for("login_page"))


# ==================== 首页 ====================

@app.route("/")
def index():
    today_stats = LiveSession.stats_today()
    top_scenarios = ConversionScenario.top_by_conversion(5)
    top_questions = Question.get_all(order="frequency DESC", limit=10)
    top_scripts = ResponseScript.top_rated(5)
    violation_count = ViolationRule.count()
    ab_stats = ScriptABTest.stats()

    return render_template("index.html",
        today_stats=today_stats,
        top_scenarios=top_scenarios,
        top_questions=top_questions,
        top_scripts=top_scripts,
        violation_count=violation_count,
        ab_stats=ab_stats)


# ==================== 场次管理 ====================

@app.route("/sessions")
def sessions_list():
    sessions = LiveSession.get_all()
    return render_template("sessions.html", sessions=sessions)

@app.route("/sessions/add", methods=["POST"])
def session_add():
    LiveSession.create(
        session_date=request.form.get("session_date", date.today().isoformat()),
        start_time=request.form.get("start_time", ""),
        end_time=request.form.get("end_time", ""),
        platform=request.form.get("platform", "抖音"),
        host_name=request.form.get("host_name", ""),
        total_viewers=int(request.form.get("total_viewers", 0)),
        peak_online=int(request.form.get("peak_online", 0)),
        total_orders=int(request.form.get("total_orders", 0)),
        total_gmv=float(request.form.get("total_gmv", 0)),
        notes=request.form.get("notes", "")
    )
    return redirect(url_for("sessions_list"))

@app.route("/sessions/<int:sid>/edit", methods=["POST"])
def session_edit(sid):
    data = {k: v for k, v in request.form.items() if v and k != "id"}
    for field in ["total_viewers", "peak_online", "total_orders"]:
        if field in data:
            data[field] = int(data[field])
    if "total_gmv" in data:
        data["total_gmv"] = float(data["total_gmv"])
    if "start_time" in data and data["start_time"].strip() == "":
        data["start_time"] = None
    if "end_time" in data and data["end_time"].strip() == "":
        data["end_time"] = None
    LiveSession.update(sid, **data)
    return redirect(url_for("sessions_list"))

@app.route("/sessions/<int:sid>/copy", methods=["POST"])
def session_copy(sid):
    """复制场次（新建一条，继承原场次信息）"""
    original = LiveSession.get_by_id(sid)
    if original:
        LiveSession.create(
            session_date=date.today().isoformat(),
            start_time=original.get("start_time"),
            end_time=original.get("end_time"),
            platform=original.get("platform", "抖音"),
            total_viewers=0,
            peak_online=0,
            total_orders=0,
            total_gmv=0.0,
            notes=f"[复制自 {original['session_date']}] {original.get('notes','')}"
        )
    return redirect(url_for("sessions_list"))

@app.route("/sessions/<int:sid>/delete", methods=["POST"])
def session_delete(sid):
    LiveSession.delete(sid)
    return redirect(url_for("sessions_list"))


# ==================== 高转化场景 ====================

@app.route("/scenarios")
def scenarios_list():
    scenarios = ConversionScenario.get_all()
    sessions = LiveSession.get_all(order="id DESC")
    return render_template("scenarios.html", scenarios=scenarios, sessions=sessions)

@app.route("/scenarios/add", methods=["POST"])
def scenario_add():
    sid = request.form.get("script_id")
    ConversionScenario.create(
        session_id=int(request.form.get("session_id", 0)),
        timestamp=request.form.get("timestamp", ""),
        scenario_type=request.form.get("scenario_type", ""),
        trigger_action=request.form.get("trigger_action", ""),
        before_orders=int(request.form.get("before_orders", 0)),
        after_orders=int(request.form.get("after_orders", 0)),
        conversion_rate_delta=float(request.form.get("conversion_rate_delta", 0)),
        chat_atmosphere=request.form.get("chat_atmosphere", ""),
        tags=request.form.get("tags", ""),
        script_id=int(sid) if sid else None
    )
    return redirect(url_for("scenarios_list"))

@app.route("/scenarios/<int:cid>/edit", methods=["POST"])
def scenario_edit(cid):
    data = {k: v for k, v in request.form.items() if k != "id"}
    # 过滤空值但保留必要的字段
    cleaned = {}
    for k, v in data.items():
        if v == "" or v is None:
            if k == "script_id":
                cleaned[k] = None  # 允许清空关联
            continue
        cleaned[k] = v
    for field in ["session_id", "before_orders", "after_orders", "script_id"]:
        if field in cleaned and cleaned[field] is not None:
            cleaned[field] = int(cleaned[field])
    if "conversion_rate_delta" in cleaned:
        cleaned["conversion_rate_delta"] = float(cleaned["conversion_rate_delta"])
    ConversionScenario.update(cid, **cleaned)
    return redirect(url_for("scenarios_list"))

@app.route("/scenarios/<int:cid>/delete", methods=["POST"])
def scenario_delete(cid):
    ConversionScenario.delete(cid)
    return redirect(url_for("scenarios_list"))


# ==================== 问题库 ====================

@app.route("/questions")
def questions_list():
    category = request.args.get("category", "")
    questions = Question.get_all(category=category if category else None)
    categories = Question.categories()
    return render_template("questions.html",
        questions=questions, categories=categories, current_category=category)

@app.route("/questions/add", methods=["POST"])
def question_add():
    Question.create_or_update(
        question_text=request.form.get("question_text", ""),
        category=request.form.get("category", ""),
        difficulty=request.form.get("difficulty", "中等"),
        is_sensitive=bool(request.form.get("is_sensitive"))
    )
    return redirect(url_for("questions_list"))

@app.route("/questions/<int:qid>/edit", methods=["POST"])
def question_edit(qid):
    data = {k: v for k, v in request.form.items() if v and k != "id"}
    if "is_sensitive" in data:
        data["is_sensitive"] = int(data["is_sensitive"])
    if "frequency" in data:
        data["frequency"] = int(data["frequency"])
    Question.update(qid, **data)
    return redirect(url_for("questions_list"))

@app.route("/questions/<int:qid>/delete", methods=["POST"])
def question_delete(qid):
    Question.delete(qid)
    return redirect(url_for("questions_list"))

@app.route("/questions/<int:qid>")
def question_detail(qid):
    q = Question.get_by_id(qid)
    if not q:
        return redirect(url_for("questions_list"))
    scripts = ResponseScript.get_by_question(qid)
    return render_template("question_detail.html", question=q, scripts=scripts)


# ==================== 话术库 ====================

@app.route("/scripts")
def scripts_list():
    scripts = ResponseScript.get_all()
    questions = Question.get_all(order="question_text ASC", limit=200)
    return render_template("scripts.html", scripts=scripts, questions=questions)

@app.route("/scripts/add", methods=["POST"])
def script_add():
    ResponseScript.create(
        question_id=int(request.form.get("question_id", 0)),
        script_text=request.form.get("script_text", ""),
        version=request.form.get("version", "v1.0"),
        script_type=request.form.get("script_type", "标准应答"),
        tone=request.form.get("tone", "专业"),
        author=request.form.get("author", ""),
        effectiveness_score=float(request.form.get("effectiveness_score", 3.0)),
        notes=request.form.get("notes", "")
    )
    return redirect(url_for("scripts_list"))

@app.route("/scripts/<int:sid>/edit", methods=["POST"])
def script_edit(sid):
    data = {k: v for k, v in request.form.items() if v and k != "id"}
    if "question_id" in data:
        data["question_id"] = int(data["question_id"])
    if "effectiveness_score" in data:
        data["effectiveness_score"] = float(data["effectiveness_score"])
    ResponseScript.update(sid, **data)
    return redirect(url_for("scripts_list"))

@app.route("/scripts/<int:sid>/delete", methods=["POST"])
def script_delete(sid):
    ResponseScript.delete(sid)
    return redirect(url_for("scripts_list"))

@app.route("/scripts/<int:sid>/use", methods=["POST"])
def script_use(sid):
    """记录话术使用次数"""
    ResponseScript.increment_usage(sid)
    return jsonify({"status": "ok"})


# ==================== A/B 测试 ====================

@app.route("/ab-tests")
def ab_tests_list():
    tests = ScriptABTest.get_all()
    questions = Question.get_all(order="question_text ASC", limit=200)
    return render_template("ab_tests.html", tests=tests, questions=questions)

@app.route("/ab-tests/add", methods=["POST"])
def ab_test_add():
    ScriptABTest.create(
        question_id=int(request.form.get("question_id", 0)),
        script_a_id=int(request.form.get("script_a_id", 0)),
        script_b_id=int(request.form.get("script_b_id", 0)),
        winner=request.form.get("winner", ""),
        metric_a=float(request.form.get("metric_a", 0)),
        metric_b=float(request.form.get("metric_b", 0)),
        conclusion=request.form.get("conclusion", ""),
        session_id=int(request.form.get("session_id", 0)) or None
    )
    return redirect(url_for("ab_tests_list"))

@app.route("/api/session/<int:sid>")
def api_session_detail(sid):
    """AJAX: 获取单个场次详情"""
    s = LiveSession.get_by_id(sid)
    if s:
        return jsonify(s)
    return jsonify({"error": "not found"}), 404

@app.route("/api/scenario/<int:cid>")
def api_scenario_detail(cid):
    """AJAX: 获取单个场景详情"""
    s = ConversionScenario.get_by_id(cid)
    if s:
        return jsonify(s)
    return jsonify({"error": "not found"}), 404

@app.route("/api/scripts")
def api_scripts_list():
    """AJAX: 获取所有话术列表（用于下拉选择）"""
    scripts = ResponseScript.get_all(order="effectiveness_score DESC", limit=200)
    return jsonify(scripts)

@app.route("/api/questions/<int:qid>/scripts")
def api_question_scripts(qid):
    """AJAX: 获取某问题下的所有话术（用于 A/B 测试选择）"""
    scripts = ResponseScript.get_by_question(qid)
    return jsonify(scripts)


# ==================== 违规管理 ====================

@app.route("/violations")
def violations_list():
    category = request.args.get("category", "")
    rules = ViolationRule.get_all(category=category if category else None)
    cases = ViolationCase.get_all()
    categories = ViolationRule.categories()
    return render_template("violations.html",
        rules=rules, cases=cases, categories=categories, current_category=category)

@app.route("/violations/check", methods=["POST"])
def violation_check():
    """实时违规词检查"""
    text = request.form.get("text", "")
    hits = ViolationRule.check_text(text)
    return render_template("_violation_check_result.html", hits=hits, text=text)

@app.route("/violations/add", methods=["POST"])
def violation_add():
    ViolationRule.create(
        keyword=request.form.get("keyword", ""),
        category=request.form.get("category", ""),
        severity=request.form.get("severity", "警告"),
        alternative=request.form.get("alternative", ""),
        source=request.form.get("source", "")
    )
    return redirect(url_for("violations_list"))

@app.route("/violations/<int:vid>/delete", methods=["POST"])
def violation_delete(vid):
    ViolationRule.delete(vid)
    return redirect(url_for("violations_list"))

@app.route("/cases/add", methods=["POST"])
def case_add():
    ViolationCase.create(
        case_title=request.form.get("case_title", ""),
        platform=request.form.get("platform", "抖音"),
        brand_name=request.form.get("brand_name", ""),
        violation_type=request.form.get("violation_type", ""),
        original_content=request.form.get("original_content", ""),
        penalty=request.form.get("penalty", ""),
        lesson=request.form.get("lesson", ""),
        preventive_measure=request.form.get("preventive_measure", ""),
        occurred_date=request.form.get("occurred_date", ""),
        source_url=request.form.get("source_url", "")
    )
    return redirect(url_for("violations_list"))

@app.route("/cases/<int:cid>/delete", methods=["POST"])
def case_delete(cid):
    ViolationCase.delete(cid)
    return redirect(url_for("violations_list"))


# ==================== 搜索页 ====================

@app.route("/search")
def search_page():
    keyword = request.args.get("q", "")
    results = None
    if keyword:
        results = global_search(keyword)
    return render_template("search.html", keyword=keyword, results=results)


# ==================== 数据导入 ====================

@app.route("/import")
def import_page():
    return render_template("import.html")

@app.route("/import/preview", methods=["POST"])
def import_preview():
    """上传文件并预览"""
    file = request.files.get("file")
    import_type = request.form.get("type", "violations")
    if not file:
        return jsonify({"error": "请选择文件"}), 400

    try:
        filename = (file.filename or "").lower()
        file_data = file.read()

        # Word 文档
        if filename.endswith(".docx"):
            from importer import Importer as Imp
            columns, rows = Imp.parse_docx_bytes(file_data)
        # Excel
        elif filename.endswith((".xlsx", ".xls")):
            from importer import Importer as Imp
            columns, rows = Imp.parse_excel_bytes(file_data)
        # CSV (默认)
        else:
            content = file_data.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(content))
            rows = [dict(r) for r in reader]
            columns = list(rows[0].keys()) if rows else []

        return render_template("_import_preview.html",
            rows=rows, columns=columns, import_type=import_type,
            filename=file.filename, total=len(rows))
    except Exception as e:
        return jsonify({"error": f"文件解析失败: {str(e)}"}), 400

@app.route("/import/execute", methods=["POST"])
def import_execute():
    """执行导入"""
    import_type = request.form.get("type", "")
    data = request.form.get("data", "[]")
    import json
    rows = json.loads(data)

    imported = 0
    skipped = 0

    if import_type == "violations":
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

    elif import_type == "cases":
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

    elif import_type == "questions":
        for row in rows:
            Question.create_or_update(
                question_text=row.get("question_text", ""),
                category=row.get("category", ""),
                difficulty=row.get("difficulty", "中等"),
                is_sensitive=bool(int(row.get("is_sensitive", 0)))
            )
            imported += 1

    return jsonify({"imported": imported, "skipped": skipped})


# ==================== 报表导出 ====================

@app.route("/export/<string:data_type>")
def export_csv(data_type):
    from reporter import export_to_csv
    buffer = export_to_csv(data_type)
    if buffer is None:
        return "Invalid type", 400

    filename_map = {
        "questions": "问题库.csv",
        "scripts": "话术库.csv",
        "scenarios": "高转化场景.csv",
        "violations": "违规词库.csv",
        "cases": "违规案例.csv",
        "sessions": "直播场次.csv",
    }
    return send_file(
        buffer,
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename_map.get(data_type, f"{data_type}.csv")
    )


# ==================== 启动 ====================

if __name__ == "__main__":
    import os as _os
    lan_ip = get_lan_ip()
    debug_mode = _os.environ.get("FLASK_ENV") != "production"
    print(f"""
+==============================================+
|   Live Stream Control Panel v1.0              |
|                                               |
|   Local:   http://127.0.0.1:5000              |
|   Network: http://{lan_ip}:5000          |
|                                               |
|   Password: {"SET" if ACCESS_PASSWORD else "OFF (open access)"}              |
|   Debug:    {"ON" if debug_mode else "OFF"}                     |
+==============================================+
    """)
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
