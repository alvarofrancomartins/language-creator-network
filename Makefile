.PHONY: data graph stats

# Fetch the upstream PLDB data (required before graph/stats).
data:
	@test -d pldb || git clone --depth 1 https://github.com/breck7/pldb.git pldb

graph: data
	python3 build_corrected_graph.py

stats: data
	python3 network_stats.py
