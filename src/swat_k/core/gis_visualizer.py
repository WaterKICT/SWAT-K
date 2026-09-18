"""SWAT 공간 데이터(Shapefile) 연계, 속성 매핑 및 QGIS 지도 시각화 모듈"""

import os
from pathlib import Path

import pandas as pd

from swat_k.utils.logger import log_warning

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
    except OSError as e:
        log_warning(f"소유역 Shapefile 디렉토리 탐색 오류: {e}")
        return ""
    except Exception as e:
        log_warning(f"소유역 Shapefile 검색 중 예외 발생: {e}")
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

    # out_* 디렉토리가 있는 경우 최신 out 폴더 우선 확인
    from swat_k.utils.settings import find_latest_out_dir

    latest_out = find_latest_out_dir(parent)
    search_dirs = [latest_out, parent] if latest_out else [parent]

    # 1. all.csv 또는 {rch_path}_all.csv 파일 탐색
    all_csv_path = None
    for sdir in search_dirs:
        candidates = [
            sdir / "all.csv",
            sdir / f"{p.name}_all.csv",
            sdir / f"{p.stem}_all.csv",
        ]
        for c in candidates:
            if c.is_file():
                all_csv_path = c
                break
        if all_csv_path:
            break
        alt = list(sdir.glob("*all.csv"))
        if alt:
            all_csv_path = alt[0]
            break

    if all_csv_path and all_csv_path.is_file():
        try:
            df = pd.read_csv(all_csv_path, index_col=0)
            # 컬럼명이 정수(하천 번호) 또는 정수 변환 가능한 문자열인지 확인
            reach_cols = {}
            for col in df.columns:
                col_str = str(col).strip()
                if col_str.isdigit():
                    reach_cols[col] = int(col_str)

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
        except Exception as e:
            log_warning(f"all.csv 로드 중 예외 발생({all_csv_path}): {e}")

    # 2. Max_step3.csv (첨두홍수량 계산 결과 파일) 탐색
    max_step3_path = None
    for sdir in search_dirs:
        candidates = [
            sdir / "Max_step3.csv",
            sdir / f"{p.name}_Max_step3.csv",
            sdir / f"{p.stem}_Max_step3.csv",
        ]
        for c in candidates:
            if c.is_file():
                max_step3_path = c
                break
        if max_step3_path:
            break
        alt = list(sdir.glob("*Max_step3.csv"))
        if alt:
            max_step3_path = alt[0]
            break

    if max_step3_path and max_step3_path.is_file() and year is not None:
        try:
            df_max = pd.read_csv(max_step3_path, index_col=0)
            if year in df_max.index:
                row = df_max.loc[year]
                result = {}
                for col in df_max.columns:
                    col_str = str(col).strip()
                    if col_str.isdigit():
                        try:
                            result[int(col_str)] = round(float(row[col]), 3)
                        except (ValueError, TypeError):
                            continue
                if result:
                    return result
        except Exception as e:
            log_warning(f"Max_step3.csv 파싱 중 예외 발생({max_step3_path}): {e}")

    # 3. 개별 {reach_id}.csv 또는 {rch_path}_{reach_id}.csv 파일 탐색
    result = {}
    for sdir in search_dirs:
        for reach_csv in sdir.glob("*.csv"):
            if any(
                k in reach_csv.name
                for k in ["FlowDuration", "Max_step", "all", "equation"]
            ):
                continue
            rch_id = None
            if reach_csv.stem.isdigit():
                rch_id = int(reach_csv.stem)
            elif reach_csv.stem.startswith(f"{p.name}_"):
                suffix = reach_csv.stem.replace(f"{p.name}_", "")
                if suffix.isdigit():
                    rch_id = int(suffix)
            if rch_id is not None:
                try:
                    df_single = pd.read_csv(
                        reach_csv, header=None, names=["date", "flow"]
                    )
                    df_single["date"] = pd.to_datetime(
                        df_single["date"], errors="coerce"
                    )
                    if year is not None:
                        df_single = df_single[df_single["date"].dt.year == year]
                    flows = pd.to_numeric(df_single["flow"], errors="coerce").dropna()
                    if not flows.empty:
                        val = float(
                            flows.max() if aggregate_mode == "max" else flows.mean()
                        )
                        result[rch_id] = round(val, 3)
                except Exception as e:
                    log_warning(f"개별 하천 CSV({reach_csv.name}) 파싱 실패: {e}")
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
                        if len(parts) >= 6 and parts[1].isdigit():
                            try:
                                rch_id = int(parts[1])
                                flow_out = float(parts[5])
                                reach_data.setdefault(rch_id, []).append(flow_out)
                            except (ValueError, IndexError):
                                continue

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
        except Exception as e:
            log_warning(f"RCH 파일({p.name}) 파싱 실패: {e}")

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
        from qgis.PyQt.QtGui import QColor
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
            sub_layer.setCustomProperty("swat_k_type", "subbasin")
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
    stream_layer_name = f"하천망 유량 (Streamflow){year_label}"
    mem_layer = QgsVectorLayer("LineString", stream_layer_name, "memory")
    if stream_orig.crs().isValid():
        mem_layer.setCrs(stream_orig.crs())
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
    mem_layer.setCustomProperty("swat_k_type", "streamflow")
    project.addMapLayer(mem_layer)

    # 5. 지도 캔버스 Extent 줌
    if iface:
        try:
            canvas = iface.mapCanvas()
            canvas.setExtent(stream_orig.extent())
            canvas.refresh()
        except Exception as e:
            log_warning(f"지도 캔버스 Extent 줌 실패: {e}")

    return (
        True,
        "하천망 유량 레이어가 QGIS 지도에 성공적으로 등록되었습니다.\n"
        f"(하천 번호 필드: '{reach_id_field}')",
    )


