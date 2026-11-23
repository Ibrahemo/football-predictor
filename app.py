# -*- coding: utf-8 -*-

import math
import streamlit as st

# ============================================================
# إعداد الصفحة
# ============================================================

st.set_page_config(
    page_title="محلل المباريات",
    page_icon="⚽",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ============================================================
# التصميم
# ============================================================

st.markdown("""
<style>
html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
    font-family: Tahoma, Arial, sans-serif;
}

.stApp {
    background-color: #070707;
    color: #ffffff;
}

.block-container {
    max-width: 850px;
    padding-top: 1rem;
    padding-bottom: 4rem;
}

h1, h2, h3 {
    text-align: center;
}

.stButton > button,
.stFormSubmitButton > button {
    width: 100%;
    min-height: 55px;
    border-radius: 12px;
    border: 0;
    font-size: 18px;
    font-weight: 800;
    background: linear-gradient(135deg, #ffd95a, #b88a16);
    color: #080808;
}

div[data-testid="stMetric"] {
    background-color: #111111;
    border: 1px solid #3d3216;
    padding: 12px;
    border-radius: 14px;
}

div[data-testid="stExpander"] {
    border: 1px solid #3d3216;
    border-radius: 14px;
}

input {
    text-align: center !important;
}

hr {
    border-color: #332b17;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# دوال المحرك
# ============================================================

def poisson(goals, expected):
    return (
        math.exp(-expected)
        * expected ** goals
        / math.factorial(goals)
    )


def form_score(wins, draws, losses):

    games = wins + draws + losses

    if games <= 0:
        return 0.5

    points = wins * 3 + draws
    return points / (games * 3)


def normalize(a, b, c):

    total = a + b + c

    if total <= 0:
        return 1/3, 1/3, 1/3

    return a/total, b/total, c/total


def team_strength(team):

    games = (
        team["w"]
        + team["d"]
        + team["l"]
    )

    if games <= 0:
        games = 5

    avg_scored = team["gf"] / games
    avg_conceded = team["ga"] / games

    form = form_score(
        team["w"],
        team["d"],
        team["l"]
    )

    attack = (
        avg_scored * 0.70
        + form * 0.30
    )

    defensive_weakness = (
        avg_conceded * 0.75
        + (1 - form) * 0.25
    )

    return attack, defensive_weakness, form


def expected_goals(home, away, h2h, crowd):

    home_attack, home_weak, home_form = team_strength(home)
    away_attack, away_weak, away_form = team_strength(away)

    h_home, _, h_away = normalize(
        h2h["home"],
        h2h["draw"],
        h2h["away"]
    )

    c_home, _, c_away = normalize(
        crowd["home"],
        crowd["draw"],
        crowd["away"]
    )

    # القوة الأساسية

    home_xg = (
        home_attack * 0.58
        + away_weak * 0.42
    )

    away_xg = (
        away_attack * 0.58
        + home_weak * 0.42
    )

    # أفضلية ملعب المضيف

    home_xg *= 1.10

    # الفورمة

    form_difference = home_form - away_form

    home_xg *= 1 + form_difference * 0.12
    away_xg *= 1 - form_difference * 0.12

    # المواجهات المباشرة

    h2h_difference = h_home - h_away

    home_xg *= 1 + h2h_difference * 0.10
    away_xg *= 1 - h2h_difference * 0.10

    # تصويت الجمهور

    crowd_difference = c_home - c_away

    home_xg *= 1 + crowd_difference * 0.05
    away_xg *= 1 - crowd_difference * 0.05

    # حدود النموذج

    home_xg = max(0.20, min(home_xg, 4.00))
    away_xg = max(0.20, min(away_xg, 4.00))

    return home_xg, away_xg


def build_matrix(home_xg, away_xg, max_goals=8):

    matrix = {}

    for hg in range(max_goals + 1):

        home_probability = poisson(
            hg,
            home_xg
        )

        for ag in range(max_goals + 1):

            away_probability = poisson(
                ag,
                away_xg
            )

            matrix[(hg, ag)] = (
                home_probability
                * away_probability
            )

    total = sum(matrix.values())

    if total > 0:

        for score in matrix:
            matrix[score] /= total

    return matrix


def calculate_markets(matrix):

    result = {
        "home": 0,
        "draw": 0,
        "away": 0,

        "over15": 0,
        "under15": 0,

        "over25": 0,
        "under25": 0,

        "over35": 0,
        "under35": 0,

        "btts_yes": 0,
        "btts_no": 0,

        "home_score": 0,
        "away_score": 0
    }

    for (hg, ag), p in matrix.items():

        if hg > ag:
            result["home"] += p

        elif hg == ag:
            result["draw"] += p

        else:
            result["away"] += p

        goals = hg + ag

        if goals >= 2:
            result["over15"] += p
        else:
            result["under15"] += p

        if goals >= 3:
            result["over25"] += p
        else:
            result["under25"] += p

        if goals >= 4:
            result["over35"] += p
        else:
            result["under35"] += p

        if hg > 0 and ag > 0:
            result["btts_yes"] += p
        else:
            result["btts_no"] += p

        if hg > 0:
            result["home_score"] += p

        if ag > 0:
            result["away_score"] += p

    return result


def confidence(markets):

    probs = sorted(
        [
            markets["home"],
            markets["draw"],
            markets["away"]
        ],
        reverse=True
    )

    difference = probs[0] - probs[1]

    if difference >= 0.25:
        return "مرتفعة 🟢"

    if difference >= 0.12:
        return "متوسطة 🟡"

    return "منخفضة 🔴"


def percent(value):
    return f"{value * 100:.1f}%"


# ============================================================
# رأس التطبيق
# ============================================================

st.title("⚽ محلل مباريات كرة القدم")

st.caption(
    "تحليل إحصائي احتمالي للمباراة"
)

st.divider()


# ============================================================
# نموذج إدخال المباراة
# ============================================================

with st.form("match_form"):

    st.subheader("🏠 الفريق المضيف")

    home_name = st.text_input(
        "اسم الفريق المضيف",
        placeholder="مثال: الأهلي"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        home_w = st.number_input(
            "فوز",
            min_value=0,
            max_value=5,
            value=0,
            step=1,
            key="home_w"
        )

    with col2:
        home_d = st.number_input(
            "تعادل",
            min_value=0,
            max_value=5,
            value=0,
            step=1,
            key="home_d"
        )

    with col3:
        home_l = st.number_input(
            "خسارة",
            min_value=0,
            max_value=5,
            value=0,
            step=1,
            key="home_l"
        )

    col1, col2 = st.columns(2)

    with col1:
        home_gf = st.number_input(
            "الأهداف المسجلة في آخر 5",
            min_value=0,
            max_value=50,
            value=0,
            step=1
        )

    with col2:
        home_ga = st.number_input(
            "الأهداف المستقبلة في آخر 5",
            min_value=0,
            max_value=50,
            value=0,
            step=1
        )

    st.divider()

    # ========================================================
    # الضيف
    # ========================================================

    st.subheader("✈️ الفريق الضيف")

    away_name = st.text_input(
        "اسم الفريق الضيف",
        placeholder="مثال: الزمالك"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        away_w = st.number_input(
            "فوز الضيف",
            min_value=0,
            max_value=5,
            value=0,
            step=1
        )

    with col2:
        away_d = st.number_input(
            "تعادل الضيف",
            min_value=0,
            max_value=5,
            value=0,
            step=1
        )

    with col3:
        away_l = st.number_input(
            "خسارة الضيف",
            min_value=0,
            max_value=5,
            value=0,
            step=1
        )

    col1, col2 = st.columns(2)

    with col1:
        away_gf = st.number_input(
            "الأهداف المسجلة للضيف في آخر 5",
            min_value=0,
            max_value=50,
            value=0,
            step=1
        )

    with col2:
        away_ga = st.number_input(
            "الأهداف المستقبلة للضيف في آخر 5",
            min_value=0,
            max_value=50,
            value=0,
            step=1
        )

    st.divider()

    # ========================================================
    # المواجهات المباشرة
    # ========================================================

    st.subheader("⚔️ المواجهات المباشرة")

    st.caption(
        "أدخل النسب التاريخية للمواجهات بين الفريقين"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        h2h_home = st.number_input(
            "فوز المضيف %",
            min_value=0.0,
            max_value=100.0,
            value=33.0,
            step=1.0
        )

    with col2:
        h2h_draw = st.number_input(
            "تعادل %",
            min_value=0.0,
            max_value=100.0,
            value=34.0,
            step=1.0
        )

    with col3:
        h2h_away = st.number_input(
            "فوز الضيف %",
            min_value=0.0,
            max_value=100.0,
            value=33.0,
            step=1.0
        )

    st.divider()

    # ========================================================
    # الجمهور
    # ========================================================

    st.subheader("👥 تصويت الجمهور")

    col1, col2, col3 = st.columns(3)

    with col1:
        crowd_home = st.number_input(
            "المضيف %",
            min_value=0.0,
            max_value=100.0,
            value=33.0,
            step=1.0
        )

    with col2:
        crowd_draw = st.number_input(
            "التعادل %",
            min_value=0.0,
            max_value=100.0,
            value=34.0,
            step=1.0
        )

    with col3:
        crowd_away = st.number_input(
            "الضيف %",
            min_value=0.0,
            max_value=100.0,
            value=33.0,
            step=1.0
        )

    st.write("")

    submitted = st.form_submit_button(
        "🔥 تحليل المباراة",
        use_container_width=True
    )


# ============================================================
# تنفيذ التحليل
# ============================================================

if submitted:

    errors = []

    if not home_name.strip():
        errors.append(
            "أدخل اسم الفريق المضيف."
        )

    if not away_name.strip():
        errors.append(
            "أدخل اسم الفريق الضيف."
        )

    if home_w + home_d + home_l != 5:
        errors.append(
            "مجموع فوز وتعادل وخسارة المضيف يجب أن يساوي 5."
        )

    if away_w + away_d + away_l != 5:
        errors.append(
            "مجموع فوز وتعادل وخسارة الضيف يجب أن يساوي 5."
        )

    if (
        h2h_home
        + h2h_draw
        + h2h_away
    ) <= 0:

        errors.append(
            "أدخل نسب المواجهات المباشرة."
        )

    if (
        crowd_home
        + crowd_draw
        + crowd_away
    ) <= 0:

        errors.append(
            "أدخل نسب تصويت الجمهور."
        )

    if errors:

        for error in errors:
            st.error(error)

    else:

        home_data = {
            "w": home_w,
            "d": home_d,
            "l": home_l,
            "gf": home_gf,
            "ga": home_ga
        }

        away_data = {
            "w": away_w,
            "d": away_d,
            "l": away_l,
            "gf": away_gf,
            "ga": away_ga
        }

        h2h = {
            "home": h2h_home,
            "draw": h2h_draw,
            "away": h2h_away
        }

        crowd = {
            "home": crowd_home,
            "draw": crowd_draw,
            "away": crowd_away
        }

        home_xg, away_xg = expected_goals(
            home_data,
            away_data,
            h2h,
            crowd
        )

        matrix = build_matrix(
            home_xg,
            away_xg
        )

        markets = calculate_markets(
            matrix
        )

        scores = sorted(
            matrix.items(),
            key=lambda item: item[1],
            reverse=True
        )[:5]

        possible_outcomes = {
            "home": markets["home"],
            "draw": markets["draw"],
            "away": markets["away"]
        }

        direction = max(
            possible_outcomes,
            key=possible_outcomes.get
        )

        if direction == "home":
            direction_text = f"فوز {home_name}"

        elif direction == "away":
            direction_text = f"فوز {away_name}"

        else:
            direction_text = "التعادل"

        st.session_state["analysis_result"] = {
            "home": home_name,
            "away": away_name,
            "home_xg": home_xg,
            "away_xg": away_xg,
            "markets": markets,
            "scores": scores,
            "direction": direction_text,
            "confidence": confidence(markets)
        }


# ============================================================
# النتائج
# ============================================================

if "analysis_result" in st.session_state:

    data = st.session_state["analysis_result"]

    home = data["home"]
    away = data["away"]

    markets = data["markets"]
    scores = data["scores"]

    best_score = scores[0][0]

    st.divider()

    st.title("📊 نتيجة التحليل")

    # ========================================================
    # النتيجة الأكثر احتمالاً
    # ========================================================

    st.subheader("🔥 النتيجة الأكثر احتمالاً")

    st.title(
        f"{home}  {best_score[0]} - {best_score[1]}  {away}"
    )

    st.caption(
        "النتيجة السابقة هي أعلى نتيجة منفردة احتمالًا "
        "في مصفوفة النتائج، وليست نتيجة مضمونة."
    )

    # ========================================================
    # Expected Goals
    # ========================================================

    st.subheader("⚽ الأهداف المتوقعة")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            home,
            f"{data['home_xg']:.2f}"
        )

    with col2:
        st.metric(
            away,
            f"{data['away_xg']:.2f}"
        )

    # ========================================================
    # 1X2
    # ========================================================

    st.subheader("🏆 احتمالات المباراة")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            f"فوز {home}",
            percent(markets["home"])
        )

    with col2:
        st.metric(
            "التعادل",
            percent(markets["draw"])
        )

    with col3:
        st.metric(
            f"فوز {away}",
            percent(markets["away"])
        )

    # ========================================================
    # الاتجاه والثقة
    # ========================================================

    st.subheader("⭐ القراءة النهائية")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "اتجاه 1X2",
            data["direction"]
        )

    with col2:
        st.metric(
            "مؤشر الثقة",
            data["confidence"]
        )

    # ========================================================
    # أفضل 5 نتائج
    # ========================================================

    st.subheader("🎯 أفضل 5 نتائج محتملة")

    for index, ((hg, ag), probability) in enumerate(
        scores,
        start=1
    ):

        medal = {
            1: "🥇",
            2: "🥈",
            3: "🥉",
            4: "4️⃣",
            5: "5️⃣"
        }[index]

        st.write(
            f"{medal}  **{home} {hg} - {ag} {away}**"
            f" — {percent(probability)}"
        )

    # ========================================================
    # Over / Under
    # ========================================================

    st.subheader("⚽ إجمالي أهداف المباراة")

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "أكثر من 1.5",
            percent(markets["over15"])
        )

        st.metric(
            "أكثر من 2.5",
            percent(markets["over25"])
        )

        st.metric(
            "أكثر من 3.5",
            percent(markets["over35"])
        )

    with col2:

        st.metric(
            "أقل من 1.5",
            percent(markets["under15"])
        )

        st.metric(
            "أقل من 2.5",
            percent(markets["under25"])
        )

        st.metric(
            "أقل من 3.5",
            percent(markets["under35"])
        )

    # ========================================================
    # BTTS
    # ========================================================

    st.subheader("🥅 هل يسجل الفريقان؟")

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "نعم",
            percent(markets["btts_yes"])
        )

    with col2:

        st.metric(
            "لا",
            percent(markets["btts_no"])
        )

    # ========================================================
    # احتمال تسجيل كل فريق
    # ========================================================

    with st.expander(
        "📈 تفاصيل هجومية إضافية"
    ):

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                f"احتمال تسجيل {home}",
                percent(
                    markets["home_score"]
                )
            )

        with col2:

            st.metric(
                f"احتمال تسجيل {away}",
                percent(
                    markets["away_score"]
                )
            )

    # ========================================================
    # مباراة جديدة
    # ========================================================

    st.write("")

    if st.button(
        "🔄 مسح النتيجة",
        use_container_width=True
    ):

        del st.session_state[
            "analysis_result"
        ]

        st.rerun()


# ============================================================
# ملاحظة
# ============================================================

st.divider()

st.caption(
    "⚠️ هذا التطبيق يقدم تحليلاً إحصائياً احتماليًا. "
    "النتائج والتوقعات ليست ضمانًا لنتيجة المباراة الفعلية."
)
