.PHONY: clean

clean:
	@echo "Cleaning up Python cache and test artifacts..."
	# Remove __pycache__ directories
	find . -type d -name "__pycache__" -exec rm -rf {} +
	# Remove .pytest_cache directories
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	# Remove specific files
	find . -type f -name "bandit_results.json" -exec rm -rf {} +
	find . -type f -name "coverage.xml" -exec rm -rf {} +
	find . -type f -name ".coverage" -exec rm -rf {} +
	@echo "Cleanup complete."