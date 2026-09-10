"""SWAT 공간 데이터(Shapefile) 연계, 속성 매핑 및 QGIS 지도 시각화 모듈"""

import os
from pathlib import Path

import pandas as pd

# 하천 번호(Reach ID) 매핑을 위해 우선 검색할 필드명 후보 (소문자 기준)
REACH_ID_FIELD_CANDIDATES = [
    "subbasin",
    "sub",
    "subid",
    "channel",
    "reach",
    "rch",
    "arcid",
    "grid_code",
    "gridcode",
    "from_node",
    "id",
]


def detect_reach_id_field(field_names: list[str]) -> str | None:
    """속성 필드명 목록 중 하천/소유역 번호(Reach ID)에 해당하는 필드명을 탐색합니다.

    Args:
        field_names: Shapefile의 필드명 목록

    Returns:
        일치하는 원본 필드명 문자열 또는 None
    """
    if not field_names:
        return None

    # 1. 완전 일치 (대소문자 무시)
    name_map = {name.lower(): name for name in field_names}
    for candidate in REACH_ID_FIELD_CANDIDATES:
        if candidate in name_map:
            return name_map[candidate]

    # 2. 부분 일치 (예: Subbasin_1, Sub_ID 등)
    for candidate in ["subbasin", "subid", "channel", "reach"]:
        for name in field_names:
            if candidate in name.lower():
                return name

    return None


def find_paired_subbasin_shp(stream_shp_path: str) -> str:
    """하천망 Shapefile 디렉토리에서 짝꿍 소유역 Shapefile을 탐색합니다.

    Args:
        stream_shp_path: 하천망 Shapefile (.shp) 파일 경로

    Returns:
        탐색된 소유역 Shapefile 절대 경로 또는 빈 문자열
    """
    if not stream_shp_path:
        return ""

    stream_p = Path(stream_shp_path)
    parent_dir = stream_p.parent
    if not parent_dir.is_dir():
        return ""

    stream_name_lower = stream_p.name.lower()

    # 동일 디렉토리 내 .shp 파일 검색
    candidates = []
    try:
        for f in parent_dir.glob("*.shp"):
            if f.name.lower() == stream_name_lower:
                continue

            fname_lower = f.stem.lower()
            # subs, sub, basin, watershed 키워드 확인
            if any(k in fname_lower for k in ["sub", "basin", "watershed"]):
                candidates.append(f)
    except Exception:
        return ""

    if not candidates:
        return ""

    # 우선순위: 'sub'가 포함된 파일 (subs1.shp, sub1.shp 등) 우선 선택
    sub_matched = [c for c in candidates if "sub" in c.stem.lower()]
    chosen = sub_matched[0] if sub_matched else candidates[0]
    return str(chosen.resolve())


