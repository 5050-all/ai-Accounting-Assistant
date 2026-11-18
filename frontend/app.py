import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st
import pandas as pd
import requests
import altair as alt

# ===================== 后端地址与类别枚举 =====================
# 后端 FastAPI 服务：在 backend 目录执行
# python -m uvicorn app.main:app --reload --port 8000
API_URL = "http://127.0.0.1:8000"
# 类别必须与后端 schemas/transaction.py 里的 Category 枚举一致
CATEGORIES = ["餐饮", "交通", "购物", "娱乐", "医疗", "居住", "其他"]
# ============================================================

# ---------------------- 页面基础设置 ----------------------
st.set_page_config(
    page_title="AI记账助手",
    page_icon="📒",
    layout="wide"
)

menu = st.sidebar.selectbox(
    "功能菜单",
    ["一句话记账", "自然语言查账", "账单与统计"]
)

st.sidebar.divider()
st.sidebar.subheader("📖 项目说明")
st.sidebar.markdown("""
智能记账AI系统
- ✍️ 文字记账：输入消费描述自动识别
- 📷 小票识别：上传截图AI提取账单
- 📊 自动统计：柱状图+饼图分析消费
""")
st.sidebar.markdown("版本：前端演示版（对接 FastAPI 后端）")

# ---------------------- 全局状态初始化 ----------------------
# 放在所有页面分支之前，这样三个页面都能访问到
if "bill_data" not in st.session_state:
    st.session_state.bill_data = pd.DataFrame([
        {"日期": "2026-11-10", "类别": "餐饮", "金额": 24.0, "商户": "食堂", "备注": "午饭"},
        {"日期": "2026-11-11", "类别": "交通", "金额": 12.0, "商户": "滴滴", "备注": "打车"},
        {"日期": "2026-11-12", "类别": "购物", "金额": 89.0, "商户": "文具店", "备注": "文具"},
    ])
if "bill_ids" not in st.session_state:
    st.session_state.bill_ids = []


