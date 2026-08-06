## Python cmd run
python -m coverup --package-dir sample_repo\mlxtend\mlxtend --tests sample_repo\mlxtend\tests --target-symbol plot_decision_regions,bootstrap_point632_score,bias_variance_decomp,minmax_scaling,standardize,fpg_step,StackingClassifier.fit --repeat-tests 20 --max-attempts 5

# Use the focused baseline suite. The upstream isort integration suite clones
# mutable external repositories and is not a stable CoverUp baseline.
python -m coverup --package-dir sample_repo\isort\isort --tests coverup_targets\isort\tests --target-symbol process --repeat-tests 1 --max-attempts 1

python -m coverup --package-dir sample_repo\mlxtend\mlxtend --tests sample_repo\mlxtend\tests --target-symbol _BaseModel._get_param_names --repeat-tests 1 --max-attempts 2

python -m coverup --package-dir sample_repo\typesystem\typesystem --tests sample_repo\typesystem\tests --target-symbol tokenize_json --repeat-tests 1 --max-attempts 1

## Coverage 
coverage run --branch --source=sample_repo/isort -m pytest sample_repo/isort/tests
coverage json --pretty-print
