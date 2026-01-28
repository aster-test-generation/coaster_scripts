# Set up

Use poetry to set up Python environment with `pyproject.toml`

Create `.env` and set API keys in it. Currently version uses OpenRouter.

# Run

<!-- ```python
python pattern_statistics.py combined.json
```

Git repos will be cloned into `temp` folder. After processing the project, the cloned folder will be removed.

Pattern statistics will be written into `stats` folder. -->

```python
python pattern_analysis.py <project folder path> >> <output json path>
```