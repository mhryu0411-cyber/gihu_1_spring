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
        if bloom_date.month < 2 or bloom_date.month > 5:
            st.warning("벚꽃 개화는 2월에서 5월 범위 내에서 입력해주세요!")
        elif not st.session_state.click_lat:
            st.warning("지도에서 위치를 먼저 클릭해주세요.")
        elif not nickname or not password:
            st.warning("닉네임과 비밀번호를 반드시 입력해주세요.")
        else:
            add_report(st.session_state.click_lat, st.session_state.click_lng, loc_name, str(bloom_date), note, nickname, password)
            st.session_state.click_lat = None
            st.session_state.click_lng = None
            st.toast("🌸 제보가 등록되었습니다!")
            st.rerun()

    # 관리자 메뉴
    st.divider()
    with st.expander("🛠️ 관리자 메뉴"):
        admin_pw = st.text_input("비밀번호", type="password", key="admin_pw", placeholder="관리자 암호")
        if admin_pw == "저녁먹쟈":
            st.session_state.is_admin = True
            st.success("인증 완료! 강제 삭제 기능 활성화.")
        elif admin_pw:
            st.session_state.is_admin = False
            st.error("비밀번호 오류")

# ─── 메인 상단: 타이틀 ───
st.markdown('<div class="title-area"><h2>🌸 봄철 벚꽃 개화 제보 지도</h2><p style="color:#888">지도를 클릭하여 벚꽃 개화 위치를 제보하세요</p></div>', unsafe_allow_html=True)

# ─── 메인: 지도 영역 ───
m = folium.Map(
    location=st.session_state.map_center,
    zoom_start=st.session_state.map_zoom,
    tiles="CartoDB positron"
)

reports = get_reports()
today = date.today()

date_coords = defaultdict(list)
for r in reports:
    try:
        b_date = datetime.strptime(r["bloom_date"], "%Y-%m-%d").date()
        days_diff = (today - b_date).days
    except:
        days_diff = 999
    
    shadow_color = "drop-shadow(0 0 6px #FF1493)" if days_diff <= 7 else "drop-shadow(0 2px 3px rgba(0,0,0,.3))"
    flower_opacity = "1.0" if days_diff <= 7 else "0.6"
    
    folium.Marker(
        [r["lat"], r["lng"]],
        popup=folium.Popup(f"<b>{r['location_name'] or '제보 위치'}</b><br>👤 {r['nickname']}<br>📅 {r['bloom_date']}<br>{r['note'] or ''}", max_width=250),
        icon=folium.DivIcon(
            html=f'<div style="font-size:28px; filter:{shadow_color}; opacity:{flower_opacity};">🌸</div>',
            icon_size=(28, 28), icon_anchor=(14, 14)
        )
    ).add_to(m)

    date_coords[r["bloom_date"]].append([r["lat"], r["lng"]])

for b_date, coords in date_coords.items():
    if len(coords) >= 2:
        try:
            dt = datetime.strptime(b_date, "%Y-%m-%d").date()
            diff = (today - dt).days
        except:
            diff = 999
            
        line_color = "#FF1493" if diff <= 7 else "#FFB6C1"
        
        folium.PolyLine(
            locations=coords,
            color=line_color,
            weight=2.5,          
            dash_array='6, 6',   
            opacity=0.7,
            tooltip=f"🌸 {b_date} 개화 전선" 
        ).add_to(m)

if st.session_state.click_lat:
    folium.Marker(
        [st.session_state.click_lat, st.session_state.click_lng],
        icon=folium.DivIcon(html='<div style="font-size:32px">📌</div>', icon_size=(32, 32), icon_anchor=(16, 16))
    ).add_to(m)

# 동적 범례 날짜 매핑
if date_coords:
    sorted_dates = sorted(list(date_coords.keys()))
    recent_date_str = sorted_dates[-1]  
    past_date_str = sorted_dates[0] if len(sorted_dates) > 1 else "이전"
else:
    recent_date_str = "제보 없음"
    past_date_str = "제보 없음"

legend_html = f'''
<div class="map-legend" style="position: absolute; bottom: 30px; right: 10px; z-index: 1000; background: rgba(255,255,255,0.9); padding: 12px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); display: flex; align-items: center; gap: 10px;">
    <div style="display: flex; flex-direction: column; justify-content: space-between; font-size: 11px; font-weight: bold; color: #555; height: 100px; text-align: right;">
        <span>🌸 {recent_date_str} (최근)</span>
        <span>{past_date_str}</span>
    </div>
    <div style="background: linear-gradient(to bottom, #FF1493, #FFB6C1); width: 14px; height: 100px; border-radius: 7px; box-shadow: inset 0 1px 3px rgba(0,0,0,0.2);"></div>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

map_data = st_folium(m, width=None, height=600, returned_objects=["last_clicked", "center", "zoom"])

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

# ─── 메인 하단: 제보 목록 영역 ───
st.markdown("---")
st.markdown("### 📋 최근 제보 내역")

if not reports:
    st.caption("아직 제보가 없습니다.")
else:
    cols_per_row = 4
    for i in range(0, len(reports), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, r in enumerate(reports[i:i+cols_per_row]):
            with cols[j]:
                try:
                    b_date = datetime.strptime(r["bloom_date"], "%Y-%m-%d").date()
                    days_diff = (today - b_date).days
                except:
                    days_diff = 999
                
                if days_diff <= 7:
                    card_border = "#FF1493"
                    card_bg = "#FFE4E1"
                else:
                    card_border = "#FFB6C1"
                    card_bg = "#FFF5F7"
                    
                note_content = r['note'] if r['note'] else '메모 없음'
                location_title = r['location_name'] if r['location_name'] else '제보 위치'
                nickname_text = r['nickname'] if r['nickname'] else '익명'
                
                # 🛠️ 카드 높이를 120px로 넉넉하게 확장 + 우측 패딩을 40px 주어 글자가 생략기호(⋮) 절대 침범 못하게 조치
                st.markdown(
                    f'<div style="height: 120px; border-left: 4px solid {card_border}; background-color: {card_bg}; padding: 12px 40px 12px 12px; border-radius: 8px; margin-bottom: 5px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);">'
                    f'<h4 style="margin: 0 0 6px; font-size: 14px; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; width: 90%;">🌸 {location_title}</h4>'
                    f'<p style="margin: 2px 0; font-size: 12px; color: #666;">👤 {nickname_text} | 📅 {r["bloom_date"]}</p>'
                    f'<p style="margin: 6px 0 0; font-size: 12px; color: #555; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.45;">📝 {note_content}</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                
                # 이제 무조건 오른쪽 끝 구석으로 완벽 정렬되는 팝오버
                with st.popover("⋮"):
                    if st.session_state.is_admin:
                        st.info("👑 관리자 권한 활성화됨")
                        if st.button("🗑️ 강제 삭제", key=f"del_admin_{r['id']}", type="primary", use_container_width=True):
                            delete_report(r['id'])
                            st.toast("관리자 권한으로 삭제되었습니다.")
                            st.rerun()
                    else:
                        st.caption("작성 시 입력한 비밀번호")
                        del_pw = st.text_input("비밀번호", type="password", key=f"pw_{r['id']}", label_visibility="collapsed")
                        if st.button("삭제하기", key=f"del_{r['id']}", type="primary", use_container_width=True):
                            if r['password'] and del_pw == r['password']:
                                delete_report(r['id'])
                                st.success("삭제되었습니다!")
                                st.rerun()
                            else:
                                st.error("비밀번호가 일치하지 않습니다.")
