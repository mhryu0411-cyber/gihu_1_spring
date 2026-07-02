import streamlit as st
import folium
from streamlit_folium import st_folium
from collections import defaultdict
import sqlite3
from datetime import date, datetime
import json
import os

# ─── 페이지 설정 ───
st.set_page_config(page_title="벚꽃 개화 제보", layout="wide", page_icon="🌸")

# ─── 1. GeoJSON 파일 캐싱 ───
@st.cache_data(show_spinner="시군구 경계 데이터를 불러오는 중...")
def load_geojson():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "SIGUNGU_2.geojson")
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"⚠️ GeoJSON 로드 실패: {e}")
        return None

geo_data = load_geojson()

# ─── UI 숨김 설정 ───
final_hide_style = """
            <style>
            [data-testid="stHeader"] { visibility: hidden !important; display: none !important; }
            footer { visibility: hidden !important; display: none !important; }
            [data-testid="stViewerBadge"], .viewerBadge, div[class*="viewerBadge"] {
                display: none !important; visibility: hidden !important;
            }
            </style>
            """
st.markdown(final_hide_style, unsafe_allow_html=True)

# ─── 세션 초기화 ───
if "click_lat" not in st.session_state: st.session_state.click_lat = None
if "click_lng" not in st.session_state: st.session_state.click_lng = None
if "selected_region" not in st.session_state: st.session_state.selected_region = ""
if "is_admin" not in st.session_state: st.session_state.is_admin = False

