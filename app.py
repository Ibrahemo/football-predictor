# -*- coding: utf-8 -*-

import math
import streamlit as st


# ==========================================================
# إعداد التطبيق
# ==========================================================

st.set_page_config(
    page_title="توقعات كرة القدم",
    page_icon="⚽",
    layout="centered",
    initial_sidebar_state="collapsed"
)


# ==========================================================
# التصميم
# ==========================================================

st.markdown("""
<style>

html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
    font-family: Tahoma, Arial, sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at top, #211a08 0%, #0b0b0b 38%, #030303 100%);
    color: white;
}

.block-container {
    max-width: 850px;
    padding-top: 1rem;
    padding-bottom: 4rem;
}

.title {
    text-align: center;
    color: #f4c542;
    font-size: 34px;
    font-weight: 900;
    margin-bottom: 5px;
}

.subtitle {
    text-align: center;
    color: #aaa;
    font-size: 15px;
    margin-bottom: 25px;
}

.section-title {
    color: #f4c542;
    font-size: 22px;
    font-weight: 900;
    margin-top: 25px;
    margin-bottom: 10px;
    border-right: 5px solid #f4c542;
    padding-right: 10px;
}

div[data-baseweb="input"] > div {
    background-color: #151515 !important;
    border: 1px solid #44391a !important;
    border-radius: 10px !important;
}

input {
    color: white !important;
    text-align: center !important;
}

label {
    color: #eeeeee !important;
    font-weight: 700 !important;
}

.stButton > button,
.stFormSubmitButton > button {
    width: 100%;
    border-radius: 12px;
    min-height: 52px;
    font-size: 18px;
    font-weight: 900;
    background: linear-gradient(135deg, #ffd95a, #b88711);
    color: #090909;
    border: none;
}

.result-card {
    background: linear-gradient(145deg, #141414, #090909);
    border: 1px solid #413617;
    border-radius: 16px;
    padding: 18px;
    margin: 15px 0;
}

.card-title {
    text-align: center;
    color: #f4c542;
    font-size: 21px;
    font-weight: 900;
    margin-bottom: 15px;
}

.score {
    text-align: center;
    color: white;
    font-size: 35px;
    font-weight: 900;
    padding: 12px 0;
}

.row {
    font-size: 17px;
    padding: 9px;
    border-bottom: 1px solid #222;
}

.home {
    color: #36d98b;
    font-weight: 900;
}

.draw {
    color: #5aa7ff;
    font-weight: 900;
}

.away {
    color: #ff6767;
    font-weight: 900;
}

.gold {
    color: #f4c542;
    font-weight: 900;
}

.center {
    text-align: center;
}

.note {
    text-align: center;
    color: #777;
    font-size: 12px;
    margin-top: 30px;
}

</style>
""", unsafe_allow_html=True)


# ==========================================================
# دوال الحساب
# ==========================================================

def poisson(k, lam):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def form_score(wins, draws, losses):

    games = wins + draws + losses

    if games == 0:
        return 0.5

    return ((wins * 3) + draws) / (games * 3)


def normalize(a, b, c):

    total = a + b + c

    if total <= 0:
        return 1 / 3, 1 / 3, 1 / 3

    return a / total, b / total, c / total


