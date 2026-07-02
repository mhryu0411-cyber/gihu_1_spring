import streamlit as st
import folium
from streamlit_folium import st_folium
import sqlite3
import json
from datetime import date, datetime

# ─── 페이지 설정 ───
st.set_page_config(page_title="🌸 벚꽃 개화 제보", layout="wide", page_icon="🌸")

# ─── CSS ───
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    div[data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #FFF0F5, #FFFFFF);
    }
    .report-card {
        padding: 12px 16px; margin-bottom: 8px;
        border-radius: 10px; background: #FFF5F7;
        border-left: 4px solid #FF69B4;
    }
    .report-card h4 { margin: 0 0 4px; font-size: 15px; }
    .report-card p { margin: 2px 0; font-size: 13px; color: #666; }
    .title-area { text-align: center; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)

# ─── DB ───
def get_db():
    conn = sqlite3.connect("reports.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lat REAL NOT NULL, lng REAL NOT NULL,
        location_name TEXT, bloom_date TEXT NOT NULL,
        note TEXT, created_at TEXT DEFAULT (datetime('now','localtime'))
    )""")
    return conn

db = get_db()

def add_report(lat, lng, name, bloom_date, note):
    db.execute("INSERT INTO reports (lat,lng,location_name,bloom_date,note) VALUES (?,?,?,?,?)",
               (lat, lng, name, bloom_date, note))
    db.commit()

def get_reports():
    return db.execute("SELECT * FROM reports ORDER BY created_at DESC").fetchall()

def delete_report(rid):
    db.execute("DELETE FROM reports WHERE id=?", (rid,))
    db.commit()

# ─── 세션 초기화 ───
if "click_lat" not in st.session_state:
    st.session_state.click_lat = None
    st.session_state.click_lng = None

# ─── 사이드바: 제보 폼 ───
with st.sidebar:
    st.markdown("## 🌸 벚꽃 개화 제보")
    st.caption("지도를 클릭하여 위치를 선택한 뒤 아래 정보를 입력하세요.")
    st.divider()

    if st.session_state.click_lat:
        st.success(f"📍 선택 좌표: {st.session_state.click_lat:.5f}, {st.session_state.click_lng:.5f}")
    else:
        st.info("📍 지도를 클릭해 위치를 선택하세요")

    loc_name = st.text_input("장소명", placeholder="예: 여의도 윤중로")
    bloom_date = st.date_input("📅 개화 확인 날짜", value=date.today())
    note = st.text_area("📝 메모 (선택)", placeholder="개화 정도, 날씨 등 자유롭게")

    if st.button("🌸 제보 등록", use_container_width=True, type="primary"):
        if st.session_state.click_lat and bloom_date:
            add_report(
                st.session_state.click_lat,
                st.session_state.click_lng,
                loc_name,
                str(bloom_date),
                note
            )
            st.session_state.click_lat = None
            st.session_state.click_lng = None
            st.toast("🌸 제보가 등록되었습니다!")
            st.rerun()
        else:
            st.warning("지도에서 위치를 먼저 클릭해주세요.")

    st.divider()
    st.markdown("### 📋 제보 목록")
    reports = get_reports()
    if not reports:
        st.caption("아직 제보가 없습니다.")
    for r in reports:
        st.markdown(f"""<div class="report-card">
            <h4>🌸 {r['location_name'] or '제보 위치'}</h4>
            <p>📅 {r['bloom_date']}</p>
            {'<p>📝 '+r['note']+'</p>' if r['note'] else ''}
            <p style="font-size:11px;color:#aaa">{r['created_at'] or ''}</p>
        </div>""", unsafe_allow_html=True)

# ─── 메인: 지도 ───
st.markdown('<div class="title-area"><h2>🌸 봄철 벚꽃 개화 제보 지도</h2><p style="color:#888">지도를 클릭하여 벚꽃 개화 위치를 제보하세요</p></div>', unsafe_allow_html=True)

m = folium.Map(
    location=[36.5, 127.8],
    zoom_start=7,
    min_zoom=6,
    max_bounds=True,
    tiles="CartoDB positron"
)
m.fit_bounds([[33, 124], [39, 132]])

reports = get_reports()
for r in reports:
    folium.Marker(
        [r["lat"], r["lng"]],
        popup=folium.Popup(
            f"<b>{r['location_name'] or '제보 위치'}</b><br>"
            f"📅 {r['bloom_date']}<br>"
            f"{r['note'] or ''}",
            max_width=250
        ),
        icon=folium.DivIcon(
            html='<div style="font-size:28px;filter:drop-shadow(0 2px 3px rgba(0,0,0,.3))">🌸</div>',
            icon_size=(28, 28),
            icon_anchor=(14, 14)
        )
    ).add_to(m)

if st.session_state.click_lat:
    folium.Marker(
        [st.session_state.click_lat, st.session_state.click_lng],
        icon=folium.DivIcon(
            html='<div style="font-size:32px">📌</div>',
            icon_size=(32, 32), icon_anchor=(16, 16)
        )
    ).add_to(m)

map_data = st_folium(m, width=None, height=600, returned_objects=["last_clicked"])

if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lng = map_data["last_clicked"]["lng"]
    if 33 <= lat <= 39 and 124 <= lng <= 132:
        st.session_state.click_lat = lat
        st.session_state.click_lng = lng
        st.rerun()
