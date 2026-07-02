import streamlit as st
import folium
from streamlit_folium import st_folium
from collections import defaultdict
import sqlite3
from datetime import date, datetime, timedelta
import json

# 🗺️ 1. 확장자를 .geojson으로 정확하게 지정하여 로드합니다.
with open("Dong_2.geojson", encoding="utf-8") as f:
    geo_data = json.load(f)

# ─── 숨기기 설정 ───
final_hide_style = """
            <style>
            /* 1. 상단 헤더 바 숨기기 */
            [data-testid="stHeader"] {
                visibility: hidden !important;
                display: none !important;
            }
            
            /* 2. 하단 기본 푸터 숨기기 */
            footer {
                visibility: hidden !important;
                display: none !important;
            }
            
            /* 3. 우측 하단 배지, 프로필, 빨간 박스 통째로 날리기 */
            [data-testid="stViewerBadge"], 
            .viewerBadge,
            div[class*="viewerBadge"],
            a[class*="viewerBadge"],
            span[class*="viewerBadge"],
            button[class*="viewerBadge"] {
                display: none !important;
                visibility: hidden !important;
                width: 0 !important;
                height: 0 !important;
                opacity: 0 !important;
                pointer-events: none !important;
            }
            </style>
            """
st.markdown(final_hide_style, unsafe_allow_html=True)


# ─── 페이지 설정 ───
st.set_page_config(page_title="벚꽃 개화 제보", layout="wide", page_icon="🌸")

# ─── 세션 초기화 ───
if "click_lat" not in st.session_state: st.session_state.click_lat = None
if "click_lng" not in st.session_state: st.session_state.click_lng = None
if "selected_region" not in st.session_state: st.session_state.selected_region = "" # 행정동 이름 저장용
if "is_admin" not in st.session_state: st.session_state.is_admin = False

# ─── CSS (우측 끝 강제 고정 및 눈이 편한 배경색) ───
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    
    /* 🕶️ 메인 화면 배경 */
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
    
    /* 🎯 점점점(⋮) 버튼 우측 상단 고정 */
    div[data-testid="stColumn"] {
        position: relative !important;
    }
    
    div[data-testid="stColumn"] div[data-testid="stPopover"] {
        position: absolute !important;
        top: 12px !important;
        right: 18px !important;
        left: auto !important;
        z-index: 99 !important;
        margin: 0 !important;
        padding: 0 !important;
        width: auto !important;
    }
    
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
    st.caption("지도에서 행정동을 클릭한 뒤 정보를 입력하세요.")
    st.divider()

    if st.session_state.click_lat and st.session_state.selected_region:
        st.success(f"📍 선택 지역: {st.session_state.selected_region}")
    else:
        st.info("📍 지도에서 행정동 구역을 클릭하세요")

    nickname = st.text_input("👤 작성자 (닉네임)", placeholder="예: 벚꽃헌터")
    password = st.text_input("🔒 비밀번호", type="password", placeholder="게시물 삭제 시 필요")
    
    # 클릭한 행정동 이름이 기본값으로 들어가도록 설정 (사용자가 직접 수정도 가능)
    loc_name = st.text_input("장소명", value=st.session_state.selected_region, placeholder="예: 여의도 윤중로")
    bloom_date = st.date_input("📅 개화 확인 날짜", value=date.today())
    note = st.