# ====================== 页面1：AI智能识别记账 ======================
if menu == "一句话记账":
    st.header("📒 AI智能识别记账")
    st.info("提示：文字描述 / 上传小票截图，AI自动识别账单，确认后才写入后端")
    st.divider()

    # ---------- 表单缓存初始化 ----------
    if "text_input_cache" not in st.session_state:
        st.session_state.text_input_cache = ""
    if "money_cache" not in st.session_state:
        st.session_state.money_cache = 0.0
    if "category_cache" not in st.session_state:
        st.session_state.category_cache = "其他"
    if "remark_cache" not in st.session_state:
        st.session_state.remark_cache = ""
    if "draft_id" not in st.session_state:
        st.session_state.draft_id = None
    if "merchant_cache" not in st.session_state:
        st.session_state.merchant_cache = ""

    st.subheader("🧾 输入文字或者上传小票")
    text_input = st.text_input(
        "文字记账，例子：午饭25、打车15、奶茶18",
        value=st.session_state.text_input_cache
    )
    upload_img = st.file_uploader(
        "上传小票、微信/支付宝截图", type=["png", "jpg", "jpeg"]
    )

    mock_money = st.session_state.money_cache
    mock_category = st.session_state.category_cache
    remark = st.session_state.remark_cache

    # ---------- 调用后端接口的函数 ----------
    def _draft_to_view(d):
        """后端 TransactionDraft → 前端显示用的字典"""
        return {
            "money": (d.get("amount_cents") or 0) / 100,
            "category": d.get("category") or "其他",
            "remark": d.get("raw_text") or "",
            "draft_id": d.get("draft_id"),
        }

    def parse_text_api(text):
        """POST /transactions/parse：文字解析"""
        try:
            res = requests.post(
                API_URL + "/transactions/parse",
                json={"text": text},       
                timeout=10
            )
            if res.status_code == 200:
                return _draft_to_view(res.json())
            st.warning(f"文字识别失败 {res.status_code}：{res.json().get('message')}")
        except Exception as e:
            st.warning(f"文字识别接口异常：{e}（请确认后端已启动）")
        return None

    def parse_image_api(img_file):
        """POST /receipts/parse：小票解析（后端目前是占位实现）"""
        try:
            # 必须显式带 (文件名, 字节内容, MIME 类型)，否则后端拿到的 content_type 是 None → 415
            mime = img_file.type or "image/png"
            res = requests.post(
                API_URL + "/receipts/parse",
                files={"file": (img_file.name, img_file.getvalue(), mime)},
                timeout=10
            )
            if res.status_code == 200:
                return _draft_to_view(res.json())
            st.warning(f"图片识别失败 {res.status_code}：{res.json().get('message')}")
        except Exception as e:
            st.warning(f"图片识别接口异常：{e}（请确认后端已启动）")
        return None

    # ---------- 文字识别 ----------
    if text_input and text_input != st.session_state.text_input_cache:
        st.session_state.text_input_cache = text_input
        api_result = parse_text_api(text_input)
        if api_result:
            mock_money = api_result["money"]
            mock_category = api_result["category"]
            remark = api_result["remark"]
            st.session_state.draft_id = api_result["draft_id"]
            st.success(f"✅【接口识别成功】{mock_category}，{mock_money} 元")
        else:
            if any(k in text_input for k in ("午饭", "晚饭", "奶茶", "吃饭")):
                mock_money, mock_category = 25, "餐饮"
            elif any(k in text_input for k in ("打车", "地铁", "公交")):
                mock_money, mock_category = 12, "交通"
            elif any(k in text_input for k in ("文具", "买")):
                mock_money, mock_category = 60, "购物"
            else:
                mock_money, mock_category = 0, "其他"
            st.info("ℹ️ 接口不可用，已用本地模拟识别，请核对下面字段")
        st.session_state.money_cache = mock_money
        st.session_state.category_cache = mock_category
        st.session_state.remark_cache = remark

    # ---------- 图片识别 ----------
    if upload_img is not None:
        st.image(upload_img, width=400)
        if st.button("开始识别小票"):
            api_result = parse_image_api(upload_img)
            if api_result:
                mock_money = api_result["money"]
                mock_category = api_result["category"]
                remark = api_result["remark"]
                st.session_state.draft_id = api_result["draft_id"]
                st.warning("⚠️ 后端小票接口目前只返回草稿，请手动核对金额和商户")
            else:
                mock_money, mock_category, remark = 0, "其他", ""
                st.warning("⚠️ 接口不可用，请手动填写下面信息")
            st.session_state.money_cache = mock_money
            st.session_state.category_cache = mock_category
            st.session_state.remark_cache = remark

    # ---------- 可编辑预览表单 ----------
    st.divider()
    st.subheader("📝 解析预览（可修改）")
    money = st.number_input(
        "金额（元）", value=float(mock_money), min_value=0.0, step=0.1
    )
    merchant = st.text_input("商户（必填）", value=st.session_state.merchant_cache)
    category = st.selectbox(
        "消费类别",
        CATEGORIES,
        index=CATEGORIES.index(mock_category) if mock_category in CATEGORIES else 0,
    )
    date = st.date_input("消费日期")
    remark = st.text_input("备注", value=remark)

    col_save, col_clear = st.columns([1, 1])
    with col_save:
        save_btn = st.button("💾 保存账单", use_container_width=True)
    with col_clear:
        clear_btn = st.button("🗑️ 清空表单", use_container_width=True)

    # ---------- 保存：真正写入后端 ----------
    if save_btn:
        if money > 0:
            payload = {
                "draft_id": st.session_state.draft_id,
                "amount_cents": int(round(money * 100)),        # 元 → 分
                "merchant": merchant.strip() or category,      # 后端必填，不能为空
                "occurred_at": f"{date}T00:00:00+08:00",       # 必须带时区
                "category": category,                          # 必须是 7 个枚举之一
                "note": remark or None,
            }
            try:
                res = requests.post(
                    API_URL + "/transactions", json=payload, timeout=10
                )
                if res.status_code == 201:                     # 后端保存成功是 201
                    saved = res.json()
                    new_row = pd.DataFrame([{
                        "日期": str(date), "类别": category, "金额": money,
                        "商户": payload["merchant"], "备注": remark,
                    }])
                    st.session_state.bill_data = pd.concat(
                        [st.session_state.bill_data, new_row], ignore_index=True
                    )
                    st.session_state.bill_ids.append(saved["id"])
                    st.session_state.draft_id = None            # 防止重复提交
                    st.session_state.merchant_cache = merchant.strip()
                    st.success("✅ 保存成功，已写入后端数据库")
                else:
                    st.error(f"保存失败 {res.status_code}：{res.json().get('message')}")
            except Exception as e:
                st.error(f"保存失败：{e}（请确认后端已启动）")
        else:
            st.error("❌ 金额必须大于 0")

    # ---------- 清空表单 ----------
    if clear_btn:
        st.session_state.text_input_cache = ""
        st.session_state.money_cache = 0.0
        st.session_state.category_cache = "其他"
        st.session_state.remark_cache = ""
        st.session_state.draft_id = None
        st.session_state.merchant_cache = ""
        st.rerun()


