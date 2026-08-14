# file: src\sample_repo\mlxtend\mlxtend\classifier\ensemble_vote.py:206-239
# asked: {"lines": [206, 221, 222, 223, 226, 227, 230, 232, 233, 234, 235, 238, 239], "branches": [[221, 222], [221, 226], [226, 227], [226, 230]]}
# gained: {"lines": [206, 221, 222, 223, 226, 227, 230, 232, 233, 234, 235, 238, 239], "branches": [[221, 222], [221, 226], [226, 227], [226, 230]]}

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import NotFittedError
from mlxtend.classifier import EnsembleVoteClassifier


def test_ensemble_vote_classifier_not_fitted():
    clf = LogisticRegression(random_state=1)
    eclf = EnsembleVoteClassifier(clfs=[clf], voting='hard')
    X = np.array([[-1, -1], [1, 1]])

    with pytest.raises(NotFittedError, match="Estimator not fitted"):
        eclf.predict(X)


def test_ensemble_vote_classifier_predict_hard_and_soft():
    X = np.array([[-1, -1], [-2, -1], [1, 1], [2, 1]])
    y = np.array([0, 0, 1, 1])

    # Hard voting test (executes hard voting branches and inverse_transform)
    clf1 = LogisticRegression(random_state=1)
    clf2 = LogisticRegression(random_state=1)
    eclf_hard = EnsembleVoteClassifier(clfs=[clf1, clf2], voting='hard', weights=[1, 1])
    eclf_hard.fit(X, y)
    preds_hard = eclf_hard.predict(X)
    assert len(preds_hard) == len(X)
    assert set(preds_hard).issubset({0, 1})

    # Soft voting test (executes soft voting branch via predict_proba)
    eclf_soft = EnsembleVoteClassifier(clfs=[clf1, clf2], voting='soft', weights=[1, 1])
    eclf_soft.fit(X, y)
    preds_soft = eclf_soft.predict(X)
    assert len(preds_soft) == len(X)
    assert set(preds_soft).issubset({0, 1})
