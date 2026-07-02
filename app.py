import streamlit as st
import folium
from streamlit_folium import st_folium
from collections import defaultdict
import sqlite3
from datetime import date, datetime, timedelta
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
    .map-legend {
        position: absolute; bottom: 30px; right: 10px; z-index: 1000;
        background: white; padding: 10px; border-radius: 5px;
        box-shadow: 0 0 15px rgba(0,0,0,0.2); font-size: 12px; line-height: 18px;
    }
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
    
    .welcome-dong {
        background-color: #FFF0F2;
        border: 1px dashed #FFB6C1;
        padding: 15px 12px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        color: #D2143A;
        margin-bottom: 15px;
        font-size: 14px;
        line-height: 1.5;
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
    except: pass
    try:
        conn.execute("ALTER TABLE reports ADD COLUMN password TEXT DEFAULT ''")
    except: pass
    try:
        conn.execute("ALTER TABLE reports ADD COLUMN region_title TEXT DEFAULT ''")
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

    if st.session_state.click_lat and st.session_state.selected_region:
        st.markdown(
            f'''
            <div class="welcome-dong">
                <span style="color: #777; font-size: 13px;">📍 현재 선택된 지역</span><br>
                <span style="font-size: 18px; color: #E8326D; font-weight: 800;">{st.session_state.selected_region}</span>
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
        elif not st.session_state.click_lat:
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

# 🗺️ 클릭 시 구역 색칠 및 전체 등치선도(경계선) 색상 진하게 변경
if geo_data:
    try:
        def style_map(feature):
            props = feature.get("properties", {})
            sido = props.get("SIDO_NM", "")
            sigungu = props.get("SIGUNGU_NM", "")
            current_feature_name = f"{sido} {sigungu}".strip()
            
            # 선택된 구역: 매우 뚜렷한 진한 핑크/마젠타
            if st.session_state.selected_region and current_feature_name == st.session_state.selected_region:
                return {
                    'fillColor': '#D81B60',  
                    'color': '#880E4F',      
                    'weight': 2.5,           
                    'fillOpacity': 0.7      
                }
            # 기본 구역: 기존보다 채도/명도를 낮춰 눈에 더 잘 띄는 진한 핑크톤 적용
            return {
                'fillColor': '#F8BBD0',  
                'color': '#F06292',      
                'weight': 1.5,           
                'fillOpacity': 0.35       
            }

        folium.GeoJson(
            geo_data,
            name="시군구 경계",
            style_function=style_map,
            highlight_function=lambda x: {
                'fillColor': '#E91E63',  
                'color': '#C2185B',
                'weight': 2.5,
                'fillOpacity': 0.5
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['SIDO_NM', 'SIGUNGU_NM'],
                aliases=['시/도:', '시/군/구:'],
                localize=True,
                sticky=True
            )
        ).add_to(m)
    except Exception as geo_err:
        folium.GeoJson(
            geo_data,
            name="시군구 경계 (안전 모드)",
            style_function=lambda x: {'fillColor': '#F8BBD0', 'color': '#F06292', 'weight': 1.5, 'fillOpacity': 0.35}
        ).add_to(m)

# 3) 마커를 벚꽃 이모지 대신 심플한 원형(CircleMarker)으로 변경
reports = get_reports()
today = date.today()
date_coords = defaultdict(list)

for row in reports:
    r = dict(row)
    r_lat, r_lng = r.get("lat"), r.get("lng")
    r_bloom_date = r.get("bloom_date", str(today))
    r_loc_name = r.get("location_name", "제보 위치")
    r_nickname = r.get("nickname", "익명")
    r_note = r.get("note", "")
    r_region_title = r.get("region_title", "")
    
    try:
        b_date = datetime.strptime(r_bloom_date, "%Y-%m-%d").date()
        days_diff = (today - b_date).days
    except:
        days_diff = 999
    
    # 시간에 따른 색상 변화 (최근일수록 진하게)
    circle_color = "#E91E63" if days_diff <= 7 else "#F48FB1"
    circle_fill = "#F06292" if days_diff <= 7 else "#FCE4EC"
    circle_opacity = 0.9 if days_diff <= 7 else 0.5
    
    marker_title = r_region_title if r_region_title else "지역 미상"
    
    folium.CircleMarker(
        location=[r_lat, r_lng],
        radius=7,
        color=circle_color,
        weight=2,
        fill=True,
        fill_color=circle_fill,
        fill_opacity=circle_opacity,
        popup=folium.Popup(f"<b>{marker_title}</b><br>📍 {r_loc_name}<br>👤 {r_nickname}<br>📅 {r_bloom_date}<br>{r_note}", max_width=250)
    ).add_to(m)
    
    date_coords[r_bloom_date].append([r_lat, r_lng])

for b_date, coords in date_coords.items():
    if len(coords) >= 2:
        try:
            dt = datetime.strptime(b_date, "%Y-%m-%d").date()
            diff = (today - dt).days
        except:
            diff = 999
        line_color = "#E91E63" if diff <= 7 else "#F48FB1"
        folium.PolyLine(locations=coords, color=line_color, weight=2.2, dash_array='5, 5', opacity=0.75).add_to(m)

# 범례 레이아웃
if date_coords:
    sorted_dates = sorted(list(date_coords.keys()))
    recent_date_str = sorted_dates[-1]  
    past_date_str = sorted_dates[0] if len(sorted_dates) > 1 else "이전"
else:
    recent_date_str, past_date_str = "제보 없음", "제보 없음"

legend_html = f'''
<div class="map-legend" style="position: absolute; bottom: 30px; right: 10px; z-index: 1000; background: rgba(255,255,255,0.9); padding: 12px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); display: flex; align-items: center; gap: 10px;">
    <div style="display: flex; flex-direction: column; justify-content: space-between; font-size: 11px; font-weight: bold; color: #555; height: 100px; text-align: right;">
        <span>📍 {recent_date_str} (최근)</span>
        <span>{past_date_str}</span>
    </div>
    <div style="background: linear-gradient(to bottom, #E91E63, #F48FB1); width: 14px; height: 100px; border-radius: 7px; box-shadow: inset 0 1px 3px rgba(0,0,0,0.2);"></div>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# 지도로부터 데이터 받기
map_data = st_folium(
    m, 
    width=None, 
    height=600, 
    key="cherry_blossom_map",
    returned_objects=["last_clicked", "last_object_clicked", "last_active_drawing"] 
)

# 데이터 추출 및 세션 저장 데이터 검증
if map_data:
    lat, lng = None, None
    if map_data.get("last_clicked"):
        lat = map_data["last_clicked"]["lat"]
        lng = map_data["last_clicked"]["lng"]
    
    clicked_feature = map_data.get("last_object_clicked") or map_data.get("last_active_drawing")
    region_name = ""
    
    if clicked_feature:
        props = clicked_feature.get("properties", {})
        sido = props.get("SIDO_NM", "")
        sigungu = props.get("SIGUNGU_NM", "")
        if sido and sigungu:
            region_name = f"{sido} {sigungu}".strip()
    
    if lat and lng and (33 <= lat <= 39 and 124 <= lng <= 132):
        if st.session_state.click_lat != lat or st.session_state.click_lng != lng or st.session_state.selected_region != region_name:
            st.session_state.click_lat = lat
            st.session_state.click_lng = lng
            if region_name:
                st.session_state.selected_region = region_name
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
                    days_diff = (today - b_date).days
                except:
                    days_diff = 999
                
                card_border, card_bg = ("#D81B60", "#FFE4E1") if days_diff <= 7 else ("#F48FB1", "#FFF5F7")
                note_content = r_note if r_note else '메모 없음'
                
                # 2) 타이틀을 무조건 '지도에서 클릭한 시군구'로 고정
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
