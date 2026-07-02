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

# ─── 100% 정확한 시군구 매핑을 위한 Point-in-Polygon 알고리즘 ───
def find_region_by_point(lat, lng, geojson):
    if not geojson or lat is None or lng is None:
        return ""
    
    def is_point_in_path(x, y, poly):
        num = len(poly)
        j = num - 1
        c = False
        for i in range(num):
            if ((poly[i][1] > y) != (poly[j][1] > y)) and \
                    (x < (poly[j][0] - poly[i][0]) * (y - poly[i][1]) / (poly[j][1] - poly[i][1]) + poly[i][0]):
                c = not c
            j = i
        return c

    for feature in geojson.get("features", []):
        geometry = feature.get("geometry", {})
        g_type = geometry.get("type")
        coords = geometry.get("coordinates", [])
        
        props = feature.get("properties", {})
        sido = props.get("SIDO_NM", "").strip()
        sigungu = props.get("SIGUNGU_NM", "").strip()
        region_name = f"{sido} {sigungu}".strip()
        
        if g_type == "Polygon":
            for ring in coords:
                if is_point_in_path(lng, lat, ring):
                    return region_name
        elif g_type == "MultiPolygon":
            for polygon in coords:
                for ring in polygon:
                    if is_point_in_path(lng, lat, ring):
                        return region_name
    return ""

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