def find_subbasin_layer(project=None):
    """QGIS 프로젝트에서 등록된 SWAT-K 소유역 레이어를 탐색합니다."""
    try:
        from qgis.core import QgsProject
    except ImportError:
        return None
    proj = project or QgsProject.instance()
    for layer in proj.mapLayers().values():
        if layer.customProperty("swat_k_type") == "subbasin":
            return layer
        if layer.name().startswith("소유역 경계"):
            return layer
    return None


def find_streamflow_layer(project=None):
    """QGIS 프로젝트에서 등록된 SWAT-K 하천망 레이어를 탐색합니다."""
    try:
        from qgis.core import QgsProject
    except ImportError:
        return None
    proj = project or QgsProject.instance()
    for layer in proj.mapLayers().values():
        if layer.customProperty("swat_k_type") == "streamflow":
            return layer
        if layer.name().startswith("하천망 유량"):
            return layer
    return None


def get_qgis_vector_layers(project=None) -> list:
    """현재 QGIS 프로젝트에 로드된 유효한 벡터 레이어 목록을 반환합니다."""
    try:
        from qgis.core import QgsProject
    except ImportError:
        return []
    proj = project or QgsProject.instance()
    if not proj:
        return []
    vector_layers = []
    for layer in proj.mapLayers().values():
        if (
            hasattr(layer, "type") and layer.type() == 0
        ):  # 0: QgsMapLayerType.VectorLayer
            if not hasattr(layer, "isValid") or layer.isValid():
                vector_layers.append(layer)
    return vector_layers


def get_layer_by_name_or_id(name_or_id: str, project=None):
    """이름 또는 레이어 ID로 QGIS 프로젝트 내 레이어를 탐색합니다."""
    if not name_or_id:
        return None
    try:
        from qgis.core import QgsProject
    except ImportError:
        return None
    proj = project or QgsProject.instance()
    if not proj:
        return None

    # 1. 레이어 ID로 검색
    layer = proj.mapLayer(name_or_id)
    if layer and (not hasattr(layer, "isValid") or layer.isValid()):
        return layer

    # 2. 레이어 이름으로 검색
    layers_by_name = proj.mapLayersByName(name_or_id)
    if layers_by_name:
        return layers_by_name[0]

    # 3. 전체 목록 순회 비교
    for lyr in proj.mapLayers().values():
        if lyr.name() == name_or_id or lyr.id() == name_or_id:
            return lyr

    return None


def get_layer_fields(layer) -> list[str]:
    """지정된 벡터 레이어의 속성 필드명 목록을 반환합니다."""
    if not layer:
        return []
    try:
        if hasattr(layer, "fields"):
            return [f.name() for f in layer.fields()]
    except Exception as e:
        log_warning(f"레이어 속성 필드 조회 실패: {e}")
    return []


