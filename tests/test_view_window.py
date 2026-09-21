"""SWAT-K View 대화상자 및 헬퍼 함수 단위 테스트"""

import sys
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from swat_k.utils import settings
from swat_k.view_window import (
    ViewDialog,
    extract_years_from_flow_duration,
    find_available_reaches,
    find_daily_flow_file,
    find_equation_file,
    find_flow_duration_file,
    find_latest_out_dir,
    read_user_equation,
    resolve_effective_data_dir,
)

app = QApplication.instance() or QApplication(sys.argv)


class TestViewWindowHelpers(unittest.TestCase):
    """FlowDuration 및 유량 파일 탐색, 소유역/연도 추출 헬퍼 함수 검증"""

    def test_extract_years_from_flow_duration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            csv_file = tmppath / "test_FlowDuration_1.csv"

            # 1. 표준 헤더 형식 (,2013,2014,...,2021,)
            csv_file.write_text(
                ",2013,2014,2015,2016,2017,2018,2019,2020,2021,\n1,10,20,30\n",
                encoding="utf-8",
            )
            years = extract_years_from_flow_duration(csv_file)
            self.assertEqual(
                years,
                ["2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021"],
            )

            # 2. 존재하지 않는 파일
            self.assertEqual(extract_years_from_flow_duration(tmppath / "none.csv"), [])

            # 3. 비정상 헤더
            csv_bad = tmppath / "bad.csv"
            csv_bad.write_text("colA,colB,not_a_year\n", encoding="utf-8")
            self.assertEqual(extract_years_from_flow_duration(csv_bad), [])

    def test_find_flow_duration_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # 1. 빈 디렉토리 -> None
            self.assertIsNone(find_flow_duration_file(tmppath, "a.rch", reach_id=1))

            # 2. [rch]_FlowDuration_1.csv 우선 탐색
            fd1 = tmppath / "a.rch_FlowDuration_1.csv"
            fd1.touch()
            found = find_flow_duration_file(tmppath, "a.rch", reach_id=1)
            self.assertEqual(found.name, "a.rch_FlowDuration_1.csv")

            # 3. a.rch_FlowDuration.csv 탐색 (사용자 언급 케이스, reach_id=1)
            fd1.unlink()
            fd_user = tmppath / "a.rch_FlowDuration.csv"
            fd_user.touch()
            found_user = find_flow_duration_file(tmppath, "a.rch", reach_id=1)
            self.assertEqual(found_user.name, "a.rch_FlowDuration.csv")

            # 4. 소유역 9번 탐색 (FlowDuration_9.csv)
            fd9 = tmppath / "a.rch_FlowDuration_9.csv"
            fd9.touch()
            found9 = find_flow_duration_file(tmppath, "a.rch", reach_id=9)
            self.assertEqual(found9.name, "a.rch_FlowDuration_9.csv")

    def test_find_daily_flow_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # 1. 빈 디렉토리 -> None
            self.assertIsNone(find_daily_flow_file(tmppath, "a.rch", reach_id=1))

            # 2. a.rch_1.csv 탐색
            d1 = tmppath / "a.rch_1.csv"
            d1.touch()
            found = find_daily_flow_file(tmppath, "a.rch", reach_id=1)
            self.assertEqual(found.name, "a.rch_1.csv")

            # 3. 소유역 9번 탐색
            d9 = tmppath / "a.rch_9.csv"
            d9.touch()
            found9 = find_daily_flow_file(tmppath, "a.rch", reach_id=9)
            self.assertEqual(found9.name, "a.rch_9.csv")

            # 4. _all.csv 대체 탐색
            d1.unlink()
            d9.unlink()
            all_csv = tmppath / "a.rch_all.csv"
            all_csv.touch()
            found_all = find_daily_flow_file(tmppath, "a.rch", reach_id=9)
            self.assertEqual(found_all.name, "a.rch_all.csv")

    def test_find_available_reaches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # 빈 폴더 기본값 [1]
            self.assertEqual(find_available_reaches(tmppath), [1])

            # _all.csv 헤더로부터 reach 1, 4, 9 탐지
            all_csv = tmppath / "model_all.csv"
            all_csv.write_text(",1,4,9\n2020-01-01,1,2,3\n", encoding="utf-8")
            self.assertEqual(find_available_reaches(tmppath), [1, 4, 9])

    def test_find_equation_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # 1. 빈 디렉토리 -> None
            self.assertIsNone(find_equation_file(tmppath, "a.rch"))

            # 2. Max_step3_equation.csv 우선 탐색
            eq_file = tmppath / "Max_step3_equation.csv"
            eq_file.touch()
            found = find_equation_file(tmppath, "a.rch")
            self.assertIsNotNone(found)
            self.assertEqual(found.name, "Max_step3_equation.csv")

            # 3. 접두사가 붙은 a.rch_Max_step3_equation.csv 탐색
            eq_file.unlink()
            eq_prefixed = tmppath / "a.rch_Max_step3_equation.csv"
            eq_prefixed.touch()
            found_prefixed = find_equation_file(tmppath, "a.rch")
            self.assertIsNotNone(found_prefixed)
            self.assertEqual(found_prefixed.name, "a.rch_Max_step3_equation.csv")

    def test_read_user_equation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            eq_csv = tmppath / "Max_step3_equation.csv"

            # 1. 수식 문자열 정상 파싱
            formula = "0.5 * v0 + 0.5 * v2 + (2 * v1 - v0 - v2) / 2"
            eq_csv.write_text(f"{formula}\n", encoding="utf-8")
            self.assertEqual(read_user_equation(eq_csv), formula)

            # 2. 파일 없음 -> 빈 문자열
            self.assertEqual(read_user_equation(tmppath / "non_existent.csv"), "")

            # 3. None 전달 -> 빈 문자열
            self.assertEqual(read_user_equation(None), "")