# ─── CSS 스타일 ───
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .stApp { background-color: #FAF5F6 !important; }
    [data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #FFE4E1 0%, #FFF5F7 30%, #FAF5F6 100%) !important;
    }
    .title-area { text-align: center; margin-top: 20px; margin-bottom: 15px; line-height: 1.4; }
    div[data-testid="stColumn"] { position: relative !important; }
    div[data-testid="stColumn"] div[data-testid="stPopover"] {
        position: absolute !important; top: 12px !important; right: 18px !important;
        left: auto !important; z-index: 99 !important; margin: 0 !important; padding: 0 !important;
    }
    div[data-testid="stColumn"] div[data-testid="stPopover"] button {
        background-color: transparent !important; border: none !important;
        box-shadow: none !important; color: #888 !important; padding: 0 4px !important; font-weight: bold !important;
    }
    div[data-testid="stColumn"] div[data-testid="stPopover"] button:hover { color: #FF1493 !important; }
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
    try: conn.execute("ALTER TABLE reports ADD COLUMN nickname TEXT DEFAULT '익명'")
    except: pass
    try: conn.execute("ALTER TABLE reports ADD COLUMN password TEXT DEFAULT ''")
    except: pass
    try: conn.execute("ALTER TABLE reports ADD COLUMN region_title TEXT DEFAULT ''")
    except: pass
    conn.commit()
    return conn

db = get_db()

def add_report(lat, lng, name, bloom_date, note, nickname, password, region_title):
    db.execute("INSERT INTO reports (lat,lng,location_name,bloom_date,note,nickname,password,region_title) VALUES (?,?,?,?,?,?,?,?)",
               (lat, lng, name, bloom_date, note, nickname, password, region_title))
    db.commit()

def get_reports():
    return db.execute("SELECT * FROM reports ORDER BY created_at DESC").fetchall()

def delete_report(rid):
    db.execute("DELETE FROM reports WHERE id=?", (rid,))
    db.commit()

# ─── 사이드바 영역 ───
with st.sidebar:
    st.markdown("## 🌸 벚꽃 개화 제보")
    st.caption("지도에서 시군구를 클릭한 뒤 정보를 입력하세요.")
    st.divider()

    # 클릭 시 안내 문구가 사라지고 선택된 지역이 즉시 대체되어 표기됨
    if st.session_state.selected_region:
        st.markdown(
            f'''
            <div style="background-color: #FFF0F2; border: 2px dashed #FF1493; padding: 15px 12px; border-radius: 8px; text-align: center; margin-bottom: 15px;">
                <span style="color: #777; font-size: 13px;">📍 현재 선택된 지역</span><br>
                <span style="font-size: 20px; color: #D81B60; font-weight: 900;">{st.session_state.selected_region}</span>
            </div>
            ''', 
            unsafe_allow_html=True
        )
    else:
        st.info("📍 지도에서 시군구 구역을 클릭하세요")

    nickname = st.text_input("👤 작성자 (닉네임)", placeholder="예: 벚꽃헌터")
    password = st.text_input("🔒 비밀번호", type="password", placeholder="게시물 삭제 시 필요")
    
    loc_name = st.text_input("세부 장소", placeholder="예: 윤중로 벚꽃길, 오거리 앞 공원")
    bloom_date = st.date_input("📅 개화 확인 날짜", value=date.today())
    note = st.text_area("📝 메모 (선택)", placeholder="개화 정도, 날씨 등 자유롭게")

    if st.button("🌸 제보 등록", use_container_width=True, type="primary"):
        if bloom_date.month < 2 or bloom_date.month > 5:
            st.warning("벚꽃 개화는 2월에서 5월 범위 내에서 입력해주세요!")
        elif not st.session_state.click_lat or not st.session_state.selected_region:
            st.warning("지도에서 원하는 시군구 지역을 먼저 클릭해주세요.")
        elif not nickname or not password:
            st.warning("닉네임과 비밀번호를 반드시 입력해주세요.")
        else:
            add_report(
                st.session_state.click_lat, 
                st.session_state.click_lng, 
                loc_name, 
                str(bloom_date), 
                note, 
                nickname, 
                password,
                st.session_state.selected_region
            )
            st.session_state.click_lat = None
            st.session_state.click_lng = None
            st.session_state.selected_region = ""
            st.toast("🌸 제보가 등록되었습니다!")
            st.rerun()

    st.divider()
    with st.expander("🛠️ 관리자 메뉴"):
        admin_pw = st.text_input("비밀번호", type="password", key="admin_pw", placeholder="관리자 암호")
        if admin_pw == "저녁먹쟈":
            st.session_state.is_admin = True
            st.success("인증 완료! 강제 삭제 기능 활성화.")
        elif admin_pw:
            st.session_state.is_admin = False
            st.error("비밀번호 오류")

# ─── 메인 타이틀 ───
st.markdown('<div class="title-area"><h2>🌸 봄철 벚꽃 개화 제보 지도</h2><p style="color:#888">지도에서 시군구를 클릭하여 벚꽃 개화 위치를 제보하세요</p></div>', unsafe_allow_html=True)

# ─── 메인 지도 생성 ───
m = folium.Map(
    location=[36.5, 127.8],
    zoom_start=7,
    tiles="CartoDB positron"
)

# 시군구 경계 스타일링
if geo_data:
    folium.GeoJson(
        geo_data,
        name="시군구 경계",
        style_function=lambda x: {
            'fillColor': '#ffffff',  
            'color': '#B0B0B0',       
            'weight': 1.2,            
            'dashArray': '5, 5',      # 경계는 점선으로 깔끔하게 처리
            'fillOpacity': 0.01       # ★ 핵심 수정: 0.01로 두어 투명해 보이지만 클릭 인식이 100% 되도록 교정
        },
        highlight_function=lambda x: {
            'color': '#FF1493',       
            'weight': 2.0,
            'dashArray': '5, 5',
            'fillOpacity': 0.05
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['SIDO_NM', 'SIGUNGU_NM'],
            aliases=['시/도:', '시/군/구:'],
            localize=True,
            sticky=True
        )
    ).add_to(m)

# ─── 날짜 동적 색상 계산 범위 추출 ───
reports = get_reports()
valid_dates = []
for row in reports:
    try: valid_dates.append(datetime.strptime(row["bloom_date"], "%Y-%m-%d").date())
    except: pass

if valid_dates:
    min_date = min(valid_dates)
    max_date = max(valid_dates)
else:
    min_date = date.today()
    max_date = date.today()

# ─── 데이터 매핑 및 오버레이 ───
date_coords = defaultdict(list)

for row in reports:
    r = dict(row)
    r_lat, r_lng = r.get("lat"), r.get("lng")
    r_bloom_date = r.get("bloom_date", str(date.today()))
    r_loc_name = r.get("location_name", "제보 위치")
    r_nickname = r.get("nickname", "익명")
    r_note = r.get("note", "")
    r_region_title = r.get("region_title", "")
    
    # [요청사항 수정] 일자가 빠를수록(과거일수록) 더 진하고 무거운 마젠타/버건디 계열 배정
    try:
        curr_d = datetime.strptime(r_bloom_date, "%Y-%m-%d").date()
        if min_date == max_date:
            ratio = 0.0
        else:
            # 빠를수록(차이가 작을수록) ratio가 0에 가깝고, 늦을수록 1에 가깝게 계산
            ratio = (curr_d - min_date).days / float((max_date - min_date).days)
            ratio = max(0.0, min(1.0, ratio))
    except:
        ratio = 0.0
        
    # 인덱스 0번(가장 빠른 날)이 가장 진함 -> 뒤로 갈수록 연한 핑크
    fills = ["#7A0026", "#AD1457", "#D81B60", "#EC407A", "#F8BBD0"] 
    lines = ["#4A0014", "#7A0026", "#880E4F", "#C2185B", "#E91E63"]
    
    idx = int(ratio * (len(fills) - 1))
    fill_color = fills[idx]
    line_color = lines[idx]
    
    marker_title = r_region_title if r_region_title else "지역 미상"
    
    # 원형 마커
    folium.CircleMarker(
        location=[r_lat, r_lng],
        radius=15,
        color=line_color,
        weight=1.5,
        fill=True,
        fill_color=fill_color,
        fill_opacity=0.85,
        popup=folium.Popup(f"<b>{marker_title}</b><br>📍 {r_loc_name}<br>👤 {r_nickname}<br>📅 {r_bloom_date}<br>{r_note}", max_width=250)
    ).add_to(m)
    
    # 코어 센터 피트
    folium.CircleMarker(
        location=[r_lat, r_lng], radius=2.5, color="#FFFFFF", weight=1, fill=True, fill_color="#300000", fill_opacity=1.0
    ).add_to(m)
    
    date_coords[r_bloom_date].append([r_lat, r_lng])

# 등치선 연결 (진한 실선 + 날짜 상시 노출 라벨 박스)
for b_date, coords in date_coords.items():
    if len(coords) >= 2:
        folium.PolyLine(locations=coords, color="#C2185B", weight=3.5, opacity=0.95).add_to(m)
        mid_idx = len(coords) // 2
        text_loc = coords[mid_idx]
    elif len(coords) == 1:
        text_loc = coords[0]
        
    folium.map.Marker(
        text_loc,
        icon=folium.features.DivIcon(
            icon_size=(110, 24),
            icon_anchor=(55, 32), 
            html=f'<div style="font-size: 12px; font-weight: 800; color: white; background-color: #880E4F; border: 1px solid #4A0014; padding: 2px 6px; border-radius: 4px; box-shadow: 1px 1px 3px rgba(0,0,0,0.4); white-space: nowrap; text-align:center;">📅 {b_date}</div>'
        )
    ).add_to(m)

# ─── 우측 하단 개화 원형 마커 기준 단일 범례 구성 ───
legend_html = f'''
<div style="position: absolute; bottom: 30px; right: 20px; z-index: 9999; background: rgba(255,255,255,0.95); padding: 14px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.3); border: 1px solid #FFB6C1;">
    <div style="font-size: 12px; font-weight: 800; color: #333; margin-bottom: 8px; text-align: center;">🌸 개화 시기별 원형 마커 색상</div>
    <div style="display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 11px; color: #7A0026; font-weight: 900; text-align: center; line-height: 1.2;">{min_date}<br>(빠를수록 진함)</span>
        <div style="width: 120px; height: 14px; background: linear-gradient(to right, #7A0026, #AD1457, #D81B60, #EC407A, #F8BBD0); border-radius: 7px; border: 1px solid #ccc;"></div>
        <span style="font-size: 11px; color: #EC407A; font-weight: 700; text-align: center; line-height: 1.2;">{max_date}<br>(늦을수록 연함)</span>
    </div>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# 지도로부터 상호작용 데이터 캐치
map_data = st_folium(
    m, 
    width=None, 
    height=600, 
    key="cherry_blossom_map",
    returned_objects=["last_clicked", "last_object_clicked"] 
)

# ─── 데이터 검증 및 세션 상태 동기화 교정 ───
if map_data:
    clicked_obj = map_data.get("last_object_clicked")
    new_region = ""
    
    if clicked_obj and "properties" in clicked_obj:
        props = clicked_obj["properties"]
        sido = props.get("SIDO_NM", "").strip()
        sigungu = props.get("SIGUNGU_NM", "").strip()
        if sido or sigungu:
            new_region = f"{sido} {sigungu}".strip()
            
    new_lat = map_data.get("last_clicked", {}).get("lat") if map_data.get("last_clicked") else None
    new_lng = map_data.get("last_clicked", {}).get("lng") if map_data.get("last_clicked") else None
    
    state_changed = False
    
    # 1. 시군구 지역명이 잡혔고, 기존과 다를 때 갱신
    if new_region and st.session_state.selected_region != new_region:
        st.session_state.selected_region = new_region
        state_changed = True
        
    # 2. 클릭한 좌표가 유효하고, 기존과 다를 때 갱신
    if new_lat and new_lng and (st.session_state.click_lat != new_lat or st.session_state.click_lng != new_lng):
        st.session_state.click_lat = new_lat
        st.session_state.click_lng = new_lng
        state_changed = True
        
    # 변경 사항이 있을 때만 정확하게 rerun 요청
    if state_changed:
        st.rerun()
                    
# ─── 제보 목록 리스트 ───
st.markdown("---")
st.markdown("### 📋 최근 제보 내역")

if not reports:
    st.caption("아직 제보가 없습니다.")
else:
    cols_per_row = 4
    for i in range(0, len(reports), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, row in enumerate(reports[i:i+cols_per_row]):
            with cols[j]:
                r = dict(row)
                r_id = r.get("id")
                r_loc_name = r.get("location_name", "제보 위치")
                r_bloom_date = r.get("bloom_date", "")
                r_note = r.get("note", "")
                r_nickname = r.get("nickname", "익명")
                r_password = r.get("password", "")
                r_region_title = r.get("region_title", "")
                
                try:
                    b_date = datetime.strptime(r_bloom_date, "%Y-%m-%d").date()
                    days_diff = (date.today() - b_date).days
                except:
                    days_diff = 999
                
                card_border, card_bg = ("#D81B60", "#FFE4E1") if days_diff <= 7 else ("#F48FB1", "#FFF5F7")
                note_content = r_note if r_note else '메모 없음'
                
                card_title = r_region_title if r_region_title else "지역 미상"
                sub_location = f"📍 {r_loc_name}" if r_loc_name else ""
                nickname_text = r_nickname if r_nickname else '익명'
                
                st.markdown(
                    f'<div style="height: 140px; border-left: 4px solid {card_border}; background-color: {card_bg}; padding: 12px 40px 12px 12px; border-radius: 8px; margin-bottom: 5px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);">'
                    f'<h4 style="margin: 0 0 4px; font-size: 14px; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; width: 90%;">🌸 {card_title}</h4>'
                    f'<p style="margin: 0; font-size: 11px; color: #FF1493; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{sub_location}</p>'
                    f'<p style="margin: 3px 0; font-size: 11px; color: #777;">👤 {nickname_text} | 📅 {r_bloom_date}</p>'
                    f'<p style="margin: 4px 0 0; font-size: 12px; color: #555; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.4;">📝 {note_content}</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                
                with st.popover("⋮"):
                    if st.session_state.is_admin:
                        st.info("👑 관리자 권한 활성화됨")
                        if st.button("🗑️ 강제 삭제", key=f"del_admin_{r_id}", type="primary", use_container_width=True):
                            delete_report(r_id)
                            st.toast("관리자 권한으로 삭제되었습니다.")
                            st.rerun()
                    else:
                        st.caption("작성 시 입력한 비밀번호")
                        del_pw = st.text_input("비밀번호", type="password", key=f"pw_{r_id}", label_visibility="collapsed")
                        if st.button("삭제하기", key=f"del_{r_id}", type="primary", use_container_width=True):
                            if r_password and del_pw == r_password:
                                delete_report(r_id)
                                st.success("삭제되었습니다!")
                                st.rerun()
                            else:
                                st.error("비밀번호가 일치하지 않습니다.")