def get_field_unique_values(layer, field_name: str) -> list[int]:
    """레이어의 특정 필드에서 고유 정수값(Reach ID 목록)을 추출합니다."""
    if not layer or not field_name:
        return []
    try:
        vals = set()
        for feat in layer.getFeatures():
            raw_val = feat[field_name]
            val_str = str(raw_val).strip()
            if val_str.isdigit():
                vals.add(int(val_str))
        return sorted(vals)
    except Exception as e:
        log_warning(f"필드({field_name}) 고유값 추출 실패: {e}")
        return []


def highlight_subbasin_feature(
    reach_id: int,
    project=None,
    iface=None,
    target_layer=None,
    reach_field: str | None = None,
) -> bool:
    """지정된 reach_id에 해당하는 피처를 QGIS 지도에서 선택/하이라이트합니다."""
    found = False

    # 1. 사용자가 직접 지정한 레이어 우선 처리
    active_layer = target_layer
    if isinstance(active_layer, str):
        active_layer = get_layer_by_name_or_id(active_layer, project)

    if active_layer and hasattr(active_layer, "isValid") and active_layer.isValid():
        field_names = [f.name() for f in active_layer.fields()]
        fld = reach_field or detect_reach_id_field(field_names)
        if fld and fld in field_names:
            target_ids = []
            for feat in active_layer.getFeatures():
                val_str = str(feat[fld]).strip()
                if val_str.isdigit() and int(val_str) == reach_id:
                    target_ids.append(feat.id())
            if target_ids:
                active_layer.selectByIds(target_ids)
                found = True
            else:
                active_layer.removeSelection()

    # 2. SWAT-K 등록 소유역 레이어 처리
    sub_layer = find_subbasin_layer(project)
    if (
        sub_layer
        and hasattr(sub_layer, "isValid")
        and sub_layer.isValid()
        and sub_layer != active_layer
    ):
        field_names = [f.name() for f in sub_layer.fields()]
        r_field = reach_field or detect_reach_id_field(field_names)
        if r_field and r_field in field_names:
            target_ids = []
            for feat in sub_layer.getFeatures():
                val_str = str(feat[r_field]).strip()
                if val_str.isdigit() and int(val_str) == reach_id:
                    target_ids.append(feat.id())
            if target_ids:
                sub_layer.selectByIds(target_ids)
                found = True
            else:
                sub_layer.removeSelection()

    # 3. 하천망 레이어 처리
    stream_layer = find_streamflow_layer(project)
    if (
        stream_layer
        and hasattr(stream_layer, "isValid")
        and stream_layer.isValid()
        and stream_layer != active_layer
    ):
        field_names = [f.name() for f in stream_layer.fields()]
        r_field = (
            "swat_reach"
            if "swat_reach" in field_names
            else detect_reach_id_field(field_names)
        )
        if r_field and r_field in field_names:
            target_ids = []
            for feat in stream_layer.getFeatures():
                val_str = str(feat[r_field]).strip()
                if val_str.isdigit() and int(val_str) == reach_id:
                    target_ids.append(feat.id())
            if target_ids:
                stream_layer.selectByIds(target_ids)
                found = True
            else:
                stream_layer.removeSelection()

    if iface and found:
        try:
            iface.mapCanvas().refresh()
        except Exception as e:
            log_warning(f"지도 캔버스 새로고침 실패: {e}")

    return found


