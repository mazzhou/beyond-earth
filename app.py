"""
🚀 Beyond Earth: Junior Astronaut Trainer
التشغيل:   python -m streamlit run app.py

البايثون يجيب داتا ناسا (game_logic.py)، وشاشة اللعبة نفسها في game.html
"""
import base64
import json
from pathlib import Path

import game_logic as gl

HERE = Path(__file__).parent


def build_game_html(planets, alert):
    """يحط داتا ناسا داخل صفحة اللعبة"""
    bg_path = HERE / "assets" / "earth_intro.jpg"
    bg = "data:image/jpeg;base64," + base64.b64encode(bg_path.read_bytes()).decode() if bg_path.exists() else ""
    data = {
        "planets": planets,
        "alert": alert,
        "results": gl.RESULTS,
        "earth": gl.EARTH_MISSIONS,
        "bg": bg,
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return (HERE / "game.html").read_text(encoding="utf-8").replace("__DATA__", payload)


if __name__ == "__main__":
    import streamlit as st
    import streamlit.components.v1 as components

    st.set_page_config(page_title="Beyond Earth", page_icon="🚀", layout="wide")
    st.markdown(
        "<style>#MainMenu,footer,header,[data-testid='stToolbar'],[data-testid='stDecoration']{display:none!important}"
        ".block-container{padding:0!important;max-width:100%!important}"
        ".stApp{background:#0b0d10}iframe{display:block;border:none}</style>",
        unsafe_allow_html=True,
    )

    @st.cache_data(ttl=3600, show_spinner="📡 نتصل بناسا...")
    def load_data():
        exo_rows, _source = gl.fetch_exoplanets()
        return gl.build_planets(exo_rows), gl.fetch_solar_alert()

    planets, alert = load_data()
    components.html(build_game_html(planets, alert), height=860, scrolling=False)