def load_reach_flows(
    rch_file_path: str,
    year: int | None = None,
    date_str: str | None = None,
    aggregate_mode: str = "max",
) -> dict[int, float]:
    """RCH 변환 CSV 또는 원본 RCH 파일에서 하천별 유량 데이터를 추출합니다.

    Args:
        rch_file_path: RCH 파일 경로 또는 변환된 CSV 경로
        year: 조회할 특정 연도 (예: 2013)
        date_str: 특정 날짜 문자열 (예: "2013-01-01")
        aggregate_mode: 연도별 집계 방식 ("max" 또는 "mean")

    Returns:
        {reach_id: flow_value} 딕셔너리
    """
    if not rch_file_path or not os.path.isfile(rch_file_path):
        return {}

    p = Path(rch_file_path)
    parent = p.parent

    # 1. {rch_path}_all.csv 파일 우선 탐색 (Converter가 생성하는 전 Reach 통합 CSV)
    all_csv_path = parent / f"{p.name}_all.csv"
    if not all_csv_path.is_file():
        # rch_all.csv 이름 후보 탐색
        alt = list(parent.glob("*_all.csv"))
        if alt:
            all_csv_path = alt[0]

    if all_csv_path.is_file():
        try:
            df = pd.read_csv(all_csv_path, index_col=0)
            # 컬럼명이 정수(하천 번호) 또는 정수 변환 가능한 문자열인지 확인
            reach_cols = {}
            for col in df.columns:
                try:
                    reach_cols[col] = int(str(col).strip())
                except ValueError:
                    pass

            if reach_cols:
                # 인덱스 날짜 파싱
                df.index = pd.to_datetime(df.index, errors="coerce")

                if date_str:
                    target_dt = pd.to_datetime(date_str)
                    df_filtered = df[df.index == target_dt]
                elif year is not None:
                    df_filtered = df[df.index.year == year]
                else:
                    df_filtered = df

                if not df_filtered.empty:
                    result = {}
                    for col, rch_id in reach_cols.items():
                        series = pd.to_numeric(
                            df_filtered[col], errors="coerce"
                        ).dropna()
                        if not series.empty:
                            val = float(
                                series.max()
                                if aggregate_mode == "max"
                                else series.mean()
                            )
                            result[rch_id] = round(val, 3)
                    return result
        except Exception:
            pass

    # 2. {rch_path}_Max_step3.csv (첨두홍수량 계산 결과 파일) 탐색
    max_step3_path = parent / f"{p.name}_Max_step3.csv"
    if max_step3_path.is_file() and year is not None:
        try:
            df_max = pd.read_csv(max_step3_path, index_col=0)
            if year in df_max.index:
                row = df_max.loc[year]
                result = {}
                for col in df_max.columns:
                    try:
                        rch_id = int(str(col).strip())
                        result[rch_id] = round(float(row[col]), 3)
                    except (ValueError, TypeError):
                        pass
                if result:
                    return result
        except Exception:
            pass

    # 3. 개별 {rch_path}_{reach_id}.csv 파일 탐색
    result = {}
    for reach_csv in parent.glob(f"{p.name}_*.csv"):
        stem = reach_csv.stem
        # _all, _FlowDuration, _Max 제외
        suffix = stem.replace(f"{p.name}_", "")
        if suffix.isdigit():
            rch_id = int(suffix)
            try:
                df_single = pd.read_csv(reach_csv, header=None, names=["date", "flow"])
                df_single["date"] = pd.to_datetime(df_single["date"], errors="coerce")
                if year is not None:
                    df_single = df_single[df_single["date"].dt.year == year]
                flows = pd.to_numeric(df_single["flow"], errors="coerce").dropna()
                if not flows.empty:
                    val = float(
                        flows.max() if aggregate_mode == "max" else flows.mean()
                    )
                    result[rch_id] = round(val, 3)
            except Exception:
                pass

    if result:
        return result

    # 4. 원본 RCH 텍스트 파일 파싱 (고정폭 텍스트)
    if p.suffix.lower() == ".rch":
        try:
            reach_data: dict[int, list[float]] = {}
            with open(p, encoding="latin1", errors="ignore") as f:
                for line in f:
                    if line.startswith("REACH"):
                        parts = line.split()
                        if len(parts) >= 6:
                            try:
                                rch_id = int(parts[1])
                                flow_out = float(parts[5])
                                reach_data.setdefault(rch_id, []).append(flow_out)
                            except (ValueError, IndexError):
                                pass

            if reach_data:
                return {
                    rch_id: round(
                        float(
                            max(vals)
                            if aggregate_mode == "max"
                            else sum(vals) / len(vals)
                        ),
                        3,
                    )
                    for rch_id, vals in reach_data.items()
                    if vals
                }
        except Exception:
            pass

    return {}


