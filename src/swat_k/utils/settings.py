"""SWAT-K 설정 관리 모듈 (QSettings 기반)"""

try:
    from qgis.PyQt.QtCore import QSettings
except ImportError:
    from PySide6.QtCore import QSettings

from swat_k.core.formula import DEFAULT_FORMULA

ORGANIZATION = "KICT"
APPLICATION = "SWAT-K"

KEY_CONVERTER_EXE = "converter_exe_path"
KEY_RCH_PATH = "rch_file_path"
KEY_CIO_PATH = "cio_file_path"
KEY_START_YEAR = "start_year"
KEY_CUSTOM_FORMULA = "custom_formula"
KEY_STREAM_SHP_PATH = "stream_shp_path"
KEY_SUBBASIN_SHP_PATH = "subbasin_shp_path"


def _get_settings() -> QSettings:
    return QSettings(ORGANIZATION, APPLICATION)


def get_converter_exe_path() -> str:
    return str(_get_settings().value(KEY_CONVERTER_EXE, ""))


def set_converter_exe_path(path: str) -> None:
    _get_settings().setValue(KEY_CONVERTER_EXE, path)


def get_rch_path() -> str:
    return str(_get_settings().value(KEY_RCH_PATH, ""))


def set_rch_path(path: str) -> None:
    _get_settings().setValue(KEY_RCH_PATH, path)


def get_cio_path() -> str:
    return str(_get_settings().value(KEY_CIO_PATH, ""))


def set_cio_path(path: str) -> None:
    _get_settings().setValue(KEY_CIO_PATH, path)


def get_start_year() -> str:
    return str(_get_settings().value(KEY_START_YEAR, ""))


def set_start_year(year: str) -> None:
    _get_settings().setValue(KEY_START_YEAR, year)


def get_custom_formula() -> str:
    val = _get_settings().value(KEY_CUSTOM_FORMULA, "")
    return str(val) if val else DEFAULT_FORMULA


def set_custom_formula(formula: str) -> None:
    _get_settings().setValue(KEY_CUSTOM_FORMULA, formula)


def get_stream_shp_path() -> str:
    return str(_get_settings().value(KEY_STREAM_SHP_PATH, ""))


def set_stream_shp_path(path: str) -> None:
    _get_settings().setValue(KEY_STREAM_SHP_PATH, path)


def get_subbasin_shp_path() -> str:
    return str(_get_settings().value(KEY_SUBBASIN_SHP_PATH, ""))


def set_subbasin_shp_path(path: str) -> None:
    _get_settings().setValue(KEY_SUBBASIN_SHP_PATH, path)
