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
    note = st.text_area("📝 메모 (선택)", placeholder="개화 정도, 날씨 등 자유롭게")

    if st.button("🌸 제보 등록", use_container_width=True, type="primary"):
        if bloom_date.month < 2 or bloom_date.month > 5:
            st.warning("벚꽃 개화는 2월에서 5월 범위 내에서 입력해주세요!")
        elif not st.session_state.click_lat:
            st.warning("지도에서 행정동 위치를 먼저 클릭해주세요.")
        elif not nickname or not password:
            st.warning("닉네임과 비밀번호를 반드시 입력해주세요.")
        else:
            add_report(st.session_state.click_lat, st.session_state.click_lng, loc_name, str(bloom_date), note, nickname, password)
            st.session_state.click_lat = None
            st.session_state.click_lng = None
            st.session_state.selected_region = ""
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
st.markdown('<div class="title-area"><h2>🌸 봄철 벚꽃 개화 제보 지도</h2><p style="color:#888">지도에서 지역을 클릭하여 벚꽃 개화 위치를 제보하세요</p></div>', unsafe_allow_html=True)

# ─── 메인: 지도 영역 ───
m = folium.Map(
    location=[36.5, 127.8],
    zoom_start=7,
    tiles="CartoDB positron"
)

# 🗺️ GeoJSON 레이어 추가 (마우스 호버 및 클릭 활성화)
folium.GeoJson(
    geo_data,
    name="행정동 경계",
    style_function=lambda x: {
        'fillColor': '#ffffff',  # 평소에는 흰색 투명
        'color': '#FFB6C1',      # 경계선 연분홍
        'weight': 1,
        'fillOpacity': 0.05
    },
    highlight_function=lambda x: {
        'fillColor': '#FF1493',  # 마우스 올리면 진분홍
        'color': '#FF1493',
        'weight': 2,
        'fillOpacity': 0.3
    },
    tooltip=folium.GeoJsonTooltip(
        fields=['SIDO_NM', 'ADM_CD'],  # GeoJSON 속성 매핑
        aliases=['시/도:', '행정동:'],  # 팝업에 보일 라벨 명칭
        localize=True,
        sticky=True
    )
).add_to(m)

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

# 동적 범례
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

# 데이터 바인딩 ("last_object_clicked" 포함)
map_data = st_folium(
    m, 
    width=None, 
    height=600, 
    key="cherry_blossom_map",
    returned_objects=["last_clicked", "last_object_clicked"] 
)

# 지도 클릭 시 좌표와 행정동 이름 동시에 세션 상태에 저장 후 리런
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lng = map_data["last_clicked"]["lng"]
    
    clicked_feature = map_data.get("last_object_clicked")
    region_name = ""
    
    if clicked_feature:
        props = clicked_feature.get("properties", {})
        sido = props.get("SIDO_NM", "")
        dong = props.get("ADM_CD", "")
        region_name = f"{sido} {dong}".strip()  # 예: "서울특별시 여의도동"
    
    if 33 <= lat <= 39 and 124 <= lng <= 132:
        if st.session_state.click_lat != lat or st.session_state.click_lng != lng:
            st.session_state.click_lat = lat
            st.session_state.click_lng = lng
            st.session_state.selected_region = region_name
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
                
                st.markdown(
                    f'<div style="height: 120px; border-left: 4px solid {card_border}; background-color: {card_bg}; padding: 12px 40px 12px 12px; border-radius: 8px; margin-bottom: 5px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);">'
                    f'<h4 style="margin: 0 0 6px; font-size: 14px; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; width: 90%;">🌸 {location_title}</h4>'
                    f'<p style="margin: 2px 0; font-size: 12px; color: #666;">👤 {nickname_text} | 📅 {r["bloom_date"]}</p>'
                    f'<p style="margin: 6px 0 0; font-size: 12px; color: #555; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.45;">📝 {note_content}</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                
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
