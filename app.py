import streamlit as st
import folium
from streamlit_folium import st_folium
import sqlite3
import json
from datetime import date, datetime

# ─── 페이지 설정 ───
st.set_page_config(page_title="벚꽃 개화 제보", layout="wide", page_icon="🌸")

# ─── CSS 수정 (타이틀 여백 확보 및 제보 목록 가로 정렬을 위한 스타일 추가) ───
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    div[data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #FFF0F5, #FFFFFF);
    }
    /* 제보 목록 카드 스타일 */
    .report-container { display: flex; flex-wrap: wrap; gap: 10px; width: 100%; }
    .report-card {
        padding: 10px 14px; 
        border-radius: 8px; background: #FFF5F7;
        border-left: 4px solid #FF69B4;
        width: 220px; /* 너비 제한 */
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .report-card h4 { margin: 0 0 4px; font-size: 15px; }
    .report-card p { margin: 2px 0; font-size: 13px; color: #666; }
    .title-area { 
        text-align: center; 
        margin-top: 20px;       /* 상단 여백을 주어 글자 잘림 방지 */
        margin-bottom: 15px; 
        line-height: 1.4;
    }
    /* 가로 배치를 위한 flex 컨테이너 */
    .report-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        width: 100%;
    }
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

# ─── 사이드바: 제보 폼 (제보 목록 제거) ───
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
            add_report(st.session_state.click_lat, st.session_state.click_lng, loc_name, str(bloom_date), note)
            st.session_state.click_lat = None
            st.session_state.click_lng = None
            st.toast("🌸 제보가 등록되었습니다!")
            st.rerun()
        else:
            st.warning("지도에서 위치를 먼저 클릭해주세요.")

# ─── 메인: 지도 ───
st.markdown('<div class="title-area"><h2>🌸 봄철 벚꽃 개화 제보 지도</h2><p style="color:#888">지도를 클릭하여 벚꽃 개화 위치를 제보하세요</p></div>', unsafe_allow_html=True)

# 1. 상단에 세션 변수 초기화 추가
if "map_center" not in st.session_state: st.session_state.map_center = [36.5, 127.8]
if "map_zoom" not in st.session_state: st.session_state.map_zoom = 7

# 2. 지도 생성 시 세션 값 주입
m = folium.Map(
    location=st.session_state.map_center,
    zoom_start=st.session_state.map_zoom,
    tiles="CartoDB positron"
)

# 3. st_folium 호출 시 리턴값에 center와 zoom 추적 추가
map_data = st_folium(m, width=None, height=600, returned_objects=["last_clicked", "center", "zoom"])

# 4. 지도 조작 감지 시 세션에 저장하는 로직 추가
if map_data:
    if map_data.get("center"):
        st.session_state.map_center = [map_data["center"]["lat"], map_data["center"]["lng"]]
    if map_data.get("zoom"):
        st.session_state.map_zoom = map_data["zoom"]

reports = get_reports()
# 1. 지도 우측 상단/하단에 띄울 범례 스타일 CSS 추가
# .map-legend { position: absolute; bottom: 30px; right: 10px; z-index: 1000; background: white; ... }

# 2. 마커 생성 반복문 내부에 날짜 비교 및 필터 분기 추가
for r in reports:
    try:
        b_date = datetime.strptime(r["bloom_date"], "%Y-%m-%d").date()
        days_diff = (date.today() - b_date).days
    except:
        days_diff = 999
    
    # 7일 이내는 진한 핫핑크 글리터 효과, 지나간 것은 투명도 0.6 처리
    shadow_color = "drop-shadow(0 0 6px #FF1493)" if days_diff <= 7 else "drop-shadow(0 2px 3px rgba(0,0,0,.3))"
    flower_opacity = "1.0" if days_diff <= 7 else "0.6"
    
    folium.Marker(
        [r["lat"], r["lng"]],
        popup=folium.Popup(...),
        icon=folium.DivIcon(
            html=f'<div style="font-size:28px; filter:{shadow_color}; opacity:{flower_opacity};">🌸</div>',
            icon_size=(28, 28), icon_anchor=(14, 14)
        )
    ).add_to(m)

# 3. 지도 객체(m) 밑에 범례 엘리먼트 강제 삽입
legend_html = '''
<div class="map-legend">
    <b>🌸 개화 시기 기준</b><br>
    <span class="legend-color" style="background: #FF1493; box-shadow: 0 0 5px #FF1493;"></span> 최근 1주일 이내<br>
    <span class="legend-color" style="background: #FFB6C1; opacity: 0.6;"></span> 1주일 이전 제보
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))
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


# ─── 메인 하단: 제보 목록 추가 ───
st.markdown("---")
st.markdown("### 📋 최근 제보 내역")
reports = get_reports()

if not reports:
    st.caption("아직 제보가 없습니다.")
else:
    # 카드가 가로로 유연하게 배치되도록 HTML 컨테이너 생성
    report_html = '<div class="report-container">'
    for r in reports:
        report_html += f"""
        <div class="report-card">
            <h4>🌸 {r['location_name'] or '제보 위치'}</h4>
            <p>📅 {r['bloom_date']}</p>
            {f'<p>📝 {r["note"]}</p>' if r['note'] else ''}
            <p style="font-size:11px;color:#aaa">{r['created_at'] or ''}</p>
        </div>
        """
    report_html += '</div>'
    st.markdown(report_html, unsafe_allow_html=True)

# (클릭 데이터 세션 처리 부분 생략)
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lng = map_data["last_clicked"]["lng"]
    if 33 <= lat <= 39 and 124 <= lng <= 132:
        st.session_state.click_lat = lat
        st.session_state.click_lng = lng
        st.rerun()
        st.session_state.click_lng = lng
        st.rerun()