# ====================== 页面2：自然语言查账 ======================
elif menu == "自然语言查账":
    st.header("🔍 自然语言查账")
    st.info("用口语提问，先解析出类别和时间范围，再查真实账目")
    st.divider()

    _SHANGHAI = ZoneInfo("Asia/Shanghai")

    def local_date(iso_text):
        """后端返回 UTC，转成北京时间再取日期，避免 0~8 点显示成前一天。"""
        return datetime.fromisoformat(iso_text.replace("Z", "+00:00")).astimezone(_SHANGHAI).date()

    # ---------- 规则解析：把口语问题拆成「类别 + 时间 + 意图」 ----------
    # 关键词按顺序匹配，具体类别在前，避免「买药」被购物抢走。
    CATEGORY_KEYWORDS = (
        ("医疗", ("医疗", "医院", "看病", "买药", "药", "挂号", "体检")),
        ("居住", ("居住", "房租", "水电", "物业", "燃气", "电费", "水费")),
        ("餐饮", ("餐饮", "吃饭", "午饭", "晚饭", "早饭", "早餐", "午餐", "晚餐", "外卖", "咖啡", "奶茶", "饭", "餐")),
        ("交通", ("交通", "打车", "地铁", "公交", "加油", "车费", "出行")),
        ("娱乐", ("娱乐", "电影", "游戏", "ktv", "演唱会", "旅游", "门票")),
        ("购物", ("购物", "买东西", "淘宝", "京东", "超市", "商场", "网购", "衣服", "鞋")),
    )

    def match_time_range(text, today):
        """识别口语里的时间词，返回起止日期和展示文案。"""
        if "今天" in text or "今日" in text:
            return today, today, "今天"
        if "昨天" in text or "昨日" in text:
            day = today - timedelta(days=1)
            return day, day, "昨天"
        if "前天" in text:
            day = today - timedelta(days=2)
            return day, day, "前天"

        match = re.search(r"最近\s*(\d+)\s*天", text) or re.search(r"近\s*(\d+)\s*天", text)
        if match:
            days = max(1, int(match.group(1)))
            return today - timedelta(days=days - 1), today, f"最近 {days} 天"

        if "最近一周" in text or "近一周" in text:
            return today - timedelta(days=6), today, "最近 7 天"
        if "最近一个月" in text or "近一个月" in text:
            return today - timedelta(days=29), today, "最近 30 天"
        if "本周" in text or "这周" in text or "这个星期" in text:
            monday = today - timedelta(days=today.weekday())
            return monday, today, "本周"
        if "上周" in text or "上个星期" in text:
            this_monday = today - timedelta(days=today.weekday())
            return this_monday - timedelta(days=7), this_monday - timedelta(days=1), "上周"
        if "本月" in text or "这个月" in text or "当月" in text:
            return today.replace(day=1), today, "本月"
        if "上个月" in text or "上月" in text:
            last_month_end = today.replace(day=1) - timedelta(days=1)
            return last_month_end.replace(day=1), last_month_end, "上个月"
        if "今年" in text or "本年" in text:
            return today.replace(month=1, day=1), today, "今年"
        if "去年" in text:
            last_year = today.year - 1
            return date(last_year, 1, 1), date(last_year, 12, 31), "去年"
        return None, None, "全部时间"

    def parse_question(question):
        """把一句中文问题解析成查询条件（类别 / 时间范围 / 意图）。"""
        text = question.strip().lower()
        today = date.today()

        category = None
        for name, keywords in CATEGORY_KEYWORDS:
            if any(keyword in text for keyword in keywords):
                category = name
                break

        date_from, date_to, time_label = match_time_range(text, today)

        if any(k in text for k in ("最多", "最高", "排名", "排行", "占比", "哪一类", "哪类", "哪个类别")):
            intent, limit = "top", 10
        elif (m := re.search(r"最近\s*(\d+)\s*条", text)) or any(
            k in text for k in ("明细", "列表", "记录", "有哪些", "账单")
        ):
            intent = "list"
            limit = max(1, min(int(m.group(1)), 100)) if m else 10
        else:
            intent, limit = "sum", 10

        intent_label = {"top": "找出金额最高的类别", "list": "列出账目明细", "sum": "按类别汇总金额"}[intent]
        explanation = f"时间：{time_label}；类别：{category or '全部'}；意图：{intent_label}"
        return {
            "category": category,
            "date_from": date_from,
            "date_to": date_to,
            "intent": intent,
            "limit": limit,
            "explanation": explanation,
        }

    # ---------- 问题输入 ----------
    question = st.text_input("输入你的问题，示例：这个月吃饭花了多少钱")
    col1, col2, col3 = st.columns(3)
    example = None
    with col1:
        if st.button("这个月餐饮一共花多少", use_container_width=True):
            example = "这个月餐饮一共花多少"
    with col2:
        if st.button("哪一类消费最多", use_container_width=True):
            example = "哪一类消费最多"
    with col3:
        if st.button("查看最近3条账单", use_container_width=True):
            example = "查看最近3条账单"

    question = question or example

    st.divider()
    st.subheader("📌 查询结果")

    if not question:
        st.info("请输入问题，或点击上面的示例按钮")
    else:
        plan = parse_question(question)
        st.caption(f"解析结果 → {plan['explanation']}")

        # from / to 用当天 0 点与 23:59:59+08:00，转成 UTC 由后端处理
        params = {}
        if plan["date_from"]:
            params["from"] = f"{plan['date_from']}T00:00:00+08:00"
        if plan["date_to"]:
            params["to"] = f"{plan['date_to']}T23:59:59+08:00"

        try:
            if plan["intent"] == "list":
                query = dict(params)
                if plan["category"]:
                    query["category"] = plan["category"]
                query["limit"] = plan["limit"]
                res = requests.get(API_URL + "/transactions", params=query, timeout=10)
            else:
                res = requests.get(API_URL + "/stats/category", params=params, timeout=10)
        except Exception as e:
            st.error(f"查询失败：{e}（请确认后端已启动）")
            res = None

        if res is not None:
            if res.status_code != 200:
                st.error(f"查询失败 {res.status_code}：{res.json().get('message')}")
            else:
                data = res.json()
                if plan["intent"] == "list":
                    items = data["items"]
                    if not items:
                        st.info("这个时间段没有账目")
                    else:
                        st.dataframe(pd.DataFrame([{
                            "日期": str(local_date(t["occurred_at"])),
                            "类别": t["category"],
                            "金额": t["amount_cents"] / 100,
                            "商户": t["merchant"],
                            "备注": t.get("note") or "",
                        } for t in items]), use_container_width=True)
                else:
                    items = data["items"]
                    if plan["intent"] == "top":
                        if items:
                            top = items[0]
                            st.success(
                                f"💡 金额最高的是「{top['category']}」，"
                                f"共 {top['total_cents'] / 100:.2f} 元，{top['count']} 笔"
                            )
                    elif plan["category"]:
                        matched = [i for i in items if i["category"] == plan["category"]]
                        total_cents = matched[0]["total_cents"] if matched else 0
                        st.metric(f"{plan['category']}支出", f"{total_cents / 100:.2f} 元")
                    else:
                        st.metric("总支出", f"{data['total_cents'] / 100:.2f} 元")

                    if items:
                        st.dataframe(pd.DataFrame([{
                            "类别": i["category"],
                            "金额": i["total_cents"] / 100,
                            "笔数": i["count"],
                            "占比": f"{i['ratio']:.0%}",
                        } for i in items]), use_container_width=True)
                    else:
                        st.info("这个时间段没有账目")


