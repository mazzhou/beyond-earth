"""
منطق اللعبة: كل الحسابات هنا، والواجهة في app.py
كل الأرقام من ناسا:
  - الكواكب البعيدة: NASA Exoplanet Archive (تنجاب مباشرة)
  - القمر والمريخ والزهرة: NASA Planetary Fact Sheet (nssdc.gsfc.nasa.gov/planetary/factsheet)
  - العواصف الشمسية: NASA DONKI (ccmc.gsfc.nasa.gov/DONKI-API)
"""
import csv
import io
import math
from datetime import date, timedelta

import requests  # بدون pandas: عشان حماية ويندوز ما توقف اللعبة


def num(v):
    """يحول أي قيمة لرقم، ولو فاضية يرجع None"""
    try:
        if v is None or str(v).strip() in ("", "nan", "None"):
            return None
        x = float(v)
        return None if x != x else x
    except (TypeError, ValueError):
        return None


def isna(v):
    return num(v) is None

TAP_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
DONKI_URL = "https://ccmc.gsfc.nasa.gov/DONKI-API/get/FLR"
LY_KM = 9.461e12          # كم كيلومتر في السنة الضوئية
VOYAGER_KMS = 17          # سرعة أسرع مركبة بعيدة عندنا (Voyager 1) كم/ثانية

# ---------------------------------------------------------------
# المجموعة الشمسية: الحجم والجاذبية من جدول ناسا (Planetary Fact Sheet - Ratio to Earth Values)
# الحرارة = متوسط الحرارة في نفس الجدول، والضوء (insol) محسوب من بعد الكوكب عن الشمس: 1 ÷ المسافة²
# ---------------------------------------------------------------
SOLAR_SYSTEM = [
    {
        "id": "moon", "name": "Moon", "nickname": "🌕 جارنا القمر",
        "radius": 0.2724, "insol": 1.0, "gravity": 0.166, "temp_C": -20,
        "trip": "3 أيام بالصاروخ 🚀", "air": "ما فيه هواء أبد", "water": "🧊 جليد بس", "danger": "🔴 عالي",
        "fact": "يومه الواحد يطول تقريبًا شهر كامل!",
        "verdict": "practical",
    },
    {
        "id": "mars", "name": "Mars", "nickname": "🔴 الكوكب الأحمر",
        "radius": 0.533, "insol": 0.431, "gravity": 0.377, "temp_C": -65,
        "trip": "7 شهور بالصاروخ 🚀", "air": "هواء خفيف جدًا وما ينفع نتنفسه", "water": "🧊 جليد تحت الأرض", "danger": "🟠 متوسط",
        "fact": "فيه أعلى بركان بالمجموعة الشمسية!",
        "verdict": "best_real",
    },
    {
        "id": "venus", "name": "Venus", "nickname": "🟡 الزهرة الجميلة",
        "radius": 0.949, "insol": 1.911, "gravity": 0.907, "temp_C": 464,
        "trip": "5 شهور بالصاروخ 🚀", "air": "هواء سام وثقيل جدًا", "water": "❌ ما فيه", "danger": "🔴 عالي جدًا",
        "fact": "حجمها قد الأرض، بس حرارتها تذوّب الرصاص!",
        "verdict": "trap",
    },
    {
        "id": "jupiter", "name": "Jupiter", "nickname": "🟠 المشتري العملاق",
        "radius": 11.21, "insol": 0.037, "gravity": 2.36, "temp_C": -110,
        "trip": "6 سنين بالصاروخ 🚀", "air": "هيدروجين وهيليوم، ما ينفع نتنفسه", "water": "❌ ما فيه سطح",
        "danger": "🔴 عالي جدًا",
        "fact": "ما فيه أرض تقف عليها! كله غيوم وغازات",
        "verdict": "gas",
    },
    {
        "id": "saturn", "name": "Saturn", "nickname": "🪐 زحل أبو الحلقات",
        "radius": 9.45, "insol": 0.011, "gravity": 0.916, "temp_C": -140,
        "trip": "7 سنين بالصاروخ 🚀", "air": "هيدروجين وهيليوم، ما ينفع نتنفسه", "water": "❌ ما فيه سطح",
        "danger": "🔴 عالي جدًا",
        "fact": "خفيف لدرجة إنه لو فيه بحر كبير كفاية... بيطفو عليه!",
        "verdict": "gas",
    },
]

