"""SWAT-K Converter 콘솔 출력 파싱 및 진행률 계산 모듈"""

import re


class ConverterOutputParser:
    """Converter 콘솔 출력을 한 줄씩 파싱하여 진행률 및 상태 메시지를 산출하는 클래스"""

    def __init__(self):
        self.start_year: int | None = None
        self.end_year: int | None = None
        self.current_year: int | None = None
        self.progress_percent: int = 0
        self.status_message: str = "변환 작업을 초기화하는 중..."
        self.is_completed: bool = False

        self._re_start_year = re.compile(r"start\s+year\s+(\d+)", re.IGNORECASE)
        self._re_year_end = re.compile(r"year\s+end\s+(\d+)", re.IGNORECASE)
        self._re_processing_year = re.compile(
            r"Processing\s*\.\.\s*year\s+(\d+)", re.IGNORECASE
        )
        self._re_reading_completed = re.compile(
            r"completed\s*\(\s*reading\s*\)", re.IGNORECASE
        )
        self._re_generating = re.compile(r"Generating\s*\.\.", re.IGNORECASE)
        self._re_final_completed = re.compile(
            r"completed\s*,\s*[\d\.]+\s*minutes", re.IGNORECASE
        )

    def feed_line(self, line: str) -> tuple[int, str, bool]:
        """콘솔 출력 라인을 입력받아 갱신된 (진행률, 상태메시지, 완료여부)를 반환합니다.

        Args:
            line: 콘솔 출력 문자열 한 줄

        Returns:
            (진행률 0~100, 상태 메시지, 완료 여부)
        """
        text = line.strip()
        if not text:
            return self.progress_percent, self.status_message, self.is_completed

        # 1. 시작 연도 감지
        m_start = self._re_start_year.search(text)
        if m_start:
            self.start_year = int(m_start.group(1))
            self.progress_percent = max(self.progress_percent, 5)
            self.status_message = f"시작 연도 확인: {self.start_year}년"
            return self.progress_percent, self.status_message, self.is_completed

        # 2. 종료 연도 감지
        m_end = self._re_year_end.search(text)
        if m_end:
            self.end_year = int(m_end.group(1))
            self.progress_percent = max(self.progress_percent, 10)
            period = f"{self.start_year or '?'} ~ {self.end_year}년"
            self.status_message = f"시뮬레이션 기간: {period}"
            return self.progress_percent, self.status_message, self.is_completed

        # 3. 데이터 읽기 완료 감지
        if self._re_reading_completed.search(text):
            self.progress_percent = max(self.progress_percent, 12)
            self.status_message = "입력 데이터 읽기 완료, 변환 준비 중..."
            return self.progress_percent, self.status_message, self.is_completed

        # 4. 파일 생성 준비 감지
        if self._re_generating.search(text):
            self.progress_percent = max(self.progress_percent, 15)
            self.status_message = "출력 데이터 생성 준비 중..."
            return self.progress_percent, self.status_message, self.is_completed

        # 5. 연도별 처리 진행 (Processing .. year YYYY)
        m_year = self._re_processing_year.search(text)
        if m_year:
            self.current_year = int(m_year.group(1))
            if (
                self.start_year is not None
                and self.end_year is not None
                and self.end_year >= self.start_year
            ):
                total_years = self.end_year - self.start_year + 1
                processed_years = self.current_year - self.start_year + 1
                fraction = min(1.0, max(0.0, processed_years / total_years))
                # 15% ~ 95% 구간을 연도별 처리에 할당
                calculated = 15 + int(80 * fraction)
                self.progress_percent = max(self.progress_percent, calculated)
                self.status_message = (
                    f"데이터 변환 중... ({self.current_year}년 / {self.end_year}년)"
                )
            else:
                self.progress_percent = min(90, self.progress_percent + 10)
                self.status_message = f"데이터 변환 처리 중... ({self.current_year}년)"
            return self.progress_percent, self.status_message, self.is_completed

        # 6. 최종 완료 감지
        if self._re_final_completed.search(text):
            self.progress_percent = 100
            self.status_message = "변환 작업이 완료되었습니다."
            self.is_completed = True
            return self.progress_percent, self.status_message, self.is_completed

        return self.progress_percent, self.status_message, self.is_completed
