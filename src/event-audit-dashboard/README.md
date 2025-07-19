### Update requirements file.
```
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

### Addind dev dependencies
```
poetry add bandit --group dev
```

### Running bandit
```
poetry run bandit -r . -ll -f json -o bandit_results.json
```

