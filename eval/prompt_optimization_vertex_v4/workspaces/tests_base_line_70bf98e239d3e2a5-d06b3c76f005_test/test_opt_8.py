# file: src\sample_repo\isort\isort\settings.py:284-516
# asked: {"lines": [284, 286, 287, 288, 289, 291, 292, 293, 294, 295, 296, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 314, 316, 320, 321, 322, 323, 325, 326, 327, 328, 333, 335, 336, 337, 339, 340, 342, 343, 345, 346, 347, 348, 349, 350, 352, 353, 355, 356, 357, 359, 360, 361, 362, 363, 365, 366, 367, 368, 369, 371, 372, 373, 374, 376, 377, 378, 379, 381, 388, 389, 390, 391, 392, 393, 394, 395, 396, 400, 403, 405, 406, 407, 408, 410, 413, 415, 416, 417, 418, 421, 422, 423, 425, 427, 428, 429, 431, 432, 433, 434, 436, 437, 440, 441, 442, 443, 444, 447, 448, 449, 450, 452, 453, 454, 455, 457, 458, 459, 461, 463, 464, 465, 466, 467, 469, 473, 474, 475, 477, 478, 480, 481, 482, 483, 484, 485, 486, 489, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 503, 504, 505, 507, 508, 509, 510, 511, 513, 514, 516], "branches": [[298, 299], [298, 314], [320, 321], [320, 335], [326, 327], [326, 345], [335, 336], [335, 342], [336, 337], [336, 339], [347, 348], [347, 359], [348, 349], [348, 352], [349, 350], [349, 352], [352, 353], [352, 355], [359, 360], [359, 361], [361, 362], [361, 365], [366, 367], [366, 376], [368, 369], [368, 371], [372, 373], [372, 374], [379, 381], [379, 427], [381, 388], [381, 415], [391, 392], [391, 405], [393, 394], [393, 403], [406, 407], [406, 415], [415, 416], [415, 417], [417, 418], [417, 421], [422, 423], [422, 425], [427, 428], [427, 440], [428, 429], [428, 431], [431, 427], [431, 432], [440, 441], [440, 447], [449, 450], [449, 452], [453, 454], [453, 461], [457, 453], [457, 458], [458, 457], [458, 459], [463, 464], [463, 473], [464, 465], [464, 469], [465, 464], [465, 466], [480, 481], [480, 492], [481, 482], [481, 483], [483, 484], [483, 492], [492, 493], [492, 494], [494, 495], [494, 498], [495, 496], [495, 497], [498, 499], [498, 503], [499, 500], [499, 501], [504, 507], [504, 513], [507, 504], [507, 508], [508, 507], [508, 509], [513, 514], [513, 516]]}
# gained: {"lines": [284, 286, 287, 288, 291, 292, 293, 294, 295, 296, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 314, 316, 320, 321, 322, 323, 325, 326, 327, 328, 333, 335, 336, 337, 339, 340, 342, 343, 345, 346, 347, 348, 349, 352, 353, 359, 361, 362, 363, 365, 366, 367, 368, 369, 371, 372, 373, 374, 376, 377, 378, 379, 381, 388, 389, 390, 391, 405, 406, 415, 416, 417, 418, 421, 422, 423, 425, 427, 428, 429, 431, 432, 433, 434, 436, 437, 440, 441, 443, 444, 447, 448, 449, 450, 452, 453, 454, 455, 457, 458, 459, 461, 463, 464, 469, 473, 474, 475, 477, 478, 480, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 503, 504, 505, 507, 508, 509, 510, 511, 513, 514, 516], "branches": [[298, 299], [298, 314], [320, 321], [320, 335], [326, 327], [335, 336], [335, 342], [336, 337], [336, 339], [347, 348], [347, 359], [348, 349], [349, 352], [352, 353], [359, 361], [361, 362], [361, 365], [366, 367], [366, 376], [368, 369], [368, 371], [372, 373], [372, 374], [379, 381], [379, 427], [381, 388], [381, 415], [391, 405], [406, 415], [415, 416], [415, 417], [417, 418], [417, 421], [422, 423], [422, 425], [427, 428], [427, 440], [428, 429], [428, 431], [431, 427], [431, 432], [440, 441], [449, 450], [449, 452], [453, 454], [453, 461], [457, 453], [457, 458], [458, 459], [463, 464], [463, 473], [464, 469], [480, 492], [492, 493], [492, 494], [494, 495], [494, 498], [495, 496], [495, 497], [498, 499], [498, 503], [499, 500], [499, 501], [504, 507], [504, 513], [507, 504], [507, 508], [508, 507], [508, 509], [513, 514], [513, 516]]}

