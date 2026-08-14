# file: src\sample_repo\mlxtend\mlxtend\data\wine.py:17-56
# asked: {"lines": [17, 53, 54, 55, 56], "branches": []}
# gained: {"lines": [17, 53, 54, 55, 56], "branches": []}

import numpy as np
from mlxtend.data import wine_data

def test_wine_data():
    X, y = wine_data()
    
    # Check return types
    assert isinstance(X, np.ndarray)
    assert isinstance(y, np.ndarray)
    
    # Check shapes
    assert X.shape == (178, 13)
    assert y.shape == (178,)
    
    # Check target labels and their distribution
    assert set(np.unique(y)) == {0, 1, 2}
    
    counts = np.bincount(y)
    np.testing.assert_array_equal(counts, [59, 71, 48])
    
    # Check data types
    assert np.issubdtype(X.dtype, np.floating)
    assert np.issubdtype(y.dtype, np.integer)