def team_strength(team):

    games = (
        team["wins"]
        + team["draws"]
        + team["losses"]
    )

    if games <= 0:
        games = 5

    goals_scored = team["gf"] / games
    goals_conceded = team["ga"] / games

    form = form_score(
        team["wins"],
        team["draws"],
        team["losses"]
    )

    attack = (
        goals_scored * 0.70
        + form * 0.30
    )

    defensive_weakness = (
        goals_conceded * 0.75
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

    # القوة الهجومية والدفاعية

    home_xg = (
        home_attack * 0.58
        + away_weak * 0.42
    )

    away_xg = (
        away_attack * 0.58
        + home_weak * 0.42
    )

    # أفضلية الأرض

    home_xg *= 1.10

    # الفورمة

    form_difference = home_form - away_form

    home_xg *= 1 + (form_difference * 0.12)
    away_xg *= 1 - (form_difference * 0.12)

    # المواجهات المباشرة

    h2h_difference = h_home - h_away

    home_xg *= 1 + (h2h_difference * 0.10)
    away_xg *= 1 - (h2h_difference * 0.10)

    # الجمهور

    crowd_difference = c_home - c_away

    home_xg *= 1 + (crowd_difference * 0.05)
    away_xg *= 1 - (crowd_difference * 0.05)

    # حدود منطقية للنموذج

    home_xg = max(0.20, min(home_xg, 4.00))
    away_xg = max(0.20, min(away_xg, 4.00))

    return home_xg, away_xg


def score_matrix(home_xg, away_xg, max_goals=8):

    matrix = {}

    for hg in range(max_goals + 1):

        ph = poisson(hg, home_xg)

        for ag in range(max_goals + 1):

            pa = poisson(ag, away_xg)

            matrix[(hg, ag)] = ph * pa

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
    }

    for (hg, ag), probability in matrix.items():

        # نتيجة المباراة

        if hg > ag:
            result["home"] += probability

        elif hg == ag:
            result["draw"] += probability

        else:
            result["away"] += probability

        total_goals = hg + ag

        # Over / Under

        if total_goals >= 2:
            result["over15"] += probability
        else:
            result["under15"] += probability

        if total_goals >= 3:
            result["over25"] += probability
        else:
            result["under25"] += probability

        if total_goals >= 4:
            result["over35"] += probability
        else:
            result["under35"] += probability

        # الفريقان يسجلان

        if hg > 0 and ag > 0:
            result["btts_yes"] += probability
        else:
            result["btts_no"] += probability

    return result


def confidence(markets):

    values = sorted(
        [
            markets["home"],
            markets["draw"],
            markets["away"]
        ],
        reverse=True
    )

    difference = values[0] - values[1]

    if difference >= 0.25:
        return "مرتفعة", "🟢"

    elif difference >= 0.12:
        return "متوسطة", "🟡"

    return "منخفضة", "🔴"


def percentage(value):
    return f"{value * 100:.1f}%"


# ==========================================================
# العنوان
# ==========================================================

st.markdown("""
<div class="title">
    ⚽ توقعات كرة القدم
</div>

<div class="subtitle">
    تحليل احتمالي للمباريات
</div>
""", unsafe_allow_html=True)


# ==========================================================
# نموذج البيانات
# ==========================================================

