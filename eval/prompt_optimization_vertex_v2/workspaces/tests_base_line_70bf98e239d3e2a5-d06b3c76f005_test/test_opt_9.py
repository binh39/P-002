# file: src\sample_repo\isort\isort\settings.py:284-516
# asked: {"lines": [284, 286, 287, 288, 289, 291, 292, 293, 294, 295, 296, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 314, 316, 320, 321, 322, 323, 325, 326, 327, 328, 333, 335, 336, 337, 339, 340, 342, 343, 345, 346, 347, 348, 349, 350, 352, 353, 355, 356, 357, 359, 360, 361, 362, 363, 365, 366, 367, 368, 369, 371, 372, 373, 374, 376, 377, 378, 379, 381, 388, 389, 390, 391, 392, 393, 394, 395, 396, 400, 403, 405, 406, 407, 408, 410, 413, 415, 416, 417, 418, 421, 422, 423, 425, 427, 428, 429, 431, 432, 433, 434, 436, 437, 440, 441, 442, 443, 444, 447, 448, 449, 450, 452, 453, 454, 455, 457, 458, 459, 461, 463, 464, 465, 466, 467, 469, 473, 474, 475, 477, 478, 480, 481, 482, 483, 484, 485, 486, 489, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 503, 504, 505, 507, 508, 509, 510, 511, 513, 514, 516], "branches": [[298, 299], [298, 314], [320, 321], [320, 335], [326, 327], [326, 345], [335, 336], [335, 342], [336, 337], [336, 339], [347, 348], [347, 359], [348, 349], [348, 352], [349, 350], [349, 352], [352, 353], [352, 355], [359, 360], [359, 361], [361, 362], [361, 365], [366, 367], [366, 376], [368, 369], [368, 371], [372, 373], [372, 374], [379, 381], [379, 427], [381, 388], [381, 415], [391, 392], [391, 405], [393, 394], [393, 403], [406, 407], [406, 415], [415, 416], [415, 417], [417, 418], [417, 421], [422, 423], [422, 425], [427, 428], [427, 440], [428, 429], [428, 431], [431, 427], [431, 432], [440, 441], [440, 447], [449, 450], [449, 452], [453, 454], [453, 461], [457, 453], [457, 458], [458, 457], [458, 459], [463, 464], [463, 473], [464, 465], [464, 469], [465, 464], [465, 466], [480, 481], [480, 492], [481, 482], [481, 483], [483, 484], [483, 492], [492, 493], [492, 494], [494, 495], [494, 498], [495, 496], [495, 497], [498, 499], [498, 503], [499, 500], [499, 501], [504, 507], [504, 513], [507, 504], [507, 508], [508, 507], [508, 509], [513, 514], [513, 516]]}
# gained: {"lines": [284, 286, 287, 288, 291, 292, 293, 294, 295, 296, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 314, 316, 320, 321, 322, 323, 325, 326, 327, 328, 333, 335, 336, 337, 339, 340, 342, 343, 345, 346, 347, 348, 349, 352, 353, 359, 360, 361, 362, 363, 365, 366, 367, 368, 369, 371, 372, 373, 374, 376, 377, 378, 379, 381, 388, 389, 390, 391, 405, 406, 415, 416, 417, 418, 421, 422, 423, 425, 427, 428, 429, 431, 432, 433, 434, 436, 437, 440, 441, 442, 443, 444, 447, 448, 449, 450, 452, 453, 454, 455, 457, 458, 459, 461, 463, 464, 469, 473, 474, 475, 477, 478, 480, 481, 482, 483, 484, 485, 486, 489, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 503, 504, 505, 507, 508, 509, 510, 511, 513, 514, 516], "branches": [[298, 299], [298, 314], [320, 321], [320, 335], [326, 327], [326, 345], [335, 336], [335, 342], [336, 337], [336, 339], [347, 348], [347, 359], [348, 349], [349, 352], [352, 353], [359, 360], [359, 361], [361, 362], [361, 365], [366, 367], [366, 376], [368, 369], [368, 371], [372, 373], [372, 374], [379, 381], [379, 427], [381, 388], [381, 415], [391, 405], [406, 415], [415, 416], [415, 417], [417, 418], [417, 421], [422, 423], [422, 425], [427, 428], [427, 440], [428, 429], [428, 431], [431, 427], [431, 432], [440, 441], [449, 450], [449, 452], [453, 454], [453, 461], [457, 453], [457, 458], [458, 459], [463, 464], [463, 473], [464, 469], [480, 481], [480, 492], [481, 482], [481, 483], [483, 484], [492, 493], [492, 494], [494, 495], [494, 498], [495, 496], [495, 497], [498, 499], [498, 503], [499, 500], [499, 501], [504, 507], [504, 513], [507, 504], [507, 508], [508, 507], [508, 509], [513, 514], [513, 516]]}

import os
import pytest
from pathlib import Path
from isort.exceptions import (
    FormattingPluginDoesNotExist,
    InvalidSettingsPath,
    ProfileDoesNotExist,
    UnsupportedSettings,
)
from isort.settings import Config


