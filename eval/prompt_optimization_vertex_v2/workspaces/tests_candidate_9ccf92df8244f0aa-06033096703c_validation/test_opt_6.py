# file: src\sample_repo\isort\isort\output.py:247-569
# asked: {"lines": [247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 260, 261, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 276, 278, 279, 280, 283, 284, 285, 286, 288, 289, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 302, 304, 305, 306, 307, 308, 309, 310, 312, 313, 314, 315, 316, 317, 318, 320, 321, 323, 324, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 337, 338, 340, 341, 342, 344, 346, 347, 349, 350, 352, 353, 356, 357, 358, 359, 360, 361, 363, 364, 366, 370, 371, 372, 373, 374, 376, 377, 379, 382, 383, 385, 386, 388, 389, 390, 391, 394, 395, 397, 398, 399, 400, 402, 403, 404, 405, 406, 407, 408, 409, 410, 412, 413, 416, 418, 419, 420, 421, 422, 424, 425, 427, 428, 429, 430, 431, 432, 433, 435, 436, 440, 442, 443, 444, 445, 446, 447, 448, 451, 453, 454, 455, 457, 461, 462, 464, 465, 466, 468, 469, 470, 472, 473, 474, 475, 476, 477, 478, 480, 481, 483, 485, 486, 487, 489, 490, 493, 494, 495, 496, 498, 499, 500, 501, 502, 504, 505, 507, 509, 510, 511, 513, 514, 519, 520, 521, 523, 526, 527, 528, 530, 531, 532, 533, 534, 535, 536, 539, 540, 541, 542, 543, 544, 545, 547, 548, 549, 550, 551, 552, 553, 557, 558, 559, 561, 563, 564, 565, 567, 568, 569], "branches": [[256, 257], [256, 569], [257, 258], [257, 260], [262, 266], [262, 278], [278, 279], [278, 283], [291, 292], [291, 304], [292, 293], [292, 296], [293, 294], [293, 296], [294, 293], [294, 295], [296, 297], [296, 304], [297, 296], [297, 298], [299, 300], [299, 302], [307, 256], [307, 308], [308, 309], [308, 312], [312, 313], [312, 327], [327, 328], [327, 385], [329, 330], [329, 567], [340, 341], [340, 344], [344, 345], [344, 382], [345, 349], [345, 352], [356, 357], [356, 370], [385, 386], [385, 442], [388, 389], [388, 390], [393, 397], [393, 418], [402, 403], [402, 404], [418, 385], [418, 419], [424, 425], [424, 427], [442, 443], [442, 453], [453, 454], [453, 485], [457, 453], [457, 460], [460, 464], [460, 468], [469, 470], [469, 472], [486, 493], [486, 494], [494, 495], [494, 498], [504, 505], [504, 507], [510, 511], [510, 513], [513, 514], [513, 518], [518, 523], [518, 525], [525, 530], [525, 539], [539, 540], [539, 564], [547, 548], [547, 567], [556, 563], [556, 567], [564, 565], [564, 567], [567, 307], [567, 568]]}
# gained: {"lines": [247, 255, 256, 257, 260, 261, 263, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 276, 278, 279, 280, 283, 284, 285, 286, 288, 289, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 304, 305, 306, 307, 308, 309, 310, 312, 327, 328, 329, 330, 331, 332, 333, 334, 335, 337, 338, 340, 344, 382, 383, 385, 442, 443, 444, 445, 446, 447, 448, 451, 453, 454, 455, 457, 461, 468, 469, 470, 474, 475, 476, 477, 478, 480, 481, 483, 485, 486, 487, 493, 494, 495, 496, 498, 499, 500, 501, 502, 504, 507, 509, 510, 511, 513, 514, 519, 520, 521, 523, 526, 527, 539, 540, 541, 542, 543, 544, 545, 547, 548, 549, 550, 551, 552, 553, 557, 558, 559, 561, 563, 564, 565, 567, 568, 569], "branches": [[256, 257], [256, 569], [257, 260], [262, 266], [278, 279], [278, 283], [291, 292], [291, 304], [292, 293], [293, 294], [293, 296], [294, 295], [296, 297], [296, 304], [297, 296], [297, 298], [299, 300], [307, 256], [307, 308], [308, 309], [308, 312], [312, 327], [327, 328], [327, 385], [329, 330], [329, 567], [340, 344], [344, 382], [385, 442], [442, 443], [442, 453], [453, 454], [453, 485], [457, 453], [457, 460], [460, 468], [469, 470], [486, 493], [486, 494], [494, 495], [494, 498], [504, 507], [510, 511], [510, 513], [513, 514], [513, 518], [518, 523], [518, 525], [525, 539], [539, 540], [539, 564], [547, 548], [547, 567], [556, 563], [564, 565], [567, 307], [567, 568]]}