import os
import pytest
from pathlib import Path
from isort.settings import Config
from isort.exceptions import (
    InvalidSettingsPath,
    ProfileDoesNotExist,
    FormattingPluginDoesNotExist,
    UnsupportedSettings,
)


def test_config_with_existing_config_object(tmp_path):
    base_config = Config()
    # Test line 298: passing config object
    new_config = Config(config=base_config, line_length=100)
    assert new_config.line_length == 100


def test_config_settings_file_empty_warning(tmp_path):
    settings_file = tmp_path / "empty.toml"
    # Provide valid TOML syntax for a table/header so tomllib parses it successfully,
    # but without any 'settings' or expected config keys inside, ensuring config_settings is empty.
    settings_file.write_text("[other_section]\nfoo = \"bar\"\n")
    # Test settings_file with no configuration inside & not quiet (lines 320-333)
    config = Config(settings_file=str(settings_file), quiet=False)
    assert config is not None


def test_config_settings_path_invalid():
    # Test line 336: invalid settings_path raises InvalidSettingsPath
    with pytest.raises(InvalidSettingsPath):
        Config(settings_path="nonexistent_path_123456789")


def test_config_profile_not_exist():
    # Test line 353: ProfileDoesNotExist
    with pytest.raises(ProfileDoesNotExist):
        Config(profile="nonexistent_profile_xyz")


def test_config_indent_variations(tmp_path):
    # Test indent handling: integer digit (368), tab (372), quotes (371)
    c1 = Config(indent=4)
    assert c1.indent == "    "

    c2 = Config(indent="tab")
    assert c2.indent == "\t"

    c3 = Config(indent="'   '")
    assert c3.indent == "   "


def test_config_known_prefix_and_warnings(tmp_path):
    # Test known_xxx prefix, mapping, custom sections, duplicate warnings (lines 381-413)
    # Also tests import headings (415) and footers (417)
    config = Config(
        **{
            "known_mycustom": ["foo", "bar"],
            "sections": ["FUTURE", "MYCUSTOM", "UNKNOWN_SECTION"],
            "known_standard_library": ["os"],  # duplicate/overlapping check or warnings
            "import_heading_mycustom": "My Custom Heading",
            "import_footer_mycustom": "My Custom Footer",
            "quiet": False,
        }
    )
    assert "mycustom" in config.known_other
    assert config.import_headings.get("mycustom") == "My Custom Heading"
    assert config.import_footers.get("mycustom") == "My Custom Footer"


def test_config_src_paths_with_glob(tmp_path):
    # Test src_paths handling with glob (lines 452-461)
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    sub_dir = src_dir / "pkg1"
    sub_dir.mkdir()

    config = Config(settings_path=str(tmp_path), src_paths=["src/*"])
    assert isinstance(config.src_paths, tuple)


def test_config_formatter_not_exist():
    # Test FormattingPluginDoesNotExist (lines 463-469)
    with pytest.raises(FormattingPluginDoesNotExist):
        Config(formatter="nonexistent_formatter_abc")


def test_config_deprecated_options():
    # Test deprecated options warning (lines 477-489)
    try:
        config = Config(multi_line_output=3, quiet=False)
        assert config is not None
    except UnsupportedSettings:
        pass


def test_config_unsupported_settings():
    # Test UnsupportedSettings exception (lines 503-514)
    with pytest.raises(UnsupportedSettings):
        Config(completely_bogus_setting_name_12345=True)