with st.form("match_form"):

    # ------------------------------------------------------
    # الفريق المضيف
    # ------------------------------------------------------

    st.markdown(
        '<div class="section-title">🏠 الفريق المضيف</div>',
        unsafe_allow_html=True
    )

    home_name = st.text_input(
        "اسم الفريق المضيف",
        placeholder="مثال: الأهلي"
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        home_wins = st.number_input(
            "فوز",
            0,
            5,
            0
        )

    with c2:
        home_draws = st.number_input(
            "تعادل",
            0,
            5,
            0
        )

    with c3:
        home_losses = st.number_input(
            "خسارة",
            0,
            5,
            0
        )

    c1, c2 = st.columns(2)

    with c1:
        home_gf = st.number_input(
            "الأهداف المسجلة",
            0,
            50,
            0,
            key="home_gf"
        )

    with c2:
        home_ga = st.number_input(
            "الأهداف المستقبلة",
            0,
            50,
            0,
            key="home_ga"
        )

    # ------------------------------------------------------
    # الفريق الضيف
    # ------------------------------------------------------

    st.markdown(
        '<div class="section-title">✈️ الفريق الضيف</div>',
        unsafe_allow_html=True
    )

    away_name = st.text_input(
        "اسم الفريق الضيف",
        placeholder="مثال: الزمالك"
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        away_wins = st.number_input(
            "فوز الضيف",
            0,
            5,
            0
        )

    with c2:
        away_draws = st.number_input(
            "تعادل الضيف",
            0,
            5,
            0
        )

    with c3:
        away_losses = st.number_input(
            "خسارة الضيف",
            0,
            5,
            0
        )

    c1, c2 = st.columns(2)

    with c1:
        away_gf = st.number_input(
            "الأهداف المسجلة للضيف",
            0,
            50,
            0
        )

    with c2:
        away_ga = st.number_input(
            "الأهداف المستقبلة للضيف",
            0,
            50,
            0
        )

    # ------------------------------------------------------
    # H2H
    # ------------------------------------------------------

    st.markdown(
        '<div class="section-title">⚔️ المواجهات المباشرة</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "أدخل نسب جميع المواجهات التاريخية بين الفريقين"
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        h2h_home = st.number_input(
            "فوز المضيف %",
            0.0,
            100.0,
            33.0
        )

    with c2:
        h2h_draw = st.number_input(
            "التعادل %",
            0.0,
            100.0,
            34.0
        )

    with c3:
        h2h_away = st.number_input(
            "فوز الضيف %",
            0.0,
            100.0,
            33.0
        )

    # ------------------------------------------------------
    # الجمهور
    # ------------------------------------------------------

    st.markdown(
        '<div class="section-title">👥 تصويت الجمهور</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        crowd_home = st.number_input(
            "تصويت المضيف %",
            0.0,
            100.0,
            33.0
        )

    with c2:
        crowd_draw = st.number_input(
            "تصويت التعادل %",
            0.0,
            100.0,
            34.0
        )

    with c3:
        crowd_away = st.number_input(
            "تصويت الضيف %",
            0.0,
            100.0,
            33.0
        )

    st.write("")

    submitted = st.form_submit_button(
        "🔥 تحليل المباراة",
        use_container_width=True
    )


# ==========================================================
# إجراء التحليل
# ==========================================================

if submitted:

    error = None

    if not home_name.strip():

        error = "أدخل اسم الفريق المضيف"

    elif not away_name.strip():

        error = "أدخل اسم الفريق الضيف"

    elif (
        home_wins
        + home_draws
        + home_losses
    ) != 5:

        error = (
            "مجموع الفوز والتعادل والخسارة "
            "للفريق المضيف يجب أن يساوي 5"
        )

    elif (
        away_wins
        + away_draws
        + away_losses
    ) != 5:

        error = (
            "مجموع الفوز والتعادل والخسارة "
            "للفريق الضيف يجب أن يساوي 5"
        )

    elif (
        h2h_home
        + h2h_draw
        + h2h_away
    ) <= 0:

        error = "أدخل نسب المواجهات المباشرة"

    elif (
        crowd_home
        + crowd_draw
        + crowd_away
    ) <= 0:

        error = "أدخل نسب تصويت الجمهور"

    if error:

        st.error(error)

    else:

        home_data = {
            "wins": home_wins,
            "draws": home_draws,
            "losses": home_losses,
            "gf": home_gf,
            "ga": home_ga
        }

        away_data = {
            "wins": away_wins,
            "draws": away_draws,
            "losses": away_losses,
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

        matrix = score_matrix(
            home_xg,
            away_xg
        )

        markets = calculate_markets(
            matrix
        )

        top_scores = sorted(
            matrix.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        confidence_text, confidence_icon = confidence(
            markets
        )

        possibilities = {
            "home": markets["home"],
            "draw": markets["draw"],
            "away": markets["away"]
        }

        best_direction = max(
            possibilities,
            key=possibilities.get
        )

        if best_direction == "home":
            direction = f"فوز {home_name}"

        elif best_direction == "away":
            direction = f"فوز {away_name}"

        else:
            direction = "التعادل"

        st.session_state["analysis"] = {
            "home_name": home_name,
            "away_name": away_name,
            "home_xg": home_xg,
            "away_xg": away_xg,
            "markets": markets,
            "scores": top_scores,
            "confidence": confidence_text,
            "confidence_icon": confidence_icon,
            "direction": direction
        }


# ==========================================================
# عرض النتيجة
# ==========================================================

if "analysis" in st.session_state:

    data = st.session_state["analysis"]

    home = data["home_name"]
    away = data["away_name"]

    markets = data["markets"]
    scores = data["scores"]

    best_score = scores[0][0]

    st.markdown("---")

    st.markdown(
        '<div class="title">📊 نتيجة التحليل</div>',
        unsafe_allow_html=True
    )

    # ------------------------------------------------------
    # النتيجة المتوقعة
    # ------------------------------------------------------

    st.markdown(
        f"""
        <div class="result-card">

            <div class="card-title">
                🔥 النتيجة الأكثر احتمالًا
            </div>

            <div class="score">
                {home}
                &nbsp;
                {best_score[0]} - {best_score[1]}
                &nbsp;
                {away}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    # ------------------------------------------------------
    # Expected Goals
    # ------------------------------------------------------

    st.markdown(
        f"""
        <div class="result-card">

            <div class="card-title">
                ⚽ الأهداف المتوقعة
            </div>

            <div class="row home">
                {home}: {data["home_xg"]:.2f}
            </div>

            <div class="row away">
                {away}: {data["away_xg"]:.2f}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    # ------------------------------------------------------
    # 1X2
    # ------------------------------------------------------

    st.markdown(
        f"""
        <div class="result-card">

            <div class="card-title">
                🏆 احتمالات المباراة
            </div>

            <div class="row home">
                فوز {home}:
                {percentage(markets["home"])}
            </div>

            <div class="row draw">
                التعادل:
                {percentage(markets["draw"])}
            </div>

            <div class="row away">
                فوز {away}:
                {percentage(markets["away"])}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    # ------------------------------------------------------
    # أفضل 5 نتائج
    # ------------------------------------------------------

    st.markdown(
        '<div class="section-title">🎯 أفضل 5 نتائج محتملة</div>',
        unsafe_allow_html=True
    )

    medals = [
        "🥇",
        "🥈",
        "🥉",
        "4️⃣",
        "5️⃣"
    ]

    for index, ((hg, ag), probability) in enumerate(scores):

        st.markdown(
            f"""
            <div class="result-card center">

                <span style="font-size:20px;">
                    {medals[index]}
                </span>

                &nbsp;&nbsp;

                <span style="font-size:22px;font-weight:900;">
                    {hg} - {ag}
                </span>

                &nbsp;&nbsp;

                <span class="gold">
                    {percentage(probability)}
                </span>

            </div>
            """,
            unsafe_allow_html=True
        )

    # ------------------------------------------------------
    # إجمالي الأهداف
    # ------------------------------------------------------

    st.markdown(
        f"""
        <div class="result-card">

            <div class="card-title">
                ⚽ إجمالي الأهداف
            </div>

            <div class="row">
                أكثر من 1.5:
                <span class="gold">
                    {percentage(markets["over15"])}
                </span>
            </div>

            <div class="row">
                أقل من 1.5:
                <span class="gold">
                    {percentage(markets["under15"])}
                </span>
            </div>

            <div class="row">
                أكثر من 2.5:
                <span class="gold">
                    {percentage(markets["over25"])}
                </span>
            </div>

            <div class="row">
                أقل من 2.5:
                <span class="gold">
                    {percentage(markets["under25"])}
                </span>
            </div>

            <div class="row">
                أكثر من 3.5:
                <span class="gold">
                    {percentage(markets["over35"])}
                </span>
            </div>

            <div class="row">
                أقل من 3.5:
                <span class="gold">
                    {percentage(markets["under35"])}
                </span>
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    # ------------------------------------------------------
    # BTTS
    # ------------------------------------------------------

    st.markdown(
        f"""
        <div class="result-card">

            <div class="card-title">
                🥅 هل يسجل الفريقان؟
            </div>

            <div class="row home">
                نعم:
                {percentage(markets["btts_yes"])}
            </div>

            <div class="row away">
                لا:
                {percentage(markets["btts_no"])}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    # ------------------------------------------------------
    # التوقع النهائي
    # ------------------------------------------------------

    st.markdown(
        f"""
        <div class="result-card">

            <div class="card-title">
                ⭐ التوقع النهائي
            </div>

            <div class="score">
                {home}
                &nbsp;
                {best_score[0]} - {best_score[1]}
                &nbsp;
                {away}
            </div>

            <div class="center" style="font-size:18px;padding:8px;">
                اتجاه المباراة:
                <span class="gold">
                    {data["direction"]}
                </span>
            </div>

            <div class="center" style="font-size:19px;padding:8px;">
                مؤشر الثقة:
                {data["confidence_icon"]}
                <strong>
                    {data["confidence"]}
                </strong>
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button(
        "🔄 مباراة جديدة",
        use_container_width=True
    ):

        del st.session_state["analysis"]

        st.rerun()


# ==========================================================
# تنبيه
# ==========================================================

st.markdown(
    """
    <div class="note">
        ⚠️ التحليل إحصائي واحتمالي ولا يضمن النتيجة الفعلية للمباراة.
    </div>
    """,
    unsafe_allow_html=True
)
