# file: src\sample_repo\isort\isort\settings.py:284-516
# asked: {"lines": [284, 286, 287, 288, 289, 291, 292, 293, 294, 295, 296, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 314, 316, 320, 321, 322, 323, 325, 326, 327, 328, 333, 335, 336, 337, 339, 340, 342, 343, 345, 346, 347, 348, 349, 350, 352, 353, 355, 356, 357, 359, 360, 361, 362, 363, 365, 366, 367, 368, 369, 371, 372, 373, 374, 376, 377, 378, 379, 381, 388, 389, 390, 391, 392, 393, 394, 395, 396, 400, 403, 405, 406, 407, 408, 410, 413, 415, 416, 417, 418, 421, 422, 423, 425, 427, 428, 429, 431, 432, 433, 434, 436, 437, 440, 441, 442, 443, 444, 447, 448, 449, 450, 452, 453, 454, 455, 457, 458, 459, 461, 463, 464, 465, 466, 467, 469, 473, 474, 475, 477, 478, 480, 481, 482, 483, 484, 485, 486, 489, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 503, 504, 505, 507, 508, 509, 510, 511, 513, 514, 516], "branches": [[298, 299], [298, 314], [320, 321], [320, 335], [326, 327], [326, 345], [335, 336], [335, 342], [336, 337], [336, 339], [347, 348], [347, 359], [348, 349], [348, 352], [349, 350], [349, 352], [352, 353], [352, 355], [359, 360], [359, 361], [361, 362], [361, 365], [366, 367], [366, 376], [368, 369], [368, 371], [372, 373], [372, 374], [379, 381], [379, 427], [381, 388], [381, 415], [391, 392], [391, 405], [393, 394], [393, 403], [406, 407], [406, 415], [415, 416], [415, 417], [417, 418], [417, 421], [422, 423], [422, 425], [427, 428], [427, 440], [428, 429], [428, 431], [431, 427], [431, 432], [440, 441], [440, 447], [449, 450], [449, 452], [453, 454], [453, 461], [457, 453], [457, 458], [458, 457], [458, 459], [463, 464], [463, 473], [464, 465], [464, 469], [465, 464], [465, 466], [480, 481], [480, 492], [481, 482], [481, 483], [483, 484], [483, 492], [492, 493], [492, 494], [494, 495], [494, 498], [495, 496], [495, 497], [498, 499], [498, 503], [499, 500], [499, 501], [504, 507], [504, 513], [507, 504], [507, 508], [508, 507], [508, 509], [513, 514], [513, 516]]}
# gained: {"lines": [284, 286, 287, 288, 291, 292, 293, 294, 295, 296, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 314, 316, 320, 321, 322, 323, 325, 326, 327, 328, 333, 335, 336, 337, 342, 343, 345, 346, 347, 348, 349, 352, 353, 355, 356, 357, 359, 361, 362, 363, 365, 366, 367, 368, 369, 371, 372, 373, 374, 376, 377, 378, 379, 381, 388, 389, 390, 391, 405, 406, 415, 416, 417, 418, 421, 422, 423, 425, 427, 428, 429, 431, 432, 433, 434, 436, 437, 440, 441, 443, 444, 447, 448, 449, 450, 452, 453, 454, 455, 457, 458, 459, 461, 463, 464, 469, 473, 474, 475, 477, 478, 480, 481, 482, 483, 484, 485, 486, 489, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 503, 504, 505, 507, 508, 509, 510, 511, 513, 514, 516], "branches": [[298, 299], [298, 314], [320, 321], [320, 335], [326, 327], [335, 336], [335, 342], [336, 337], [347, 348], [347, 359], [348, 349], [348, 352], [349, 352], [352, 353], [352, 355], [359, 361], [361, 362], [361, 365], [366, 367], [366, 376], [368, 369], [368, 371], [372, 373], [372, 374], [379, 381], [379, 427], [381, 388], [381, 415], [391, 405], [406, 415], [415, 416], [415, 417], [417, 418], [417, 421], [422, 423], [422, 425], [427, 428], [427, 440], [428, 429], [428, 431], [431, 427], [431, 432], [440, 441], [440, 447], [449, 450], [449, 452], [453, 454], [453, 461], [457, 453], [457, 458], [458, 459], [463, 464], [463, 473], [464, 469], [480, 481], [480, 492], [481, 482], [481, 483], [483, 484], [492, 493], [492, 494], [494, 495], [494, 498], [495, 496], [495, 497], [498, 499], [498, 503], [499, 500], [499, 501], [504, 507], [504, 513], [507, 504], [507, 508], [508, 507], [508, 509], [513, 514], [513, 516]]}

import os
from pathlib import Path
import pytest

from isort.exceptions import (
    FormattingPluginDoesNotExist,
    InvalidSettingsPath,
    ProfileDoesNotExist,
    UnsupportedSettings,
)
from isort.settings import Config


def test_config_with_config_object():
    base_cfg = Config(profile="black")
    new_cfg = Config(config=base_cfg, quiet=True)
    assert new_cfg.profile == "black"


def test_config_with_settings_file_empty(tmp_path):
    settings_file = tmp_path / ".isort.cfg"
    settings_file.write_text("[settings]\n")
    # This hits settings_file handling, empty config warning (if quiet=False)
    cfg = Config(settings_file=str(settings_file), quiet=False)
    assert cfg is not None


def test_config_with_invalid_settings_path():
    with pytest.raises(InvalidSettingsPath):
        Config(settings_path="/non/existent/path/123456")


def test_config_profile_not_found():
    with pytest.raises(ProfileDoesNotExist):
        Config(profile="non_existent_profile_xyz")


def test_config_indent_variations():
    cfg1 = Config(indent=4)
    assert cfg1.indent == "    "

    cfg2 = Config(indent="tab")
    assert cfg2.indent == "\t"

    cfg3 = Config(indent="'--'")
    assert cfg3.indent == "--"


def test_config_known_prefix_and_sections(tmp_path):
    # Tests KNOWN_PREFIX handling, section mapping conflicts, unknown section warnings, etc.
    cfg = Config(
        known_mycustom="foo,bar",
        sections=["FUTURE", "MYCUSTOM", "MISSINGSECTION"],
        import_heading_mycustom="Heading",
        import_footer_mycustom="Footer",
        quiet=False,
    )
    assert "mycustom" in cfg.known_other


def test_config_src_paths_glob_and_default(tmp_path):
    sub = tmp_path / "src" / "pkg"
    sub.mkdir(parents=True)
    # Test directory fallback when directory not in combined_config
    cfg1 = Config(directory=str(tmp_path), src_paths=("*",))
    assert len(cfg1.src_paths) >= 1

    # Test file is_dir() fallback
    file_path = tmp_path / "file.py"
    file_path.write_text("")
    cfg2 = Config(directory=str(file_path), src_paths=("pkg",))
    assert cfg2 is not None


def test_config_formatter_not_exist():
    with pytest.raises(FormattingPluginDoesNotExist):
        Config(formatter="non_existent_formatter_abc")


def test_config_deprecated_settings():
    # isort uses some deprecated settings like 'not_skip' or similar if present, or let's check DEPRECATED_SETTINGS
    from isort.settings import DEPRECATED_SETTINGS
    if DEPRECATED_SETTINGS:
        dep_opt = next(iter(DEPRECATED_SETTINGS))
        cfg = Config(**{dep_opt: "something", "quiet": False})
        assert cfg is not None


def test_config_unsupported_settings():
    with pytest.raises(UnsupportedSettings):
        Config(completely_unsupported_setting_xyz=123)
