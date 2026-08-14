# file: src\sample_repo\mlxtend\mlxtend\frequent_patterns\apriori.py:134-341
# asked: {"lines": [134, 135, 208, 231, 232, 234, 235, 236, 238, 241, 243, 245, 246, 248, 249, 252, 253, 254, 255, 256, 257, 258, 259, 261, 263, 264, 270, 271, 272, 275, 276, 278, 279, 280, 281, 282, 283, 284, 287, 288, 289, 291, 292, 293, 295, 296, 297, 298, 299, 300, 301, 304, 305, 306, 307, 309, 311, 312, 313, 314, 315, 316, 319, 321, 322, 323, 324, 326, 327, 329, 330, 331, 332, 333, 334, 336, 338, 339, 341], "branches": [[234, 235], [234, 241], [243, 245], [243, 252], [245, 246], [245, 248], [263, 264], [263, 321], [270, 271], [270, 291], [278, 279], [278, 280], [280, 281], [280, 287], [295, 296], [295, 297], [297, 298], [297, 304], [304, 305], [304, 309], [306, 307], [306, 311], [313, 314], [313, 319], [322, 323], [322, 329], [331, 332], [331, 336], [338, 339], [338, 341]]}
# gained: {"lines": [134, 135, 208, 231, 232, 234, 235, 236, 238, 241, 243, 245, 246, 248, 249, 252, 253, 254, 255, 256, 257, 258, 259, 261, 263, 264, 270, 271, 272, 275, 276, 278, 280, 281, 282, 283, 284, 287, 288, 289, 291, 292, 293, 295, 296, 297, 298, 299, 300, 301, 304, 305, 306, 307, 309, 311, 312, 313, 314, 315, 316, 321, 322, 323, 324, 326, 327, 329, 330, 331, 332, 333, 334, 336, 338, 339, 341], "branches": [[234, 235], [234, 241], [243, 245], [243, 252], [245, 246], [245, 248], [263, 264], [263, 321], [270, 271], [270, 291], [278, 280], [280, 281], [295, 296], [295, 297], [297, 298], [297, 304], [304, 305], [304, 309], [306, 307], [306, 311], [313, 314], [322, 323], [322, 329], [331, 332], [331, 336], [338, 339], [338, 341]]}

import pytest
import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori


def test_apriori_basic():
    df = pd.DataFrame({
        'Apple': [True, True, True, False, False],
        'Bananas': [False, False, True, True, False],
        'Beer': [True, True, False, False, True]
    })
    res = apriori(df, min_support=0.4, use_colnames=True, verbose=1)
    assert not res.empty
    assert 'itemsets' in res.columns
    assert 'support' in res.columns


def test_apriori_max_len_and_low_memory():
    df = pd.DataFrame({
        0: [1, 1, 1, 0, 1],
        1: [1, 0, 1, 1, 1],
        2: [1, 1, 1, 1, 1]
    })
    res = apriori(df, min_support=0.4, max_len=2, low_memory=True, verbose=2)
    assert not res.empty
    # Ensure max length condition is respected
    max_observed_len = res['itemsets'].apply(len).max()
    assert max_observed_len <= 2


def test_apriori_sparse():
    # Construct a sparse DataFrame (pandas >= 1.0 / modern pandas sparse support)
    df = pd.DataFrame({
        'A': [1, 0, 1, 1],
        'B': [1, 1, 0, 1]
    }).astype(pd.SparseDtype(int, 0))
    res = apriori(df, min_support=0.5, use_colnames=True, low_memory=False)
    assert not res.empty


def test_apriori_empty_sparse():
    df = pd.DataFrame(columns=['A', 'B']).astype(pd.SparseDtype(int, 0))
    res = apriori(df, min_support=0.5)
    assert res.empty


def test_apriori_invalid_min_support():
    df = pd.DataFrame({
        'A': [True, False]
    })
    with pytest.raises(ValueError, match="`min_support` must be a positive"):
        apriori(df, min_support=0.0)


def test_apriori_no_frequent_itemsets():
    df = pd.DataFrame({
        'A': [True, False, False, False],
        'B': [False, True, False, False]
    })
    res = apriori(df, min_support=0.9)
    # Should only return items that meet support >= 0.9, but none do except maybe empty if handled.
    # Actually support for A is 0.25, so no 1-itemsets or higher will meet min_support=0.9.
    # Wait, support_dict[1] will be empty, max_itemset loop won't execute further.
    assert res.empty
