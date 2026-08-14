# file: src\sample_repo\mlxtend\mlxtend\frequent_patterns\apriori.py:55-131
# asked: {"lines": [55, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 125, 126, 127, 128, 129, 130, 131], "branches": [[115, 0], [115, 116], [120, 121], [120, 125], [128, 115], [128, 129]]}
# gained: {"lines": [55, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 125, 126, 127, 128, 129, 130, 131], "branches": [[115, 0], [115, 116], [120, 121], [120, 125], [128, 115], [128, 129]]}

import numpy as np
import scipy.sparse as sp
from mlxtend.frequent_patterns.apriori import generate_new_combinations_low_memory

def test_generate_new_combinations_low_memory_dense():
    # Dense matrix X
    # Transactions: 4, Items: 4 (indices 0, 1, 2, 3)
    X = np.array([
        [True, True, True, False],
        [True, True, False, False],
        [True, False, True, False],
        [False, False, False, True]
    ])
    
    # old_combinations containing itemsets of size 1, e.g., [[0], [1]]
    old_combinations = np.array([[0], [1]])
    
    # min_support = 0.5 -> threshold = 2 * 4 = 2
    # For old_combination [0]:
    # valid_items (items > 0) are [1, 2, 3]
    # rows where column 0 is True: rows 0, 1, 2
    # subset of X[rows, valid_items]:
    # row 0: [True, True, False]
    # row 1: [True, False, False]
    # row 2: [False, True, False]
    # sum along columns: item 1 -> 2, item 2 -> 1, item 3 -> 0
    # supports >= 2: item 1 (support = 2)
    # Yields: support (2), old_tuple (0,), valid_item (1) -> [2, 0, 1]
    
    res = list(generate_new_combinations_low_memory(old_combinations, X, min_support=0.5, is_sparse=False))
    assert len(res) > 0
    # Check output format: support followed by old_combination elements followed by new item
    assert res[0] == 2
    assert res[1] == 0
    assert res[2] == 1

def test_generate_new_combinations_low_memory_sparse():
    # Sparse matrix X
    X_dense = np.array([
        [True, True, True, False],
        [True, True, False, False],
        [True, False, True, False],
        [False, False, False, True]
    ])
    X = sp.csr_matrix(X_dense)
    
    old_combinations = np.array([[0], [1]])
    
    res = list(generate_new_combinations_low_memory(old_combinations, X, min_support=0.5, is_sparse=True))
    assert len(res) > 0
    assert res[0] == 2
    assert res[1] == 0
    assert res[2] == 1
