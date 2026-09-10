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
    find_daily_flow_file,
    find_flow_duration_file,
)

app = QApplication.instance() or QApplication(sys.argv)


class TestViewWindowHelpers(unittest.TestCase):
    """FlowDuration 및 유량 파일 탐색, 연도 추출 헬퍼 함수 검증"""

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
            self.assertIsNone(find_flow_duration_file(tmppath, "a.rch"))

            # 2. [rch]_FlowDuration_1.csv 우선 탐색
            fd1 = tmppath / "a.rch_FlowDuration_1.csv"
            fd1.touch()
            found = find_flow_duration_file(tmppath, "a.rch")
            self.assertEqual(found.name, "a.rch_FlowDuration_1.csv")

            # 3. a.rch_FlowDuration.csv 탐색 (사용자 언급 케이스)
            fd1.unlink()
            fd_user = tmppath / "a.rch_FlowDuration.csv"
            fd_user.touch()
            found_user = find_flow_duration_file(tmppath, "a.rch")
            self.assertEqual(found_user.name, "a.rch_FlowDuration.csv")

            # 4. 와일드카드 탐색 (rch_path가 없을 때)
            found_wildcard = find_flow_duration_file(tmppath, "")
            self.assertEqual(found_wildcard.name, "a.rch_FlowDuration.csv")

    def test_find_daily_flow_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # 1. 빈 디렉토리 -> None
            self.assertIsNone(find_daily_flow_file(tmppath, "a.rch"))

            # 2. a.rch_1.csv 탐색
            d1 = tmppath / "a.rch_1.csv"
            d1.touch()
            found = find_daily_flow_file(tmppath, "a.rch")
            self.assertEqual(found.name, "a.rch_1.csv")

            # 3. _all.csv 대체 탐색
            d1.unlink()
            all_csv = tmppath / "a.rch_all.csv"
            all_csv.touch()
            found_all = find_daily_flow_file(tmppath, "a.rch")
            self.assertEqual(found_all.name, "a.rch_all.csv")


class TestSettingsDataDirAndYear(unittest.TestCase):
    """settings 모듈의 data_dir 및 target_year 관리 검증"""

    def test_data_dir_fallback_and_persistence(self):
        # RCH 파일 경로로부터 data_dir 기본값 도출 확인
        settings.set_data_dir("")
        settings.set_rch_path(r"C:\test_project\output.rch")
        self.assertEqual(settings.get_data_dir(), r"C:\test_project")

        # 명시적 data_dir 설정 시 우선 반영 확인
        settings.set_data_dir(r"C:\custom_data_dir")
        self.assertEqual(settings.get_data_dir(), r"C:\custom_data_dir")

    def test_target_year_fallback_and_sync(self):
        # start_year와의 호환성 확인
        settings.set_target_year("")
        settings.set_start_year("2015")
        self.assertEqual(settings.get_target_year(), "2015")

        # target_year 저장 시 start_year도 동기화
        settings.set_target_year("2020")
        self.assertEqual(settings.get_target_year(), "2020")
        self.assertEqual(settings.get_start_year(), "2020")


class TestViewDialog(unittest.TestCase):
    """ViewDialog UI 및 콤보박스 연동 테스트"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmppath = Path(self.tmpdir.name)

        # 모의 FlowDuration 및 Daily CSV 파일 생성
        self.fd_csv = self.tmppath / "model.rch_FlowDuration_1.csv"
        self.fd_csv.write_text(
            ",2018,2019,2020,\n"
            "1,50.5,60.2,45.8\n"
            "2,30.1,35.0,25.4\n",
            encoding="utf-8",
        )

        self.daily_csv = self.tmppath / "model.rch_1.csv"
        self.daily_csv.write_text(
            "2018-07-01,50.5\n"
            "2018-07-02,30.1\n"
            "2019-07-01,60.2\n"
            "2020-07-01,45.8\n",
            encoding="utf-8",
        )

        # settings 사전 설정
        settings.set_data_dir(str(self.tmppath))
        settings.set_rch_path(str(self.tmppath / "model.rch"))
        settings.set_target_year("2019")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_view_dialog_loads_years_and_updates_chart(self):
        dialog = ViewDialog()

        # 1. UI에 데이터 폴더가 올바르게 설정되었는지 확인
        self.assertEqual(dialog.lineEdit_data_dir.text(), str(self.tmppath))

        # 2. 콤보박스에 연도 목록(2018, 2019, 2020)이 정상 등록되었는지 확인
        combo_items = [dialog.combo_year.itemText(i) for i in range(dialog.combo_year.count())]
        self.assertEqual(combo_items, ["2018", "2019", "2020"])

        # 3. 설정된 2019년이 선택되어 있는지 확인
        self.assertEqual(dialog.combo_year.currentText(), "2019")

        # 4. 2019년 최대 유량 라벨 검증 (60.20 m³/s)
        self.assertIn("60.20", dialog.label_max_flow_val.text())

        # 5. 연도를 2018년으로 변경 시 라벨 갱신 확인 (50.50 m³/s)
        dialog.combo_year.setCurrentText("2018")
        self.assertEqual(settings.get_target_year(), "2018")
        self.assertIn("50.50", dialog.label_max_flow_val.text())

        dialog.close()


if __name__ == "__main__":
    unittest.main()