class TestTimestampedOutFolderHelpers(unittest.TestCase):
    """신규 Converter out_YYMMDD_HHMMSS 결과 폴더 및 파일명 규격 탐색 검증"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tmpdir.name)

        # 이전 실행 폴더와 최신 실행 폴더 생성
        self.old_out = self.base / "out_260914_090000"
        self.old_out.mkdir()
        (self.old_out / "FlowDuration_1.csv").write_text(",2018,\n1,10.0\n", encoding="utf-8")

        self.latest_out = self.base / "out_260915_103942"
        self.latest_out.mkdir()

        # 최신 폴더에 파일 생성
        (self.latest_out / "FlowDuration_1.csv").write_text(
            ",2019,2020,\n1,50.0,60.0\n", encoding="utf-8"
        )
        (self.latest_out / "FlowDuration_9.csv").write_text(
            ",2019,2020,\n1,85.5,108.3\n", encoding="utf-8"
        )
        (self.latest_out / "1.csv").write_text(
            "2020-01-01,5.5\n2020-01-02,6.0\n", encoding="utf-8"
        )
        (self.latest_out / "9.csv").write_text(
            "2020-01-01,15.5\n2020-01-02,18.3\n", encoding="utf-8"
        )
        (self.latest_out / "all.csv").write_text(
            ",1,9\n2020-01-01,5.5,15.5\n2020-01-02,6.0,18.3\n", encoding="utf-8"
        )
        (self.latest_out / "Max_step3.csv").write_text(
            ",1,9\n2020,60.0,108.3\n", encoding="utf-8"
        )

        # rch 파일 더미 생성
        self.rch_file = self.base / "model.rch"
        self.rch_file.touch()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_find_latest_out_dir(self):
        latest = find_latest_out_dir(self.base)
        self.assertIsNotNone(latest)
        self.assertEqual(latest.name, "out_260915_103942")

    def test_resolve_effective_data_dir(self):
        # 1. out_* 하위 폴더를 가진 부모 디렉토리가 주어졌을 때 최신 out 폴더 자동 선택
        resolved = resolve_effective_data_dir(self.base)
        self.assertEqual(resolved.name, "out_260915_103942")

        # 2. out_* 폴더 자체가 주어졌을 때는 그대로 반환
        resolved_direct = resolve_effective_data_dir(self.latest_out)
        self.assertEqual(resolved_direct.name, "out_260915_103942")

    def test_find_files_in_new_format(self):
        # 1. FlowDuration 파일 탐색 (out_dir 직접 및 base 부모 폴더 모두 탐색 가능)
        fd1_direct = find_flow_duration_file(self.latest_out, reach_id=1)
        self.assertIsNotNone(fd1_direct)
        self.assertEqual(fd1_direct.name, "FlowDuration_1.csv")

        fd9_parent = find_flow_duration_file(self.base, reach_id=9)
        self.assertIsNotNone(fd9_parent)
        self.assertEqual(fd9_parent.name, "FlowDuration_9.csv")

        # 2. 일별 유량 파일 탐색 ({reach_id}.csv)
        d1_direct = find_daily_flow_file(self.latest_out, reach_id=1)
        self.assertIsNotNone(d1_direct)
        self.assertEqual(d1_direct.name, "1.csv")

        d9_parent = find_daily_flow_file(self.base, reach_id=9)
        self.assertIsNotNone(d9_parent)
        self.assertEqual(d9_parent.name, "9.csv")

        # 3. 소유역 목록 추출 ([1, 9])
        reaches_direct = find_available_reaches(self.latest_out)
        self.assertEqual(reaches_direct, [1, 9])

        reaches_parent = find_available_reaches(self.base)
        self.assertEqual(reaches_parent, [1, 9])

    def test_load_reach_flows_with_latest_out(self):
        from swat_k.core.gis_visualizer import load_reach_flows

        flows = load_reach_flows(str(self.rch_file), year=2020)
        self.assertIn(1, flows)
        self.assertIn(9, flows)
        self.assertEqual(flows[1], 6.0)
        self.assertEqual(flows[9], 18.3)


class TestSettingsDataDirAndReach(unittest.TestCase):
    """settings 모듈의 data_dir, target_year, target_reach 관리 검증"""

    def test_data_dir_fallback_and_persistence(self):
        settings.set_data_dir("")
        settings.set_rch_path(r"C:\test_project\output.rch")
        self.assertEqual(settings.get_data_dir(), r"C:\test_project")

        settings.set_data_dir(r"C:\custom_data_dir")
        self.assertEqual(settings.get_data_dir(), r"C:\custom_data_dir")

    def test_target_year_fallback_and_sync(self):
        settings.set_target_year("")
        settings.set_start_year("2015")
        self.assertEqual(settings.get_target_year(), "2015")

        settings.set_target_year("2020")
        self.assertEqual(settings.get_target_year(), "2020")
        self.assertEqual(settings.get_start_year(), "2020")

    def test_target_reach_persistence(self):
        settings.set_target_reach(9)
        self.assertEqual(settings.get_target_reach(), 9)
        settings.set_target_reach(1)
        self.assertEqual(settings.get_target_reach(), 1)


    def test_layer_and_field_settings(self):
        settings.set_selected_layer_name("subs1")
        self.assertEqual(settings.get_selected_layer_name(), "subs1")

        settings.set_selected_reach_field("Subbasin")
        self.assertEqual(settings.get_selected_reach_field(), "Subbasin")


class MockField:
    def __init__(self, name: str):
        self._name = name

    def name(self) -> str:
        return self._name


class MockFeature:
    def __init__(self, feat_id: int, attrs: dict):
        self._id = feat_id
        self._attrs = attrs

    def id(self) -> int:
        return self._id

    def __getitem__(self, key: str):
        return self._attrs[key]


class MockVectorLayer:
    def __init__(self, name: str, field_names: list[str], features: list[MockFeature] | None = None):
        self._name = name
        self._fields = [MockField(f) for f in field_names]
        self._features = features or []
        self.selected_ids = []

    def name(self) -> str:
        return self._name

    def id(self) -> str:
        return f"{self._name}_id"

    def isValid(self) -> bool:
        return True

    def type(self) -> int:
        return 0

    def fields(self) -> list[MockField]:
        return self._fields

    def getFeatures(self, req=None):
        return iter(self._features)

    def selectByIds(self, ids: list[int]):
        self.selected_ids = list(ids)

    def removeSelection(self):
        self.selected_ids = []


class TestViewDialogLayerAndField(unittest.TestCase):
    """QGIS 벡터 레이어 및 속성 필드 콤보박스 연동 테스트"""

    def test_headless_layer_combo_fallback(self):
        # QGIS 프로젝트가 없는 환경에서는 레이어 콤보가 안내 문구로 비활성화됨
        dialog = ViewDialog()
        self.assertEqual(dialog.combo_layer.count(), 1)
        self.assertEqual(dialog.combo_layer.itemText(0), "(로드된 QGIS 레이어 없음)")
        self.assertFalse(dialog.combo_layer.isEnabled())
        self.assertEqual(dialog.combo_field.count(), 0)
        self.assertFalse(dialog.combo_field.isEnabled())
        dialog.close()

    def test_mock_layer_and_field_selection(self):
        feat1 = MockFeature(101, {"OBJECTID": 1, "Subbasin": 1, "Area": 120.5})
        feat9 = MockFeature(109, {"OBJECTID": 2, "Subbasin": 9, "Area": 250.8})
        layer = MockVectorLayer("subs1", ["OBJECTID", "Subbasin", "Area"], [feat1, feat9])

        dialog = ViewDialog()
        dialog.combo_layer.setEnabled(True)
        dialog.combo_layer.addItem(layer.name(), userData=layer)
        dialog.combo_layer.setCurrentText(layer.name())

        # 1. 레이어 변경 슬롯 호출
        dialog._on_layer_changed(layer.name())

        # 2. 필드 콤보에 ["OBJECTID", "Subbasin", "Area"]가 채워졌는지 검증
        field_items = [dialog.combo_field.itemText(i) for i in range(dialog.combo_field.count())]
        self.assertIn("OBJECTID", field_items)
        self.assertIn("Subbasin", field_items)
        self.assertIn("Area", field_items)

        # 3. Subbasin 필드가 자동 추천/선택되었는지 검증
        self.assertEqual(dialog.combo_field.currentText(), "Subbasin")
        self.assertEqual(settings.get_selected_reach_field(), "Subbasin")
        self.assertEqual(settings.get_selected_layer_name(), "subs1")

        # 4. 하이라이트 함수 검증
        from swat_k.core.gis_visualizer import highlight_subbasin_feature

        res = highlight_subbasin_feature(9, target_layer=layer, reach_field="Subbasin")
        self.assertTrue(res)
        self.assertEqual(layer.selected_ids, [109])

        # 존재하지 않는 소유역 하이라이트 시도 -> 빈 선택
        res_none = highlight_subbasin_feature(999, target_layer=layer, reach_field="Subbasin")
        self.assertFalse(res_none)
        self.assertEqual(layer.selected_ids, [])

        dialog.close()


class TestViewDialog(unittest.TestCase):
    """ViewDialog UI 및 콤보박스 / 배너 명시적 표출 연동 테스트"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmppath = Path(self.tmpdir.name)

        # 1번 소유역 데이터 생성
        self.fd1 = self.tmppath / "model.rch_FlowDuration_1.csv"
        self.fd1.write_text(
            ",2019,2020,\n1,50.0,60.0\n",
            encoding="utf-8",
        )
        self.d1 = self.tmppath / "model.rch_1.csv"
        self.d1.write_text(
            "2019-07-01,50.0\n2020-07-01,60.0\n",
            encoding="utf-8",
        )

        # 9번 소유역 데이터 생성
        self.fd9 = self.tmppath / "model.rch_FlowDuration_9.csv"
        self.fd9.write_text(
            ",2019,2020,\n1,85.5,108.3\n",
            encoding="utf-8",
        )
        self.d9 = self.tmppath / "model.rch_9.csv"
        self.d9.write_text(
            "2019-07-01,85.5\n2020-07-01,108.3\n",
            encoding="utf-8",
        )

        # Step 3 첨두홍수량 요약 파일 생성
        self.s3 = self.tmppath / "model.rch_Max_step3.csv"
        self.s3.write_text(
            ",1,9\n2019,50.0,85.5\n2020,60.0,108.3\n",
            encoding="utf-8",
        )

        # 수식 파일 생성 (Max_step3_equation.csv)
        self.eq_file = self.tmppath / "model.rch_Max_step3_equation.csv"
        self.eq_formula = "0.5 * v0 + 0.5 * v2 + (2 * v1 - v0 - v2) / 2"
        self.eq_file.write_text(f"{self.eq_formula}\n", encoding="utf-8")

        # settings 사전 설정
        settings.set_data_dir(str(self.tmppath))
        settings.set_rch_path(str(self.tmppath / "model.rch"))
        settings.set_target_reach(1)
        settings.set_target_year("2020")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_view_dialog_reach_and_year_explicit_display(self):
        dialog = ViewDialog()

        # 1. 소유역 콤보에 1번, 9번이 모두 등록되었는지 확인
        reach_items = [dialog.combo_reach.itemText(i) for i in range(dialog.combo_reach.count())]
        self.assertIn("1번 소유역", reach_items)
        self.assertIn("9번 소유역", reach_items)

        # 2. 연도 콤보 확인
        year_items = [dialog.combo_year.itemText(i) for i in range(dialog.combo_year.count())]
        self.assertIn("2019", year_items)
        self.assertIn("2020", year_items)

        # 3. 소유역을 9번으로 전환 (사용자 시나리오: 9번 소유역 선택 + 2020년 지정)
        dialog.set_target_reach(9)
        dialog.combo_year.setCurrentText("2020")

        # 4. 명시적 안내 배너 검증 ("9번 소유역", "2020년")
        banner_text = dialog.label_banner.text()
        self.assertIn("9번 소유역", banner_text)
        self.assertIn("2020년", banner_text)

        # 5. 사용자 식 라벨 검증
        eq_text = dialog.label_equation.text()
        self.assertIn("사용자 식:", eq_text)
        self.assertIn(self.eq_formula, eq_text)

        # 6. 차트 제목 검증
        daily_title = dialog.ax_daily.get_title()
        self.assertIn("9번 소유역", daily_title)
        self.assertIn("2020년", daily_title)

        duration_title = dialog.ax_duration.get_title()
        self.assertIn("9번 소유역", duration_title)
        self.assertIn("2020년", duration_title)

        # 7. 홍수량 통계 수치 검증 (Reach 9의 2020년 데이터: 108.30 m³/s)
        self.assertIn("108.30", dialog.label_max_flow_val.text())
        self.assertIn("108.30", dialog.label_peak_flow_val.text())

        dialog.close()


if __name__ == "__main__":
    unittest.main()
