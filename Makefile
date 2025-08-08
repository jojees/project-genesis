.PHONY: clean

clean:
	@echo "Cleaning up Python cache and test artifacts..."
	@echo "  Removing __pycache__ directories..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +

	@echo "  Removing .pytest_cache directories..."
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +

	@echo "  Removing specific Python test artifacts..."
	@find . -type f -name "bandit_results.json" -exec rm -rf {} +
	@find . -type f -name "coverage.xml" -exec rm -rf {} +
	@find . -type f -name ".coverage" -exec rm -rf {} +

	@echo "Cleaning up Helm chart packages..."
	@find k8s/charts -type f -name "*.tgz" -delete

	@echo "Cleanup complete."