"""Converter 콘솔 출력 파서 단위 테스트"""

import unittest

from swat_k.core.converter_parser import ConverterOutputParser

SAMPLE_OUTPUT = """2026-09-08 오후 4:38:52 start. Version = 2026.9.4.26
input_data_for_swat-k-console_exe__v2025.10\\output_v20251015.rch
input_data_for_swat-k-console_exe__v2025.10\\file.cio
User Equation = 0.5 * v0 + 0.5 * v2 + (2 * v1 - v0 - v2) /2
22.2
            2012    | IYR : Beginning year of simulation
               1    | NYSKIP: number of years to skip output printing/summarization
            2012
               1
start year 2013
2026-09-08 오후 4:38:52
2026-09-08 오후 4:38:54 completed (reading)
reach max = 12
39444
year end 2021
Generating .. output_v20251015.rch_12
reach : ,1,2,3,4,5,6,7,8,9,10,11,12
2026-09-08 오후 4:38:54 output_v20251015.rch_all
Processing .. year 2013
Processing .. year 2014
Processing .. year 2015
Processing .. year 2016
Processing .. year 2017
Processing .. year 2018
Processing .. year 2019
Processing .. year 2020
Processing .. year 2021
2026-09-08 오후 4:38:54 completed , 0.0 minutes collapsed
"""


class TestConverterOutputParser(unittest.TestCase):
    """ConverterOutputParser 동작 테스트"""

    def test_sample_output_parsing(self):
        """실제 콘솔 출력 샘플 전체 파싱 흐름 검증"""
        parser = ConverterOutputParser()
        lines = SAMPLE_OUTPUT.strip().splitlines()

        progress_history = []
        for line in lines:
            pct, msg, done = parser.feed_line(line)
            progress_history.append((pct, msg, done))

        # 1. 시작 및 종료 연도 파싱 확인
        self.assertEqual(parser.start_year, 2013)
        self.assertEqual(parser.end_year, 2021)
        self.assertEqual(parser.current_year, 2021)

        # 2. 진행률이 점진적으로 증가하였는지 확인
        percentages = [item[0] for item in progress_history]
        is_monotonic = all(
            percentages[i] <= percentages[i + 1] for i in range(len(percentages) - 1)
        )
        self.assertTrue(
            is_monotonic,
            "진행률은 감소하지 않고 점진적으로 증가해야 합니다.",
        )

        # 3. 최종 완료 확인
        self.assertEqual(parser.progress_percent, 100)
        self.assertTrue(parser.is_completed)
        self.assertIn("완료", parser.status_message)


if __name__ == "__main__":
    unittest.main()
