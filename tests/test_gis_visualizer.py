"""SWAT GIS 시각화 모듈 단위 테스트"""

import tempfile
import unittest
from pathlib import Path

from swat_k.core.gis_visualizer import (
    detect_reach_id_field,
    find_paired_subbasin_shp,
    get_qgis_vector_layers,
    load_reach_flows,
)
from swat_k.utils import settings


class TestGisVisualizer(unittest.TestCase):
    """GIS 시각화 핵심 함수 테스트"""

    def test_detect_reach_id_field(self):
        """속성 필드명으로부터 하천 번호(Reach ID) 필드 감지 검증"""
        # 1. 일반적인 ArcSWAT 필드
        fields_arcswat = ["OBJECTID", "ARCID", "GRID_CODE", "Subbasin", "AreaC"]
        self.assertEqual(detect_reach_id_field(fields_arcswat), "Subbasin")

        # 2. 대소문자 혼용
        fields_case = ["fid", "SUBBASIN", "shape_length"]
        self.assertEqual(detect_reach_id_field(fields_case), "SUBBASIN")

        # 3. QSWAT 및 기타 명칭
        fields_qswat = ["id", "SubId", "Channel", "Slope"]
        self.assertEqual(detect_reach_id_field(fields_qswat), "SubId")

        # 4. 후보 필드가 없을 때
        fields_none = ["name", "elevation", "type"]
        self.assertIsNone(detect_reach_id_field(fields_none))

    def test_find_paired_subbasin_shp(self):
        """하천망 Shapefile 경로로부터 같은 폴더 내 소유역 파일 자동 탐색 검증"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            stream_file = tmppath / "riv1.shp"
            stream_file.touch()

            # 1. 소유역 파일이 없을 때 -> 빈 문자열
            self.assertEqual(find_paired_subbasin_shp(str(stream_file)), "")

            # 2. subs1.shp 파일 생성 시 자동 탐지
            sub_file = tmppath / "subs1.shp"
            sub_file.touch()

            paired = find_paired_subbasin_shp(str(stream_file))
            self.assertEqual(Path(paired).name.lower(), "subs1.shp")

    def test_find_paired_custom_names(self):
        """커스텀 파일명(watershed, sub)에 대한 자동 추천 검증"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            stream_file = tmppath / "my_stream_network.shp"
            stream_file.touch()

            sub_file = tmppath / "watershed_boundary.shp"
            sub_file.touch()

            paired = find_paired_subbasin_shp(str(stream_file))
            self.assertEqual(Path(paired).name.lower(), "watershed_boundary.shp")

    def test_load_reach_flows_from_csv(self):
        """전체 Reach 통합 CSV 파일로부터 유량 추출 검증"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            rch_base = tmppath / "output.rch"
            rch_base.touch()

            all_csv = tmppath / "output.rch_all.csv"
            # 샘플 데이터 생성
            all_csv.write_text(
                ",1,2,3\n"
                "2020-01-01,10.5,20.2,5.1\n"
                "2020-01-02,15.8,18.0,6.2\n"
                "2021-01-01,30.0,40.0,12.0\n",
                encoding="utf-8",
            )

            # 2020년 최대 유량 추출
            flows_2020 = load_reach_flows(
                str(rch_base), year=2020, aggregate_mode="max"
            )
            self.assertEqual(flows_2020.get(1), 15.8)
            self.assertEqual(flows_2020.get(2), 20.2)
            self.assertEqual(flows_2020.get(3), 6.2)

            # 2021년 최대 유량 추출
            flows_2021 = load_reach_flows(
                str(rch_base), year=2021, aggregate_mode="max"
            )
            self.assertEqual(flows_2021.get(1), 30.0)
            self.assertEqual(flows_2021.get(2), 40.0)
            self.assertEqual(flows_2021.get(3), 12.0)

    def test_settings_stream_and_subbasin_path(self):
        """Shapefile 경로 QSettings 저장 및 복원 검증"""
        test_stream = r"C:\data\shapes\riv1.shp"
        test_sub = r"C:\data\shapes\subs1.shp"

        settings.set_stream_shp_path(test_stream)
        settings.set_subbasin_shp_path(test_sub)

        self.assertEqual(settings.get_stream_shp_path(), test_stream)
        self.assertEqual(settings.get_subbasin_shp_path(), test_sub)

    def test_get_qgis_vector_layers_excludes_raster(self):
        """get_qgis_vector_layers가 래스터 레이어를 제외하고 유효한 벡터 레이어만 반환하는지 검증"""
        class DummyLayer:
            def __init__(self, name: str, layer_type: int, is_valid: bool = True):
                self._name = name
                self._type = layer_type
                self._valid = is_valid

            def name(self):
                return self._name

            def type(self):
                return self._type

            def isValid(self):
                return self._valid

        class DummyProject:
            def __init__(self, layers: list):
                self._layers = {str(i): lyr for i, lyr in enumerate(layers)}

            def mapLayers(self):
                return self._layers

        # 0: Vector, 1: Raster
        vec1 = DummyLayer("subbasins_vector", 0, is_valid=True)
        vec2 = DummyLayer("stream_vector", 0, is_valid=True)
        raster1 = DummyLayer("dem_raster", 1, is_valid=True)
        raster2 = DummyLayer("landuse_raster", 1, is_valid=True)
        invalid_vec = DummyLayer("broken_vector", 0, is_valid=False)

        mock_project = DummyProject([vec1, raster1, vec2, invalid_vec, raster2])

        result = get_qgis_vector_layers(mock_project)
        self.assertEqual(len(result), 2)
        self.assertIn(vec1, result)
        self.assertIn(vec2, result)
        self.assertNotIn(raster1, result)
        self.assertNotIn(raster2, result)
        self.assertNotIn(invalid_vec, result)

    def test_get_qgis_vector_layers_excludes_point_layer(self):
        """get_qgis_vector_layers가 포인트 지오메트리 벡터 레이어를 제외하고 폴리곤/라인 레이어만 반환하는지 검증"""
        class DummyVectorLayer:
            def __init__(self, name: str, layer_type: int, geom_type: int, is_valid: bool = True):
                self._name = name
                self._type = layer_type
                self._geom_type = geom_type
                self._valid = is_valid

            def name(self):
                return self._name

            def type(self):
                return self._type

            def isValid(self):
                return self._valid

            def geometryType(self):
                return self._geom_type

        class DummyProject:
            def __init__(self, layers: list):
                self._layers = {str(i): lyr for i, lyr in enumerate(layers)}

            def mapLayers(self):
                return self._layers

        # geom_type: 0 (Point), 1 (Line), 2 (Polygon)
        point1 = DummyVectorLayer("weather_stations", 0, geom_type=0, is_valid=True)
        point2 = DummyVectorLayer("monitoring_points", 0, geom_type=0, is_valid=True)
        polygon1 = DummyVectorLayer("subbasin_polygons", 0, geom_type=2, is_valid=True)
        line1 = DummyVectorLayer("stream_reach_lines", 0, geom_type=1, is_valid=True)

        mock_project = DummyProject([point1, polygon1, point2, line1])
        result = get_qgis_vector_layers(mock_project)

        self.assertNotIn(point1, result)
        self.assertNotIn(point2, result)
        self.assertIn(polygon1, result)
        self.assertIn(line1, result)
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
