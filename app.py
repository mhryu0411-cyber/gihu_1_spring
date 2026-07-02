import streamlit as st
import folium
from streamlit_folium import st_folium
from collections import defaultdict
import sqlite3
from datetime import date, datetime, timedelta

# ─── 페이지 설정 ───
st.set_page_config(page_title="벚꽃 개화 제보", layout="wide", page_icon="🌸")

# ─── 세션 초기화 ───
if "click_lat" not in st.session_state: st.session_state.click_lat = None
if "click_lng" not in st.session_state: st.session_state.click_lng = None
if "map_center" not in st.session_state: st.session_state.map_center = [36.5, 127.8]
if "map_zoom" not in st.session_state: st.session_state.map_zoom = 7
if "is_admin" not in st.session_state: st.session_state.is_admin = False

# ─── CSS (우측 끝 강제 고정 및 눈이 편한 배경색) ───
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    
    /* 2) 🕶️ 메인 화면 배경: 눈이 편안하고 부드러운 벚꽃 힌트 오프화이트 컬러 */
    .stApp {
        background-color: #FAF5F6 !important;
    }
    
    /* 왼쪽 사이드바 그라데이션 고정 */
    [data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #FFE4E1 0%, #FFF5F7 30%, #FAF5F6 100%) !important;
    }
    
    .title-area { 
        text-align: center; 
        margin-top: 20px;
        margin-bottom: 15px; 
        line-height: 1.4;
    }
    
    /* 지도 내부 날짜 히트맵 범례 스타일 */
    .map-legend {
        position: absolute; bottom: 30px; right: 10px; z-index: 1000;
        background: white; padding: 10px; border-radius: 5px;
        box-shadow: 0 0 15px rgba(0,0,0,0.2); font-size: 12px; line-height: 18px;
    }
    
    /* 1) 🎯 점점점(⋮) 버튼을 카드의 무조건 '최우측 상단'으로 강제 고정 */
    div[data-testid="stColumn"] {
        position: relative !important;
    }
    
    div[data-testid="stColumn"] div[data-testid="stPopover"] {
        position: absolute !important;
        top: 12px !important;
        right: 18px !important; /* 오른쪽 끝에서 살짝 안으로 조정 */
        left: auto !important;   /* 왼쪽 정렬 풀기 */
        z-index: 99 !important;
        margin: 0 !important;
        padding: 0 !important;
        width: auto !important;
    }
    
    /* 점점점 버튼 스타일 투명화 및 터치 영역 최적화 */
    div[data-testid="stColumn"] div[data-testid="stPopover"] button {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #888 !important;
        padding: 0 4px !important;
        font-weight: bold !important;
    }
    div[data-testid="stColumn"] div[data-testid="stPopover"] button:hover {
        color: #FF1493 !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── DB 설정 ───
def get_db():
    conn = sqlite3.connect("reports.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lat REAL NOT NULL, lng REAL NOT NULL,
        location_name TEXT, bloom_date TEXT NOT NULL,
        note TEXT, created_at TEXT DEFAULT (datetime('now','localtime'))
    )""")
    
    try:
        conn.execute("ALTER TABLE reports ADD COLUMN nickname TEXT DEFAULT '익명'")
        conn.execute("ALTER TABLE reports ADD COLUMN password TEXT DEFAULT ''")
        conn.commit()
    except:
        pass
        
    return conn

db = get_db()

def add_report(lat, lng, name, bloom_date, note, nickname, password):
    db.execute("INSERT INTO reports (lat,lng,location_name,bloom_date,note,nickname,password) VALUES (?,?,?,?,?,?,?)",
               (lat, lng, name, bloom_date, note, nickname, password))
    db.commit()

def get_reports():
    return db.execute("SELECT * FROM reports ORDER BY created_at DESC").fetchall()

def delete_report(rid):
    db.execute("DELETE FROM reports WHERE id=?", (rid,))
    db.commit()

# ─── 사이드바: 제보 폼 & 관리자 모드 ───
with st.sidebar:
    st.markdown("## 🌸 벚꽃 개화 제보")
    st.caption("지도를 클릭하여 위치를 선택한 뒤 아래 정보를 입력하세요.")
    st.divider()

    if st.session_state.click_lat:
        st.success(f"📍 선택 좌표: {st.session_state.click_lat:.5f}, {st.session_state.click_lng:.5f}")
    else:
        st.info("📍 지도를 클릭해 위치를 선택하세요")

    nickname = st.text_input("👤 작성자 (닉네임)", placeholder="예: 벚꽃헌터")
    password = st.text_input("🔒 비밀번호", type="password", placeholder="게시물 삭제 시 필요")
    
    loc_name = st.text_input("장소명", placeholder="예: 여의도 윤중로")
    bloom_date = st.date_input("📅 개화 확인 날짜", value=date.today())
    note = st.text_area("📝 메모 (선택)", placeholder="개화 정도, 날씨 등 자유롭게")

    if st.button("🌸 제보 등록", use_container_width=True, type="primary"):
        if bloom_date.month