def render_swat_layers_to_qgis(
    stream_shp_path: str,
    subbasin_shp_path: str = "",
    flow_data: dict[int, float] | None = None,
    year_label: str = "",
    iface=None,
) -> tuple[bool, str]:
    """하천망 및 소유역 Shapefile을 QGIS 지도에 단계 구분 심볼로 시각화하여 등록합니다.

    Args:
        stream_shp_path: 하천망 Shapefile (.shp) 경로 (필수)
        subbasin_shp_path: 소유역 Shapefile (.shp) 경로 (선택)
        flow_data: {reach_id: flow_cms} 유량 매핑 데이터
        year_label: 레이어 이름에 표시할 연도 레이블 (예: " (2013년)")
        iface: QGIS QgisInterface 객체 (선택)

    Returns:
        (성공여부: bool, 결과메시지: str)
    """
    try:
        from qgis.core import (
            QColor,
            QgsFeature,
            QgsField,
            QgsFields,
            QgsFillSymbol,
            QgsGraduatedSymbolRenderer,
            QgsLineSymbol,
            QgsProject,
            QgsRendererRange,
            QgsSingleSymbolRenderer,
            QgsVectorLayer,
        )
        from qgis.PyQt.QtCore import QVariant
    except ImportError:
        return False, "QGIS Python API(qgis.core)를 로드할 수 없는 환경입니다."

    if not stream_shp_path or not os.path.isfile(stream_shp_path):
        return False, f"하천망 Shapefile이 유효하지 않습니다: {stream_shp_path}"

    project = QgsProject.instance()

    # 1. 소유역 레이어 추가 (배경 레이어 - 제공된 경우)
    if subbasin_shp_path and os.path.isfile(subbasin_shp_path):
        sub_layer_name = f"소유역 경계 (Subbasins){year_label}"
        sub_layer = QgsVectorLayer(subbasin_shp_path, sub_layer_name, "ogr")
        if sub_layer.isValid():
            # 은은한 회색 테두리 + 반투명 채우기 스타일 설정
            sub_sym = QgsFillSymbol.createSimple(
                {
                    "color": "230,235,245,60",  # 투명도 있는 옅은 블루그레이
                    "outline_color": "100,116,139,200",  # 진한 슬레이트 그레이
                    "outline_width": "0.4",
                    "outline_style": "solid",
                }
            )
            sub_layer.setRenderer(QgsSingleSymbolRenderer(sub_sym))
            sub_layer.triggerRepaint()
            project.addMapLayer(sub_layer)

    # 2. 하천망 레이어 로드 및 유량 속성 결합
    stream_orig = QgsVectorLayer(stream_shp_path, "temp_stream", "ogr")
    if not stream_orig.isValid():
        return False, f"하천망 Shapefile을 읽을 수 없습니다: {stream_shp_path}"

    # 하천 번호 필드 감지
    field_names = [f.name() for f in stream_orig.fields()]
    reach_id_field = detect_reach_id_field(field_names)
    if not reach_id_field:
        return (
            False,
            "하천망 Shapefile에서 하천 번호 필드(Subbasin 등)를 찾을 수 없습니다.\n"
            f"확인된 필드: {', '.join(field_names[:8])}",
        )

    # 원본 Shapefile을 보호하기 위해 QGIS 메모리 벡터 레이어(LineString) 생성
    crs_str = stream_orig.crs().authid() or "EPSG:5179"
    stream_layer_name = f"하천망 유량 (Streamflow){year_label}"
    mem_layer = QgsVectorLayer(f"LineString?crs={crs_str}", stream_layer_name, "memory")
    mem_dp = mem_layer.dataProvider()

    # 원본 필드 복제 + 유량 및 하천번호 필드 추가
    new_fields = QgsFields()
    for field in stream_orig.fields():
        new_fields.append(field)
    new_fields.append(QgsField("swat_reach", QVariant.Int))
    new_fields.append(QgsField("swat_flow", QVariant.Double))
    mem_dp.addAttributes(list(new_fields))
    mem_layer.updateFields()

    # 피처 복제 및 유량 값 주입
    flow_map = flow_data or {}
    new_features = []
    flows_collected = []

    for feat in stream_orig.getFeatures():
        new_feat = QgsFeature(mem_layer.fields())
        new_feat.setGeometry(feat.geometry())

        # 기존 속성 복사
        attrs = feat.attributes()
        rch_val = feat[reach_id_field]
        try:
            rch_id = int(rch_val)
        except (ValueError, TypeError):
            rch_id = 0

        flow_val = float(flow_map.get(rch_id, 0.0))
        attrs.append(rch_id)
        attrs.append(flow_val)
        new_feat.setAttributes(attrs)
        new_features.append(new_feat)

        if flow_val > 0:
            flows_collected.append(flow_val)

    mem_dp.addFeatures(new_features)
    mem_layer.updateExtents()

    # 3. 단계 구분 심볼(Graduated Symbol Renderer) 적용
    # 5단계 파란색 계열 색상 및 선 두께 (연한 파랑 -> 짙은 남색)
    colors = [
        QColor("#93C5FD"),  # 1단계: Light Blue
        QColor("#60A5FA"),  # 2단계: Sky Blue
        QColor("#3B82F6"),  # 3단계: Blue
        QColor("#1D4ED8"),  # 4단계: Dark Blue
        QColor("#1E3A8A"),  # 5단계: Navy
    ]
    widths = [0.8, 1.2, 1.7, 2.2, 2.8]  # 선 두께 (mm)

    ranges = []
    if flows_collected:
        min_f = min(flows_collected)
        max_f = max(flows_collected)
    else:
        min_f = 0.0
        max_f = 100.0

    if min_f == max_f:
        max_f = min_f + 1.0

    step = (max_f - min_f) / 5.0
    for i in range(5):
        lower = min_f + i * step
        upper = min_f + (i + 1) * step if i < 4 else max_f * 1.001
        label = f"{lower:.1f} ~ {upper:.1f} m³/s"

        sym = QgsLineSymbol.createSimple(
            {
                "color": colors[i].name(),
                "width": str(widths[i]),
                "line_style": "solid",
                "capstyle": "round",
                "joinstyle": "round",
            }
        )
        ranges.append(QgsRendererRange(lower, upper, sym, label))

    renderer = QgsGraduatedSymbolRenderer("swat_flow", ranges)
    mem_layer.setRenderer(renderer)
    mem_layer.triggerRepaint()

    # 4. QGIS 프로젝트에 레이어 등록
    project.addMapLayer(mem_layer)

    # 5. 지도 캔버스 Extent 줌
    if iface:
        try:
            canvas = iface.mapCanvas()
            canvas.setExtent(stream_orig.extent())
            canvas.refresh()
        except Exception:
            pass

    return (
        True,
        "하천망 유량 레이어가 QGIS 지도에 성공적으로 등록되었습니다.\n"
        f"(하천 번호 필드: '{reach_id_field}')",
    )
