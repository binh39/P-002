# file: src\sample_repo\mlxtend\mlxtend\frequent_patterns\apriori.py:55-131
# asked: {"lines": [55, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 125, 126, 127, 128, 129, 130, 131], "branches": [[115, 0], [115, 116], [120, 121], [120, 125], [128, 115], [128, 129]]}
# gained: {"lines": [55, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 125, 126, 127, 128, 129, 130, 131], "branches": [[115, 0], [115, 116], [120, 121], [120, 125], [128, 115], [128, 129]]}

import numpy as np
import scipy.sparse as sp
from mlxtend.frequent_patterns.apriori import generate_new_combinations_low_memory


def test_generate_new_combinations_low_memory_dense():
    # Dense matrix test
    # Transactions:
    # 0: item 0, item 1
    # 1: item 0, item 1, item 2
    # 2: item 0, item 2
    # 3: item 1, item 2
    X = np.array([
        [True, True, False],
        [True, True, True],
        [True, False, True],
        [False, True, True]
    ])
    
    # old_combinations: size 1, containing items [0], [1], [2]
    old_combinations = np.array([[0], [1], [2]])
    
    # min_support = 0.5 -> threshold = 0.5 * 4 = 2.0
    # For combination [0]: valid items > 0 are [1, 2].
    #   - [0, 1] occurs in rows 0, 1 -> support = 2 >= 2. (Valid)
    #   - [0, 2] occurs in rows 1, 2 -> support = 2 >= 2. (Valid)
    # For combination [1]: valid items > 1 are [2].
    #   - [1, 2] occurs in rows 1, 3 -> support = 2 >= 2. (Valid)
    # For combination [2]: valid items > 2 are none.
    
    gen = generate_new_combinations_low_memory(old_combinations, X, min_support=0.5, is_sparse=False)
    results = list(gen)
    
    # Expected outputs:
    # support, old_tuple..., valid_item
    # [0, 1] -> support 2, 0, 1
    # [0, 2] -> support 2, 0, 2
    # [1, 2] -> support 2, 1, 2
    assert len(results) > 0
    assert 2 in results


def test_generate_new_combinations_low_memory_sparse():
    # Sparse matrix test (CSC or CSR format)
    X_dense = np.array([
        [True, True, False],
        [True, True, True],
        [True, False, True],
        [False, True, True]
    ])
    X = sp.csr_matrix(X_dense)
    
    old_combinations = np.array([[0], [1]])
    
    gen = generate_new_combinations_low_memory(old_combinations, X, min_support=0.5, is_sparse=True)
    results = list(gen)
    
    assert len(results) > 0
    # Check that combination [0, 1] with support 2 is generated
    # Supports format: support, old_item, new_item
    found = False
    for i in range(0, len(results), 3):
        if results[i+1] == 0 and results[i+2] == 1:
            assert results[i] == 2
            found = True
    assert found