# أسماء دلع للكواكب المعروفة (أي كوكب ثاني ياخذ اسم تلقائي)
NICKNAMES = {
    "Kepler-442 b": "🌏 كبلر 442b ابن عم الأرض",
    "Kepler-452 b": "🌏 كبلر 452b ابن عم الأرض",
    "Kepler-186 f": "🌏 كبلر 186f الكوكب الأحمر الصغير",
    "Proxima Cen b": "🏠 الجار الأقرب",
    "TRAPPIST-1 e": "🌗 كوكب نص نهار نص ليل",
    "Teegarden's Star b": "🧥 الكوكب أبو جاكيت",
    "Wolf 1069 b": "👯 توأم الأرض البعيد",
    "TOI-700 d": "🔭 اكتشاف تلسكوب ناسا",
}


# ---------------------------------------------------------------
# الحسابات
# ---------------------------------------------------------------
def esi(radius, insol):
    """Earth Similarity Index (Schulze-Makuch et al. 2011): 1 = الأرض تمامًا"""
    radius, insol = num(radius), num(insol)
    if radius is None or insol is None:
        return None
    return 1 - math.sqrt(0.5 * (((insol - 1) / (insol + 1)) ** 2 + ((radius - 1) / (radius + 1)) ** 2))


def stars(score):
    n = max(0, min(5, round(score * 5)))
    return "⭐" * n + "☆" * (5 - n)


def weather(t):
    if t is None or isna(t):
        return "❓ ما نعرف"
    if t > 100:
        return "🔥 يذوّب كل شي"
    if t > 40:
        return "🥵 حار مرة"
    if t > 10:
        return "☀️ دافي"
    if t > -30:
        return "🧥 بارد، البس جاكيت"
    return "🥶 متجمد"


def weather_short(t):
    if t is None or isna(t):
        return "❓ ما نعرف"
    if t > 100:
        return "🔥 نار"
    if t > 40:
        return "🥵 حار"
    if t > 10:
        return "☀️ دافي"
    if t > -30:
        return "🥶 بارد"
    return "🧊 متجمد"


# 🌍 المهمة الأرضية: كل كوكب يعلّمك شي ينقذ الأرض
EARTH_MISSIONS = {
    "practical": "💡 القاعدة على القمر تعيش على طاقة الشمس وتوفرها. مهمتك اليوم: طفّي أي نور ما تحتاجه في البيت!",
    "best_real": "🚿 على المريخ كل نقطة ماء غالية. مهمتك اليوم: سكّر الماي وإنت تفرش أسنانك!",
    "trap": "🌡️ الزهرة حارة لأن غازات تحبس الحرارة، ونفس الشي يصير للأرض بشكل أخف. مهمتك: امشِ مع أهلك لمشوار قريب بدل السيارة!",
    "gas": "🌱 هواء المشتري ما ينفع نتنفسه، وهواء الأرض نعمة. مهمتك: ازرع نبتة أو اسقِ وحدة، لأن النباتات تنظف الهواء!",
    "far_twin": "🌍 حتى أقرب توأم للأرض بعيد آلاف السنين. مهمتك: ارمِ الزبالة في مكانها، وحافظ على الكوكب الوحيد اللي عندنا!",
}


DANGERS = ["🔥 الحر الشديد", "🥶 البرد الشديد", "🌬️ ما فيه هواء", "🛰️ المسافة البعيدة جدًا"]


def danger_answer(p):
    """الإجابة الصحيحة لسؤال: وش أكبر خطر هنا؟"""
    if p.get("verdict") == "far_twin":
        return DANGERS[3]
    t = p.get("temp_C")
    if t is not None and not isna(t) and t > 100:
        return DANGERS[0]
    if p.get("air", "").startswith("ما فيه"):
        return DANGERS[2]
    return DANGERS[1]


DANGER_WHY = {
    DANGERS[0]: "الحرارة هناك تذوّب المعادن! ما فيه بدلة تتحملها لفترة طويلة.",
    DANGERS[1]: "البرد هناك أقوى من أبرد مكان في القطب الجنوبي، فلازم قواعد مدفّاة.",
    DANGERS[2]: "ما فيه هواء أبد! برا القاعدة لازم بدلة فضاء فيها أكسجين.",
    DANGERS[3]: "حتى لو الكوكب حلو، الوصول له ياخذ مئات آلاف السنين بمركباتنا الحالية.",
}


