## Python cmd run
python -m coverup --package-dir sample_repo\mlxtend\mlxtend --tests sample_repo\mlxtend\tests --target-symbol plot_decision_regions,bootstrap_point632_score,bias_variance_decomp,minmax_scaling,standardize,fpg_step,StackingClassifier.fit --repeat-tests 20 --max-attempts 5

python -m coverup --package-dir sample_repo\isort\isort --tests sample_repo\isort\tests --target-symbol process --repeat-tests 20 --max-attempts 5

## Coverage 
coverage run --branch --source=sample_repo/isort -m pytest sample_repo/isort/tests
coverage json --pretty-print