import copy
from collections.abc import Iterable
from isort import parse, sorting, wrap
from isort.settings import Config
from isort.output import _with_from_imports


def test_with_from_imports_full_coverage():
    # Construct a parsed content object using parse.ParsedContent with all required arguments
    # Note: categorized_comments["from"] values must be lists instead of tuples if combined with lists in output.py (line 495).
    parsed = parse.ParsedContent(
        in_lines=[],
        lines_without_imports=[],
        import_index=0,
        place_imports={},
        import_placements={},
        as_map={
            "from": {
                "mod1.a": ["alias_a"],
                "mod3.d": ["alias_d"],
            }
        },
        imports={
            "default": {
                "from": {
                    "mod1": {"a": True, "b": False},
                    "mod2": {"*": True, "c": True},
                    "mod3": {"d": True, "e": True},
                    "mod4": {"f": True},
                    "mod5": {"g": True},
                },
                "straight": set(),
            }
        },
        categorized_comments={
            "from": {
                "mod1": ["# mod1 comment"],
                "mod2": ["# mod2 comment"],
                "mod3": ["# mod3 comment"],
                "mod4": ["# mod4 comment"],
                "mod5": ["# mod5 comment"],
                "mod3.__combined_as__": ["# combined as comment"],
            },
            "above": {
                "from": {
                    "mod1": ["# above mod1"],
                }
            },
            "nested": {
                "mod1": {"a": "# nested a", "alias_a": "# nested alias_a"},
                "mod3": {"d": "# noqa: E501"},
            },
            "straight": {
                "mod1.a": ["# straight a"],
            },
        },
        change_count=0,
        original_line_count=0,
        line_separator="\n",
        sections=[],
        verbose_output=[],
        trailing_commas={"mod4"},
    )

    # Test case 1: remove_imports filtering and combine_as_imports with grid wrap & vertical grid check
    config = Config(
        line_length=10,
        combine_as_imports=True,
        combine_star=False,
        force_grid_wrap=2,
        multi_line_output=wrap.Modes.GRID,
        split_on_trailing_comma=False,
    )
    res1 = _with_from_imports(
        parsed=copy.deepcopy(parsed),
        config=config,
        from_modules=["mod1", "mod2", "mod3", "mod4", "mod5"],
        section="default",
        remove_imports=["mod1.b"],
        import_type="import",
    )
    assert isinstance(res1, list)

    # Test case 2: force_single_line, split_on_trailing_comma, ignore_comments, and specific multi_line_output modes
    config2 = Config(
        line_length=40,
        force_single_line=True,
        single_line_exclusions=[],
        split_on_trailing_comma=True,
        multi_line_output=wrap.Modes.VERTICAL,
    )
    res2 = _with_from_imports(
        parsed=copy.deepcopy(parsed),
        config=config2,
        from_modules=["mod4"],
        section="default",
        remove_imports=[],
        import_type="import",
    )
    assert isinstance(res2, list)

    # Test case 3: HANGING_INDENT with noqa comment and branch 518->525 explicitly targeted
    config3 = Config(
        line_length=5,
        multi_line_output=wrap.Modes.HANGING_INDENT,
    )
    parsed_hang = parse.ParsedContent(
        in_lines=[],
        lines_without_imports=[],
        import_index=0,
        place_imports={},
        import_placements={},
        as_map={"from": {}},
        imports={
            "default": {
                "from": {
                    "mod_hang": {"x": True, "y": True},
                },
                "straight": set(),
            }
        },
        categorized_comments={
            "from": {"mod_hang": []},
            "above": {"from": {}},
            "nested": {"mod_hang": {"x": "# noqa: E501"}},
            "straight": {},
        },
        change_count=0,
        original_line_count=0,
        line_separator="\n",
        sections=[],
        verbose_output=[],
        trailing_commas=set(),
    )
    res3 = _with_from_imports(
        parsed=parsed_hang,
        config=config3,
        from_modules=["mod_hang"],
        section="default",
        remove_imports=[],
        import_type="import",
    )
    assert isinstance(res3, list)