def size_text(r):
    if 0.8 <= r <= 1.25:
        return "🔵 قد الأرض"
    return "🔹 أصغر من الأرض" if r < 0.8 else "🔷 أكبر من الأرض"


def jump_text(g):
    if g is None or isna(g) or g <= 0:
        return "❓ ما نعرف"
    times = 1 / g
    if 0.85 <= times <= 1.15:
        return "🦘 نفس نطتك في الأرض"
    if times > 1:
        return f"🦘 تنط أعلى {times:.1f} مرة!"
    return f"🐢 نطتك أقصر {1 / times:.1f} مرة"


def trip_text(distance_ly):
    years = distance_ly * LY_KM / VOYAGER_KMS / 3.156e7
    return f"{years:,.0f} سنة بأسرع مركبة عندنا 🛰️"


# ---------------------------------------------------------------
# جلب الداتا من ناسا
# ---------------------------------------------------------------
def fetch_exoplanets(timeout=60):
    """يجيب الكواكب من NASA Exoplanet Archive، ولو ما فيه نت يقرا ملف النوتبوك"""
    query = """
    select pl_name, hostname, pl_rade, pl_insol, pl_eqt, pl_bmasse, pl_orbper, sy_dist, st_spectype, disc_year, disc_facility
    from pscomppars
    where pl_rade is not null and pl_insol is not null and sy_dist is not null
    """
    try:
        r = requests.get(TAP_URL, params={"query": query, "format": "csv"}, timeout=timeout)
        r.raise_for_status()
        return list(csv.DictReader(io.StringIO(r.text))), "live"
    except Exception:
        # خطة احتياطية: الملف اللي طلع من النوتبوك (data/nasa_exoplanets_esi.csv)
        for path in ["nasa_exoplanets_esi.csv", "data/nasa_exoplanets_esi.csv"]:
            try:
                with open(path, encoding="utf-8") as f:
                    return list(csv.DictReader(f)), "file"
            except Exception:
                pass
    return [], "none"


def exo_to_planet(row):
    """يحول صف من أرشيف ناسا لبطاقة كوكب"""
    radius, insol = num(row["pl_rade"]), num(row["pl_insol"])
    mass = num(row.get("pl_bmasse"))
    gravity = mass / radius ** 2 if mass is not None else None
    eqt = num(row.get("pl_eqt"))
    temp = eqt - 273.15 if eqt is not None else None
    dist = num(row["sy_dist"]) * 3.26156
    spec = str(row.get("st_spectype") or "")
    red_dwarf = spec.startswith("M")
    period = num(row.get("pl_orbper"))

    if red_dwarf and period is not None and period < 30:
        fact = "نصه نهار على طول، ونصه ليل على طول!"
    elif red_dwarf:
        fact = "شمسه حمراء صغيرة، وسماه برتقالية!"
    else:
        year = num(row.get("disc_year"))
        fact = f"اكتشفوه سنة {int(year)}!" if year else "كوكب غامض!"

    return {
        "id": row["pl_name"], "name": row["pl_name"],
        "nickname": NICKNAMES.get(row["pl_name"], f"🪐 {row['pl_name']}"),
        "radius": radius, "insol": insol, "gravity": gravity, "temp_C": temp,
        "distance_ly": dist, "trip": trip_text(dist),
        "air": "ما نعرف، ما أحد زاره", "water": "❓ ممكن",
        "danger": "🔴 عالي" if red_dwarf else "🟡 ما نعرف",
        "fact": fact, "verdict": "far_twin",
        "raw": {k: (num(row.get(k)) if num(row.get(k)) is not None else row.get(k) or None) for k in ["pl_rade", "pl_insol", "pl_eqt", "pl_bmasse", "pl_orbper", "sy_dist", "st_spectype", "disc_facility"]},
    }


KEPLER_PICKS = ["Kepler-442 b", "Kepler-452 b", "Kepler-186 f"]   # كوكب من تلسكوب كبلر حق ناسا


