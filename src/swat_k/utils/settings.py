from pathlib import Path

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
KEY_TARGET_YEAR = "target_year"
KEY_TARGET_REACH = "target_reach"
KEY_DATA_DIR = "data_dir"
KEY_CUSTOM_FORMULA = "custom_formula"
KEY_STREAM_SHP_PATH = "stream_shp_path"
KEY_SUBBASIN_SHP_PATH = "subbasin_shp_path"
KEY_SELECTED_LAYER_NAME = "selected_layer_name"
KEY_SELECTED_REACH_FIELD = "selected_reach_field"


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


def get_target_year() -> str:
    val = str(_get_settings().value(KEY_TARGET_YEAR, "")).strip()
    if not val:
        val = get_start_year()
    return val


def set_target_year(year: str) -> None:
    _get_settings().setValue(KEY_TARGET_YEAR, year)
    set_start_year(year)


def get_target_reach() -> int:
    val = _get_settings().value(KEY_TARGET_REACH, 1)
    try:
        r = int(val)
        return r if r > 0 else 1
    except (ValueError, TypeError):
        return 1


def set_target_reach(reach_id: int) -> None:
    _get_settings().setValue(KEY_TARGET_REACH, int(reach_id))


def find_latest_out_dir(base_dir: Path | str) -> Path | None:
    """rch 파일 디렉토리 등에서 가장 최근 생성된 out_timestamp 디렉토리를 탐색합니다."""
    if not base_dir:
        return None
    p = Path(base_dir)
    if not p.is_dir():
        return None
    out_dirs = [d for d in p.glob("out_*") if d.is_dir()]
    if not out_dirs:
        return None
    return sorted(out_dirs, key=lambda d: (d.name, d.stat().st_mtime), reverse=True)[0]


def get_data_dir() -> str:
    val = str(_get_settings().value(KEY_DATA_DIR, "")).strip()
    if not val:
        rch = get_rch_path()
        if rch:
            parent = Path(rch).parent
            out_dir = find_latest_out_dir(parent)
            if out_dir:
                return str(out_dir)
            return str(parent)
    return val


def set_data_dir(path: str) -> None:
    _get_settings().setValue(KEY_DATA_DIR, path)


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


def get_selected_layer_name() -> str:
    return str(_get_settings().value(KEY_SELECTED_LAYER_NAME, ""))


def set_selected_layer_name(name: str) -> None:
    _get_settings().setValue(KEY_SELECTED_LAYER_NAME, name)


def get_selected_reach_field() -> str:
    return str(_get_settings().value(KEY_SELECTED_REACH_FIELD, ""))


def set_selected_reach_field(field_name: str) -> None:
    _get_settings().setValue(KEY_SELECTED_REACH_FIELD, field_name)
