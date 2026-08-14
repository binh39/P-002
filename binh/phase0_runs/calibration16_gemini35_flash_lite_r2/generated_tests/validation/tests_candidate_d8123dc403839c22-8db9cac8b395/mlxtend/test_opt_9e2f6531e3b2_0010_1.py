# file: src\sample_repo\mlxtend\mlxtend\classifier\ensemble_vote.py:206-239
# asked: {"lines": [206, 221, 222, 223, 226, 227, 230, 232, 233, 234, 235, 238, 239], "branches": [[221, 222], [221, 226], [226, 227], [226, 230]]}
# gained: {"lines": [206, 221, 222, 223, 226, 227, 230, 232, 233, 234, 235, 238, 239], "branches": [[221, 222], [221, 226], [226, 227], [226, 230]]}

import numpy as np
import pytest
from sklearn.exceptions import NotFittedError
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import load_iris
from mlxtend.classifier import EnsembleVoteClassifier


def test_ensemble_vote_classifier_predict_not_fitted():
    iris = load_iris()
    X, y = iris.data, iris.target
    clf1 = LogisticRegression(random_state=1, max_iter=200)
    eclf = EnsembleVoteClassifier(clfs=[clf1], voting='hard')
    
    with pytest.raises(NotFittedError, match="Estimator not fitted"):
        eclf.predict(X)


def test_ensemble_vote_classifier_predict_hard_and_soft_voting():
    iris = load_iris()
    X, y = iris.data, iris.target

    # Hard voting with weights
    clf1 = LogisticRegression(random_state=1, max_iter=200)
    clf2 = LogisticRegression(random_state=2, max_iter=200)
    eclf_hard = EnsembleVoteClassifier(clfs=[clf1, clf2], voting='hard', weights=[1, 1])
    eclf_hard.fit(X, y)
    preds_hard = eclf_hard.predict(X)
    assert len(preds_hard) == len(y)
    assert set(preds_hard).issubset(set(y))

    # Soft voting
    eclf_soft = EnsembleVoteClassifier(clfs=[clf1, clf2], voting='soft')
    eclf_soft.fit(X, y)
    preds_soft = eclf_soft.predict(X)
    assert len(preds_soft) == len(y)
    assert set(preds_soft).issubset(set(y))