def pick_exoplanets(rows, n=3):
    """يختار أكثر الكواكب الصخرية شبهًا بالأرض، ودايمًا يضمن وجود كوكب من تلسكوب كبلر"""
    rocky = []
    for r in rows:
        rad, ins, eqt, dist = num(r.get("pl_rade")), num(r.get("pl_insol")), num(r.get("pl_eqt")), num(r.get("sy_dist"))
        if None in (rad, ins, eqt, dist) or rad > 1.6:
            continue
        rocky.append((esi(rad, ins), r))
    rocky.sort(key=lambda x: x[0], reverse=True)
    chosen = [r for _, r in rocky[:n]]
    if not any(str(r.get("pl_name", "")).startswith("Kepler") for r in chosen):
        by_name = {r.get("pl_name"): r for r in rows}
        for name in KEPLER_PICKS:
            r = by_name.get(name)
            if r and None not in (num(r.get("pl_rade")), num(r.get("pl_insol")), num(r.get("sy_dist"))):
                chosen = chosen[:n - 1] + [r]
                break
    return [exo_to_planet(r) for r in chosen]


def build_planets(exo_df, n_exo=3):
    planets = [dict(p) for p in SOLAR_SYSTEM]
    for p in planets:
        p["raw"] = {"radius (Earth=1)": p["radius"], "gravity (Earth=1)": p["gravity"], "mean temp °C": p["temp_C"]}
    planets += pick_exoplanets(exo_df, n_exo)
    for p in planets:
        p["esi"] = esi(p["radius"], p["insol"])
    return planets


def fetch_solar_alert(days=7, timeout=30):
    """آخر انفجار شمسي قوي (M أو X) من NASA DONKI، ولو ما فيه يرجع None"""
    end, start = date.today(), date.today() - timedelta(days=days)
    try:
        r = requests.get(DONKI_URL, params={"startDate": start, "endDate": end}, timeout=timeout)
        r.raise_for_status()
        flares = [f for f in r.json() if str(f.get("classType", "")).startswith(("M", "X"))]
        if not flares:
            return {"level": "calm", "count": 0}
        last = flares[-1]
        return {"level": "X" if last["classType"].startswith("X") else "M",
                "class": last["classType"], "time": last.get("peakTime") or last.get("beginTime"),
                "count": len(flares)}
    except Exception:
        return None


# ---------------------------------------------------------------
# نتيجة الاختيار (الدرس العلمي)
# ---------------------------------------------------------------
RESULTS = {
    "practical": ("🌕 خيار ذكي للبداية!", "info", [
        "✅ قريب، توصله في 3 أيام بس",
        "✅ مكان ممتاز نتدرب فيه",
        "⚠️ ما فيه هواء، والإشعاع قوي",
        "💡 ناسا راجعة له مع برنامج Artemis!",
    ]),
    "best_real": ("🔴 أفضل خيار واقعي اليوم!", "success", [
        "✅ فيه جليد ماء",
        "✅ يومه قريب من يومنا (24 ساعة و40 دقيقة)",
        "⚠️ بارد مرة، وهواه خفيف ما نتنفسه",
        "💡 العلماء يشوفونه الخطوة الجاية بعد القمر",
    ]),
    "trap": ("😱 فخ! الزهرة تشبه الأرض بالحجم بس!", "error", [
        "❌ حرارتها 464° مئوية",
        "❌ هواها سام",
        "🤔 أخذت نجوم كثير لأن حجمها قد الأرض",
        "💡 الدرس: الرقم الواحد ما يقول كل شي، افحص كل شي 🔬",
    ]),
    "gas": ("☁️ ما فيه أرض نبني عليها!", "error", [
        "❌ كوكب غازي، كله غيوم بدون سطح",
        "❌ الضغط يزيد كل ما نزلت لتحت",
        "🤩 بس أقماره فيها جليد، والعلماء يدرسونها!",
        "💡 الدرس: مو كل كوكب كبير ينفع نعيش فيه",
    ]),
    "far_twin": ("🪐 توأم بعيد!", "warning", [
        "✅ حجمه وجوه يشبهون الأرض",
        "❓ ما نعرف إذا فيه هواء أو ماء",
        "❌ بعيد مرة، والرحلة تاخذ مئات آلاف السنين",
        "💡 حلم المستقبل، بس اليوم ما نقدر نوصله",
    ]),
}

