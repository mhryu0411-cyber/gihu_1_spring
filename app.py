# ─── [중앙 구역] 지도(Map) 렌더링 영역 ───
with main_col_map:
    st.markdown(
        '''
        <div class="title-area" style="font-family: 'Nanum Gothic', sans-serif;">
            <h2 style="margin: 0 0 4px 0;">🌸 봄철 벚꽃 개화 제보</h2>
            <p style="color:#4E3629; font-weight: 600; font-size: 15px; margin: 0;">
                여러분이 직접 벚꽃이 개화한 장소들을 제보해보세요!<br>
                개화 지도를 통해 위도별 개화 일수의 변화를 살펴볼 수 있습니다.
            </p>
        </div>
        ''', 
        unsafe_allow_html=True
    )

    # ──────────────────────────────────────────────────────────────
    # [🔥 신규 추가] RCP 시나리오 선택 버튼 구역 (디자인 전용, 동작 없음)
    # ──────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
        .rcp-container {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
            font-family: 'Nanum Gothic', sans-serif;
        }
        .rcp-btn {
            flex: 1;
            padding: 12px 0;
            font-size: 16px;
            font-weight: 800;
            text-align: center;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.25s ease;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        }
        /* 기본(Active 상태 느낌의 포인트 컬러) */
        .rcp-btn.active {
            background: linear-gradient(135deg, #FF69B4 0%, #E91E63 100%);
            color: #FFFFFF;
            border: 1px solid #E91E63;
        }
        /* RCP 버튼들 (부드러운 파스텔 핑크 톤) */
        .rcp-btn.normal {
            background: #FFF0F2;
            color: #D81B60;
            border: 1px solid #FFB6C1;
        }
        .rcp-btn.normal:hover {
            background: #FFE4E1;
            border-color: #FF69B4;
            transform: translateY(-1px);
            box-shadow: 0 4px 10px rgba(233, 30, 99, 0.15);
        }
    </style>
    
    <div class="rcp-container">
        <div class="rcp-btn active">기본</div>
        <div class="rcp-btn normal">RCP 2.6</div>
        <div class="rcp-btn normal">RCP 4.5</div>
        <div class="rcp-btn normal">RCP 8.5</div>
    </div>
    """, unsafe_allow_html=True)
    # ──────────────────────────────────────────────────────────────

    # 이후 기존 folium.Map 생성 코드가 이어집니다.
    m = folium.Map(
        location=[36.3, 127.8],
        zoom_start=9,
        ...
