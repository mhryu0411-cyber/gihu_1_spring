import streamlit as st
import folium
from streamlit_folium import st_folium
import sqlite3
from datetime import date, datetime

# ─── 페이지 설정 ───
st.set_page_config(page_title="벚꽃 개화 제보", layout="wide", page_icon="🌸")

# ─── CSS (타이틀 짤림 방지, 카드 너비 축소, 범례 스타일) ───
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    div[data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #FFF0F5, #FFFFFF);
    }
    /* 1) 하단 제보 목록 카드 너비 제한 (220px) 및 배치 */
    .report-container { display: flex; flex-wrap: wrap; gap: 10px; width: 100%; }
    .report-card {
        padding: 10px 14px; 
        border-radius: 8px; background: #FFF5F7;
        border-left: 4px solid #FF69B4;
        width: 220px; 
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .report-card h4 { margin: 0 0 4px; font-size: 14px; color: #333; }
    .report-card p { margin: 2px 0; font-size: 12px; color: #666; }
    .title-area { 
        text-align: center; 
        margin-top: 20px;       /* 상단 여백 확보로 글자 잘림 방지 */
        margin-bottom: 15px; 
        line-height: 1.4;
    }
    
    /* 3) 지도 내부 날짜 히트맵 범례 스타일 */
    .map-legend {
        position: absolute; bottom: 30px; right: 10px; z-index: 1000;
        background: white; padding: 10px; border-radius: 5px;
        box-shadow: 0 0 15px rgba(0,0,0,0.2); font-size: 12px; line-height: 18px;
    }
    .legend-color { display: inline-block; width: 12px; height: 12px; margin-right: 5px; border-radius: 50%; }
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

# ─── 세션 초기화 (2) 지도 원래 축척 및 위치 기억용 포함) ───
if "click_lat" not in st.session_state: st.session_state.click_lat = None
if "click_lng" not in st.session_state: st.session_state.click_lng = None
if "map_center" not in st.session_state: st.session_state.map_center = [36.5, 127.8]
if "map_zoom" not in st.session_state: st.session_state.map_zoom = 7

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
            add_report(st.session_state.click_lat, st.session_state.click_lng, loc_name, str(bloom_date), note)
            st.session_state.click_lat = None
            st.session_state.click_lng = None
            st.toast("🌸 제보가 등록되었습니다!")
            st.rerun()
        else:
            st.warning("지도에서 위치를 먼저 클릭해주세요.")

# ─── 메인: 지도 영역 ───
st.markdown('<div class="title-area"><h2>🌸 봄철 벚꽃 개화 제보 지도</h2><p style="color:#888">지도를 클릭하여 벚꽃 개화 위치를 제보하세요</p></div>', unsafe_allow_html=True)

# 2) 원래 축척 및 위치 유지를 위해 세션 데이터 바인딩
m = folium.Map(
    location=st.session_state.map_center,
    zoom_start=st.session_state.map_zoom,
    tiles="CartoDB positron"
)

reports = get_reports()
today = date.today()

# 3) 날짜에 따른 벚꽃 아이콘 분기 (히트맵 효과)
for r in reports:
    try:
        b_date = datetime.strptime(r["bloom_date"], "%Y-%m-%d").date()
        days_diff = (today - b_date).days
    except:
        days_diff = 999
    
    # 일주일 이내 제보는 강렬한 핫핑크 링 필터, 오래된 제보는 투명도 감소 처리
    shadow_color = "drop-shadow(0 0 6px #FF1493)" if days_diff <= 7 else "drop-shadow(0 2px 3px rgba(0,0,0,.3))"
    flower_opacity = "1.0" if days_diff <= 7 else "0.6"
    
    folium.Marker(
        [r["lat"], r["lng"]],
        popup=folium.Popup(f"<b>{r['location_name'] or '제보 위치'}</b><br>📅 {r['bloom_date']}<br>{r['note'] or ''}", max_width=250),
        icon=folium.DivIcon(
            html=f'<div style="font-size:28px; filter:{shadow_color}; opacity:{flower_opacity};">🌸</div>',
            icon_size=(28, 28), icon_anchor=(14, 14)
        )
    ).add_to(m)

# 현재 마우스로 새로 선택한 핀 표시
if st.session_state.click_lat:
    folium.Marker(
        [st.session_state.click_lat, st.session_state.click_lng],
        icon=folium.DivIcon(html='<div style="font-size:32px">📌</div>', icon_size=(32, 32), icon_anchor=(16, 16))
    ).add_to(m)

# 3) 지도 내 우측 하단 범례 추가
legend_html = '''
<div class="map-legend">
    <b>🌸 개화 시기 기준</b><br>
    <span class="legend-color" style="background: #FF1493; box-shadow: 0 0 5px #FF1493;"></span> 최근 1주일 이내<br>
    <span class="legend-color" style="background: #FFB6C1; opacity: 0.6;"></span> 1주일 이전 제보
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# ─── 지도 렌더링 및 인터랙션 정보 통합 수집 (지도가 중복 생성되지 않도록 여기 한 곳에서만 호출) ───
map_data = st_folium(m, width=None, height=600, returned_objects=["last_clicked", "center", "zoom"])

# 2) 사용자가 지도를 움직이거나 확대/축소할 때 위치 및 줌 기억 + 클릭 좌표 획득
if map_data:
    if map_data.get("center"):
        st.session_state.map_center = [map_data["center"]["lat"], map_data["center"]["lng"]]
    if map_data.get("zoom"):
        st.session_state.map_zoom = map_data["zoom"]

    if map_data.get("last_clicked"):
        lat = map_data["last_clicked"]["lat"]
        lng = map_data["last_clicked"]["lng"]
        if 33 <= lat <= 39 and 124 <= lng <= 132:
            st.session_state.click_lat = lat
            st.session_state.click_lng = lng
            st.rerun()

# ─── 메인 하단: 제보 목록 영역 (1) 너비가 줄어든 콤팩트 카드 형태) ───
st.markdown("---")
st.markdown("### 📋 최근 제보 내역")

if not reports:
    st.caption("아직 제보가 없습니다.")
else:
    report_html = '<div class="report-container">'
    for r in reports:
        # 메모 길이에 상관없이 이쁘게 떨어지도록 한 줄 처리
        note_display = f'<p style="text-overflow: ellipsis; overflow: hidden; white-space: nowrap; margin: 0;">📝 {r["note"]}</p>' if r['note'] else ''
        report_html += f"""
        <div class="report-card">
            <h4>🌸 {r['location_name'] or '제보 위치'}</h4>
            <p>📅 {r['bloom_date']}</p>
            {note_display}
            <p style="font-size:11px;color:#aaa; margin: 0;">⏱️ {r['created_at'][:16] if r['created_at'] else ''}</p>
        </div>
        """
    report_html += '</div>'
    st.markdown(report_html, unsafe_allow_html=True)