# ====================== 页面3：账单与统计 ======================
elif menu == "账单与统计":
    st.header("📊 账单列表 & 消费统计")
    st.divider()

    # ---------- 优先从后端拉取账单 ----------
    backend_ok = False
    try:
        res = requests.get(API_URL + "/transactions?limit=100", timeout=10)
        if res.status_code == 200:
            data = res.json()
            st.session_state.bill_data = pd.DataFrame([{
                "日期": t["occurred_at"][:10],
                "类别": t["category"],
                "金额": t["amount_cents"] / 100,
                "商户": t["merchant"],
                "备注": t.get("note") or "",
            } for t in data["items"]])
            st.session_state.bill_ids = [t["id"] for t in data["items"]]
            backend_ok = True
    except Exception as e:
        st.warning(f"读取后端账单失败：{e}；当前显示本地演示数据")

    if not backend_ok:
        st.info("ℹ️ 后端未连接或暂无数据，显示本地演示账单")

    st.subheader("📋 全部账单")
    if not st.session_state.bill_data.empty:
        df_show = st.session_state.bill_data.copy()
        df_show.insert(0, "序号", list(range(len(df_show))))
        st.dataframe(df_show, use_container_width=True)

        st.divider()
        st.subheader("🗑️ 删除账单")
        del_index = st.number_input(
            "输入要删除账单的序号",
            min_value=0, max_value=len(st.session_state.bill_data) - 1, step=1
        )
        delete_btn = st.button("确认删除这条账单")
        if delete_btn:
            # 后端目前没有 DELETE 接口，先删本地；接口就绪后在此处补 requests.delete
            st.session_state.bill_data = (
                st.session_state.bill_data.drop(del_index).reset_index(drop=True)
            )
            if del_index < len(st.session_state.bill_ids):
                st.session_state.bill_ids.pop(del_index)
            st.success(f"✅ 序号{del_index}账单已从本地列表删除")
            st.rerun()
    else:
        st.info("暂无账单数据")

    # ---------- 统计：优先用后端 /stats/category ----------
    st.divider()
    st.subheader("📈 消费分类统计")
    group_data = None
    try:
        res = requests.get(API_URL + "/stats/category", timeout=10)
        if res.status_code == 200:
            group_data = pd.DataFrame([{
                "类别": i["category"], "金额": i["total_cents"] / 100
            } for i in res.json()["items"]])
    except Exception:
        pass

    if group_data is None or group_data.empty:
        if not st.session_state.bill_data.empty:
            group_data = (
                st.session_state.bill_data.groupby("类别")["金额"]
                .sum().reset_index()
            )

    if group_data is not None and not group_data.empty:
        col_left, col_right = st.columns(2)
        with col_left:
            st.bar_chart(group_data, x="类别", y="金额")
        with col_right:
            pie = alt.Chart(group_data).mark_arc().encode(
                theta="金额", color="类别"
            )
            st.altair_chart(pie, use_container_width=True)
    else:
        st.info("暂无账单数据")