# ─── 전역 CSS 스타일 (나눔고딕 & 배경색 완화 & 메뉴 우측 고정 및 화살표 파괴) ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@400;700;800&display=swap');

    /* 모든 스트림릿 위젯과 텍스트에 나눔고딕 강제 적용 */
    html, body, .stApp, [data-testid="stWidgetLabel"], h1, h2, h3, h4, h5, h6, p, span, div, input, textarea, button {
        font-family: 'Nanum Gothic', sans-serif !important;
    }
    
    .block-container { padding-top: 1rem; }
    
    /* [수정 요청사항] 지도와 카드가 있는 메인 배경란을 아주 깨끗하고 연한 순수 화이트로 변경 */
    .stApp { background-color: #FEFCFC !important; }
    
    /* 사이드바 스타일 배경색 및 내부 폰트 크게 유지 */
    [data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #FFE4E1 0%, #FFF5F7 30%, #FFFFFF 100%) !important;
    }
    [data-testid="stSidebar"] h2 { font-size: 24px !important; font-weight: 800 !important; }
    [data-testid="stSidebar"] .stMarkdown p { font-size: 15px !important; line-height: 1.5; }
    [data-testid="stSidebar"] .stCaption p { font-size: 13px !important; color: #666 !important; }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { font-size: 15px !important; font-weight: 700 !important; color: #333 !important; }
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea { font-size: 14px !important; }
    [data-testid="stSidebar"] button p { font-size: 16px !important; font-weight: 700 !important; }
    
    /* 🔥 [추가] st.expander 관리자 메뉴 내 화살표 및 _arrow_right 찌꺼기 영구 박멸 */
    [data-testid="stSidebar"] [data-testid="stExpander"] summary svg,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary [data-testid="stIcon"],
    [data-testid="stSidebar"] [data-testid="stExpander"] summary span[class*="X"] {
        display: none !important;
        visibility: hidden !important;
    }
    /* 깨진 레이아웃을 초기화하고 텍스트만 정중앙에 화사하게 배치 */
    [data-testid="stSidebar"] [data-testid="stExpander"] summary p {
        font-size: 15px !important;
        font-weight: 700 !important;
        color: #444 !important;
        margin: 0 !important;
        padding: 0 !important;
        display: inline-block !important;
    }
    
    .title-area { text-align: center; margin-top: 20px; margin-bottom: 15px; line-height: 1.5; }
    
    /* [수정 요청사항] 제보 내역 카드 기준으로 팝오버 컨테이너를 우측 상단으로 강제 절대 좌표 지정 */
    div[data-testid="stColumn"] { position: relative !important; }
    div[data-testid="stColumn"] div[data-testid="stPopover"] {
        position: absolute !important; 
        top: 14px !important; 
        right: 15px !important;
        left: auto !important; 
        left: unset !important;
        z-index: 99 !important; 
        margin: 0 !important; 
        padding: 0 !important;
        width: auto !important;
    }
    
    /* [수정 요청사항] expand_more 화살표 아이콘 완전 파괴 및 순수 점점점(⋮) 구현 */
    div[data-testid="stColumn"] div[data-testid="stPopover"] button[data-testid="stPopoverButton"] {
        background-color: transparent !important; border: none !important;
        box-shadow: none !important; padding: 0 !important;
        width: 24px !important; height: 24px !important; min-height: 24px !important;
        display: inline-flex !important; align-items: center !important; justify-content: center !important;
    }
    /* 버튼 내부의 모든 원래 요소(화살표 껍데기, 스트림릿 내장 아이콘 전부)를 흔적도 없이 숨김 */
    div[data-testid="stColumn"] div[data-testid="stPopover"] button[data-testid="stPopoverButton"] * {
        display: none !important;
    }
    /* 텅 빈 버튼에 CSS 가상 선택자로 큼직한 점점점(⋮)만 새로 주입 */
    div[data-testid="stColumn"] div[data-testid="stPopover"] button[data-testid="stPopoverButton"]::after {
        content: "⋮" !important; 
        display: inline-block !important;
        visibility: visible !important;
        font-size: 22px !important; 
        font-weight: 900 !important; 
        color: #999 !important;
        line-height: 1 !important;
    }
    div[data-testid="stColumn"] div[data-testid="stPopover"] button[data-testid="stPopoverButton"]:hover::after {
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
    db.execute("DELETE WHERE id=?", (rid,))
    db.commit()

# ─── 사이드바 영역 ───
with st.sidebar:
    st.markdown("## 🌸 벚꽃 개화 제보")
    st.caption("지도에서 원하는 곳을 클릭하면 해당 시군구가 자동 선택됩니다.")
    st.divider()

    if st.session_state.selected_region:
        st.markdown(
            f'''
            <div style="font-family: 'Nanum Gothic', sans-serif; background-color: #FFF0F2; border: 2px dashed #FF1493; padding: 15px 12px; border-radius: 8px; text-align: center; margin-bottom: 15px;">
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
            st.warning("지도에서 원하는 지역을 먼저 선택(클릭)해주세요.")
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

# ─── 메인 타이틀 & 가이드 멘트 ───
st.markdown(
    '''
    <div class="title-area" style="font-family: 'Nanum Gothic', sans-serif;">
        <h2>🌸 봄철 벚꽃 개화 제보 지도</h2>
        <p style="color:#4E3629; font-weight: 600; font-size: 15px; margin-bottom: 5px;">
            여러분이 직접 벚꽃이 개화한 장소들을 제보해보세요!
        </p>
        <p style="color:#D81B60; font-weight: 700; font-size: 15px; margin-top: 0;">
            개화 지도를 통해, 위도별 개화 일수의 변화를 살펴보세요.
        </p>
    </div>
    ''', 
    unsafe_allow_html=True
)

# ─── 메인 지도 생성 ───
m = folium.Map(
    location=[36.5, 127.8],
    zoom_start=7,
    tiles="CartoDB positron"
)

# 시군구 경계 배경 오버레이
if geo_data:
    folium.GeoJson(
        geo_data,
        name="시군구 경계",
        style_function=lambda x: {
            'fillColor': '#ffffff',  
            'color': '#C0C0C0',       
            'weight': 1.0,            
            'dashArray': '4, 4',      
            'fillOpacity': 0.01       
        },
        highlight_function=lambda x: {
            'color': '#FF1493',       
            'weight': 1.8,
            'dashArray': '4, 4',
            'fillOpacity': 0.03
        }
    ).add_to(m)

# ─── 날짜 기준 색상 셰이딩 범위 연산 ───
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

fills = ["#4A0014", "#7A0026", "#AD1457", "#D81B60", "#EC407A", "#F8BBD0"] 
lines = ["#25000A", "#4A0014", "#7A0026", "#880E4F", "#C2185B", "#E91E63"]

# ─── 제보 데이터 가시화 매핑 ───
date_coords = defaultdict(list)

for row in reports:
    r = dict(row)
    r_lat, r_lng = r.get("lat"), r.get("lng")
    r_bloom_date = r.get("bloom_date", str(date.today()))
    r_loc_name = r.get("location_name", "제보 위치")
    r_nickname = r.get("nickname", "익명")
    r_note = r.get("note", "")
    r_region_title = r.get("region_title", "")
    
    try:
        curr_d = datetime.strptime(r_bloom_date, "%Y-%m-%d").date()
        if min_date == max_date:
            ratio = 0.0
        else:
            ratio = (curr_d - min_date).days / float((max_date - min_date).days)
            ratio = max(0.0, min(1.0, ratio))
    except:
        ratio = 0.0
        
    idx = int(ratio * (len(fills) - 1))
    fill_color = fills[idx]
    line_color = lines[idx]
    
    marker_title = r_region_title if r_region_title else "지역 미상"
    
    folium.CircleMarker(
        location=[r_lat, r_lng],
        radius=15,
        color=line_color,
        weight=1.5,
        fill=True,
        fill_color=fill_color,
        fill_opacity=0.85,
        popup=folium.Popup(f"<div style='font-family: \"Nanum Gothic\", sans-serif;'><b>{marker_title}</b><br>📍 {r_loc_name}<br>👤 {r_nickname}<br>📅 {r_bloom_date}<br>{r_note}</div>", max_width=250)
    ).add_to(m)
    
    folium.CircleMarker(
        location=[r_lat, r_lng], radius=2.5, color="#FFFFFF", weight=1, fill=True, fill_color="#25000A", fill_opacity=1.0
    ).add_to(m)
    
    date_coords[r_bloom_date].append([r_lat, r_lng])

# ─── 선 및 날짜 칸 가시화 연동 ───
for b_date, coords in date_coords.items():
    try:
        curr_d = datetime.strptime(b_date, "%Y-%m-%d").date()
        if min_date == max_date:
            ratio = 0.0
        else:
            ratio = (curr_d - min_date).days / float((max_date - min_date).days)
            ratio = max(0.0, min(1.0, ratio))
    except:
        ratio = 0.0
        
    idx = int(ratio * (len(fills) - 1))
    target_fill = fills[idx]
    target_line = lines[idx]
    
    if len(coords) >= 2:
        folium.PolyLine(locations=coords, color=target_line, weight=3.5, opacity=0.9).add_to(m)
        mid_lat = sum(c[0] for c in coords) / len(coords)
        mid_lng = sum(c[1] for c in coords) / len(coords)
        text_loc = [mid_lat, mid_lng]
    elif len(coords) == 1:
        text_loc = coords[0]
        
    # 확대된 날짜 배지 (13px 크기 고정 적용)
    folium.map.Marker(
        text_loc,
        icon=folium.features.DivIcon(
            icon_size=(125, 26),
            icon_anchor=(62, 13), 
            html=f'<div style="font-family: \'Nanum Gothic\', sans-serif; font-size: 13px; font-weight: 800; color: white; background-color: {target_fill}; border: 1.5px solid {target_line}; padding: 3px 7px; border-radius: 11px; box-shadow: 0px 2px 6px rgba(0,0,0,0.35); white-space: nowrap; text-align:center; line-height:16px;">📅 {b_date}</div>'
        )
    ).add_to(m)

# ─── 우측 하단 범례 ───
legend_html = f'''
<div style="position: absolute; bottom: 30px; right: 20px; z-index: 9999; background: rgba(255,255,255,0.96); padding: 16px; border-radius: 8px; box-shadow: 0 3px 12px rgba(0,0,0,0.25); border: 1px solid #FFB6C1; font-family: 'Nanum Gothic', sans-serif;">
    <div style="font-size: 14px; font-weight: 800; color: #333; margin-bottom: 10px; text-align: center;">🌸 개화 시기별 연동 색상</div>
    <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 13px; color: #4A0014; font-weight: 900; text-align: center; line-height: 1.3;">{min_date}<br>(빠를수록 진함)</span>
        <div style="width: 150px; height: 16px; background: linear-gradient(to right, #4A0014, #7A0026, #AD1457, #D81B60, #EC407A, #F8BBD0); border-radius: 8px; border: 1px solid #ccc;"></div>
        <span style="font-size: 13px; color: #EC407A; font-weight: 700; text-align: center; line-height: 1.3;">{max_date}<br>(늦을수록 연함)</span>
    </div>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# 지도로부터 인터랙션 좌표 캐치
map_data = st_folium(
    m, 
    width=None, 
    height=600, 
    key="cherry_blossom_map",
    returned_objects=["last_clicked"] 
)

if map_data and map_data.get("last_clicked"):
    click_pos = map_data["last_clicked"]
    new_lat = click_pos.get("lat")
    new_lng = click_pos.get("lng")
    
    if new_lat and new_lng and (st.session_state.click_lat != new_lat or st.session_state.click_lng != new_lng):
        detected_region = find_region_by_point(new_lat, new_lng, geo_data)
        
        if detected_region:
            st.session_state.selected_region = detected_region
            st.session_state.click_lat = new_lat
            st.session_state.click_lng = new_lng
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
                
                # 제보 정보 카드 배치
                st.markdown(
                    f'<div style="font-family: \'Nanum Gothic\', sans-serif; height: 175px; border-left: 5px solid {card_border}; background-color: {card_bg}; padding: 14px 40px 14px 14px; border-radius: 8px; margin-bottom: 5px; box-shadow: 0 1px 5px rgba(0,0,0,0.08);">'
                    f'<h4 style="margin: 0 0 6px; font-size: 17px; color: #222; font-weight: 800; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; width: 90%;">🌸 {card_title}</h4>'
                    f'<p style="margin: 0; font-size: 14px; color: #FF1493; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{sub_location}</p>'
                    f'<p style="margin: 4px 0; font-size: 13px; color: #555; font-weight: 500;">👤 {nickname_text} | 📅 {r_bloom_date}</p>'
                    f'<p style="margin: 6px 0 0; font-size: 14px; color: #333; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.5; font-weight: 400;">📝 {note_content}</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                
                # 상단 CSS 인젝션으로 인해 화살표가 영구 격리되고 우측 상단으로 이동한 순수 점점점(⋮) 메뉴
                with st.popover(""):
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