try:
    from qgis.core import QgsFeatureRequest, QgsRectangle
    from qgis.gui import QgsMapToolEmitPoint
    from qgis.PyQt.QtCore import pyqtSignal

    class SubbasinSelectMapTool(QgsMapToolEmitPoint):
        """QGIS 지도 캔버스 클릭 시 피처를 감지하여 Reach ID를 알리는 맵 툴"""

        reach_selected = pyqtSignal(int)

        def __init__(
            self, canvas, iface=None, target_layer=None, reach_field: str | None = None
        ):
            super().__init__(canvas)
            self.iface = iface
            self.target_layer = target_layer
            self.reach_field = reach_field

        def set_target_layer(self, layer):
            self.target_layer = layer

        def set_reach_field(self, field_name: str | None):
            self.reach_field = field_name

        def canvasReleaseEvent(self, event):
            point = self.toMapCoordinates(event.pos())
            mupp = (
                self.canvas().mapUnitsPerPixel()
                if hasattr(self.canvas(), "mapUnitsPerPixel")
                else 1.0
            )

            # 1. 사용자가 선택한 target_layer가 있는 경우 우선 탐색
            layer = self.target_layer
            if isinstance(layer, str):
                layer = get_layer_by_name_or_id(layer)

            if layer and hasattr(layer, "isValid") and layer.isValid():
                field_names = [f.name() for f in layer.fields()]
                reach_field = (
                    self.reach_field
                    if (self.reach_field and self.reach_field in field_names)
                    else detect_reach_id_field(field_names)
                )

                if reach_field:
                    matched_feat = None
                    # 포인트 포함 여부 확인
                    for feat in layer.getFeatures():
                        geom = feat.geometry()
                        if geom and geom.contains(point):
                            matched_feat = feat
                            break

                    # 버퍼 반경 내 검색
                    if not matched_feat:
                        search_radius = mupp * 6
                        rect = QgsRectangle(
                            point.x() - search_radius,
                            point.y() - search_radius,
                            point.x() + search_radius,
                            point.y() + search_radius,
                        )
                        for feat in layer.getFeatures(
                            QgsFeatureRequest().setFilterRect(rect)
                        ):
                            matched_feat = feat
                            break

                    if matched_feat:
                        val_str = str(matched_feat[reach_field]).strip()
                        if val_str.isdigit():
                            reach_id = int(val_str)
                            layer.selectByIds([matched_feat.id()])
                            self.reach_selected.emit(reach_id)
                            return

            # 2. SWAT-K 등록 소유역 레이어 검색
            sub_layer = find_subbasin_layer()
            if sub_layer and sub_layer.isValid():
                field_names = [f.name() for f in sub_layer.fields()]
                reach_field = detect_reach_id_field(field_names)
                if reach_field:
                    matched_feat = None
                    for feat in sub_layer.getFeatures():
                        geom = feat.geometry()
                        if geom and geom.contains(point):
                            matched_feat = feat
                            break

                    if not matched_feat:
                        search_radius = mupp * 5
                        rect = QgsRectangle(
                            point.x() - search_radius,
                            point.y() - search_radius,
                            point.x() + search_radius,
                            point.y() + search_radius,
                        )
                        for feat in sub_layer.getFeatures(
                            QgsFeatureRequest().setFilterRect(rect)
                        ):
                            matched_feat = feat
                            break

                    if matched_feat:
                        val_str = str(matched_feat[reach_field]).strip()
                        if val_str.isdigit():
                            reach_id = int(val_str)
                            sub_layer.selectByIds([matched_feat.id()])
                            self.reach_selected.emit(reach_id)
                            return

            # 3. 하천망 선 레이어 검색
            stream_layer = find_streamflow_layer()
            if stream_layer and stream_layer.isValid():
                search_radius = mupp * 8
                rect = QgsRectangle(
                    point.x() - search_radius,
                    point.y() - search_radius,
                    point.x() + search_radius,
                    point.y() + search_radius,
                )
                field_names = [f.name() for f in stream_layer.fields()]
                reach_field = (
                    "swat_reach"
                    if "swat_reach" in field_names
                    else detect_reach_id_field(field_names)
                )
                for feat in stream_layer.getFeatures(
                    QgsFeatureRequest().setFilterRect(rect)
                ):
                    val_str = str(feat[reach_field]).strip()
                    if val_str.isdigit():
                        reach_id = int(val_str)
                        stream_layer.selectByIds([feat.id()])
                        self.reach_selected.emit(reach_id)
                        return

except ImportError:

    class SubbasinSelectMapTool:
        """QGIS 비의존성 환경용 더미 클래스"""

        def __init__(
            self, canvas=None, iface=None, target_layer=None, reach_field=None
        ):
            self.canvas = canvas
            self.iface = iface
            self.target_layer = target_layer
            self.reach_field = reach_field

        def set_target_layer(self, layer):
            self.target_layer = layer

        def set_reach_field(self, field_name: str | None):
            self.reach_field = field_name
