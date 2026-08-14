# file: src\sample_repo\mlxtend\mlxtend\frequent_patterns\apriori.py:134-341
# asked: {"lines": [134, 135, 208, 231, 232, 234, 235, 236, 238, 241, 243, 245, 246, 248, 249, 252, 253, 254, 255, 256, 257, 258, 259, 261, 263, 264, 270, 271, 272, 275, 276, 278, 279, 280, 281, 282, 283, 284, 287, 288, 289, 291, 292, 293, 295, 296, 297, 298, 299, 300, 301, 304, 305, 306, 307, 309, 311, 312, 313, 314, 315, 316, 319, 321, 322, 323, 324, 326, 327, 329, 330, 331, 332, 333, 334, 336, 338, 339, 341], "branches": [[234, 235], [234, 241], [243, 245], [243, 252], [245, 246], [245, 248], [263, 264], [263, 321], [270, 271], [270, 291], [278, 279], [278, 280], [280, 281], [280, 287], [295, 296], [295, 297], [297, 298], [297, 304], [304, 305], [304, 309], [306, 307], [306, 311], [313, 314], [313, 319], [322, 323], [322, 329], [331, 332], [331, 336], [338, 339], [338, 341]]}
# gained: {"lines": [134, 135, 208, 231, 232, 234, 235, 236, 238, 241, 243, 245, 246, 248, 249, 252, 253, 254, 255, 256, 257, 258, 259, 261, 263, 264, 270, 271, 272, 275, 276, 278, 279, 280, 281, 282, 283, 284, 287, 288, 289, 291, 292, 293, 295, 296, 297, 298, 299, 300, 301, 304, 305, 306, 307, 309, 311, 312, 313, 314, 315, 316, 319, 321, 322, 323, 324, 326, 327, 329, 330, 331, 332, 333, 334, 336, 338, 339, 341], "branches": [[234, 235], [234, 241], [243, 245], [243, 252], [245, 246], [245, 248], [263, 264], [263, 321], [270, 271], [270, 291], [278, 279], [278, 280], [280, 281], [295, 296], [295, 297], [297, 298], [297, 304], [304, 305], [304, 309], [306, 307], [306, 311], [313, 314], [313, 319], [322, 323], [322, 329], [331, 332], [331, 336], [338, 339], [338, 341]]}

import pytest
import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori


def test_apriori_basic():
    df = pd.DataFrame({
        'Apple': [True, True, True, False, False],
        'Bananas': [False, True, True, False, False],
        'Beer': [True, True, False, True, True],
    })
    res = apriori(df, min_support=0.4, use_colnames=True)
    assert not res.empty
    assert 'itemsets' in res.columns
    assert 'support' in res.columns


def test_apriori_max_len_and_verbose():
    df = pd.DataFrame({
        0: [1, 1, 1, 0, 0],
        1: [0, 1, 1, 1, 0],
        2: [1, 1, 0, 1, 1],
    })
    res = apriori(df, min_support=0.2, max_len=2, verbose=1)
    assert not res.empty
    assert all(len(itemset) <= 2 for itemset in res['itemsets'])


def test_apriori_low_memory():
    df = pd.DataFrame({
        0: [True, True, False, True, True],
        1: [True, True, True, False, True],
        2: [False, True, True, True, True],
    })
    res = apriori(df, min_support=0.4, low_memory=True, verbose=1)
    assert not res.empty


def test_apriori_sparse_dataframe():
    df = pd.DataFrame({
        0: [True, False, True, True],
        1: [True, True, False, True],
    }, dtype=pd.SparseDtype(bool, False))
    res = apriori(df, min_support=0.5)
    assert not res.empty


def test_apriori_empty_sparse_dataframe():
    df_sparse_empty = pd.DataFrame(columns=[0, 1], dtype=bool).astype(pd.SparseDtype(bool, False)).iloc[0:0]
    if hasattr(df_sparse_empty, "sparse"):
        res = apriori(df_sparse_empty, min_support=0.5)
        assert res.empty


def test_apriori_no_frequent_combinations():
    df = pd.DataFrame({
        0: [True, False, False],
        1: [False, True, False],
    })
    res = apriori(df, min_support=0.9)
    assert res.empty


def test_apriori_invalid_min_support():
    df = pd.DataFrame({0: [True, False]})
    with pytest.raises(ValueError, match="`min_support` must be a positive"):
        apriori(df, min_support=0.0)