def test_config_with_existing_config_object():
    base_config = Config()
    config = Config(config=base_config, py_version="py38")
    assert config is not None


def test_config_settings_file_empty():
    # Use standard temporary file / folder naming without tmp_path fixture to avoid Windows PermissionError on cleanup
    temp_dir = Path("test_temp_settings_dir")
    temp_dir.mkdir(exist_ok=True)
    try:
        settings_file = temp_dir / "setup.cfg"
        settings_file.write_text("[other]\nfoo = bar\n")
        config = Config(settings_file=str(settings_file))
        assert config is not None
    finally:
        for p in temp_dir.glob("*"):
            p.unlink()
        temp_dir.rmdir()


def test_config_settings_path_invalid():
    with pytest.raises(InvalidSettingsPath):
        Config(settings_path="/nonexistent/path/to/isort/config")


def test_config_settings_path_valid():
    temp_dir = Path("test_temp_path_dir")
    temp_dir.mkdir(exist_ok=True)
    try:
        isort_cfg = temp_dir / ".isort.cfg"
        isort_cfg.write_text("[isort]\nline_length = 100\n")
        config = Config(settings_path=str(temp_dir))
        assert config.line_length == 100
    finally:
        for p in temp_dir.glob("*"):
            p.unlink()
        temp_dir.rmdir()


def test_config_profile_not_exist():
    with pytest.raises(ProfileDoesNotExist):
        Config(profile="nonexistent_profile_xyz")


def test_config_indent_variations():
    c1 = Config(indent=4)
    assert c1.indent == "    "

    c2 = Config(indent="'\t'")
    assert c2.indent == "\t"

    c3 = Config(indent='"tab"')
    assert c3.indent == "\t"

    c4 = Config(indent=2)
    assert c4.indent == "  "


def test_config_known_prefix_warnings_and_mappings():
    temp_dir = Path("test_temp_known_dir")
    temp_dir.mkdir(exist_ok=True)
    try:
        isort_cfg = temp_dir / ".isort.cfg"
        isort_cfg.write_text(
            "[isort]\n"
            "known_foo = my_pkg\n"
            "known_third_party = other_pkg\n"
            "sections = STANDARD_LIBRARY, THIRDPARTY, FOO, BAR\n"
        )
        config = Config(settings_file=str(isort_cfg))
        assert "foo" in config.known_other
    finally:
        for p in temp_dir.glob("*"):
            p.unlink()
        temp_dir.rmdir()


def test_config_sections_missing_known():
    temp_dir = Path("test_temp_sections_dir")
    temp_dir.mkdir(exist_ok=True)
    try:
        isort_cfg = temp_dir / ".isort.cfg"
        isort_cfg.write_text(
            "[isort]\n"
            "sections = STANDARD_LIBRARY, THIRDPARTY, MY_CUSTOM_SECTION\n"
        )
        config = Config(settings_file=str(isort_cfg))
        assert config is not None
    finally:
        for p in temp_dir.glob("*"):
            p.unlink()
        temp_dir.rmdir()


def test_config_src_paths_explicit():
    temp_dir = Path("test_temp_src_dir")
    temp_dir.mkdir(exist_ok=True)
    try:
        src_dir = temp_dir / "src"
        src_dir.mkdir(exist_ok=True)
        config = Config(settings_path=str(temp_dir), src_paths=["src"])
        assert len(config.src_paths) == 1
    finally:
        for p in temp_dir.glob("*"):
            if p.is_dir():
                for sub in p.glob("*"):
                    sub.unlink()
                p.rmdir()
            else:
                p.unlink()
        temp_dir.rmdir()


def test_config_formatter_does_not_exist():
    with pytest.raises(FormattingPluginDoesNotExist):
        Config(formatter="nonexistent_formatter_plugin")


def test_config_deprecated_options():
    from isort.settings import DEPRECATED_SETTINGS
    if DEPRECATED_SETTINGS:
        dep_opt = next(iter(DEPRECATED_SETTINGS))
        config = Config(**{dep_opt: True, "quiet": False})
        assert config is not None


def test_config_import_headings_and_footers():
    temp_dir = Path("test_temp_headings_dir")
    temp_dir.mkdir(exist_ok=True)
    try:
        isort_cfg = temp_dir / ".isort.cfg"
        isort_cfg.write_text(
            "[isort]\n"
            "import_heading_firstparty = First Party\n"
            "import_footer_firstparty = End First Party\n"
        )
        config = Config(settings_file=str(isort_cfg))
        assert config.import_headings.get("firstparty") == "First Party"
        assert config.import_footers.get("firstparty") == "End First Party"
    finally:
        for p in temp_dir.glob("*"):
            p.unlink()
        temp_dir.rmdir()


def test_unsupported_settings():
    with pytest.raises(UnsupportedSettings):
        Config(completely_bogus_setting_name=123)
