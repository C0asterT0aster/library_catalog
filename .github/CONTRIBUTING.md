# Contributing to Library Catalog

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Code of Conduct

We are committed to providing a welcoming and inspiring community for all. Please be respectful and constructive.

## How to Contribute

### Reporting Issues

If you encounter a bug or have a feature request:

1. Check [existing issues](https://github.com/C0asterT0aster/library_catalog/issues) first
2. Provide detailed description of the problem or feature
3. Include:
   - Home Assistant version
   - Python version
   - Steps to reproduce (for bugs)
   - Expected vs. actual behavior
   - Relevant error logs

### Development Setup

1. Fork and clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/library_catalog.git
cd library_catalog
```

2. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```

3. Install development dependencies:
```bash
pip install -r requirements.txt
pip install flake8 pytest pytest-asyncio
```

4. Make your changes following the code style guide (see below)

5. Test your changes:
```bash
python -m flake8 custom_components/library_catalog
python -m pytest tests/
```

### Code Style

This project follows these conventions:

- **Python**: PEP 8 with flake8 validation
- **Type Hints**: Complete type hints required on all functions
- **Docstrings**: Google-style docstrings for all public functions and classes
- **Async**: Use async/await throughout, no sync blocking calls
- **Comments**: Add comments for complex logic, not obvious code

Example:
```python
async def async_search_books(self, query: str, limit: int = 50) -> List[BookEntity]:
    """Search for books in the library.
    
    Args:
        query: Search term (title, author, or ISBN)
        limit: Maximum number of results
        
    Returns:
        List of matching BookEntity objects
        
    Raises:
        RuntimeError: If database not initialized
    """
    # Implementation here
    pass
```

### Commit Message Guidelines

Write clear, descriptive commit messages:

```
Short summary (50 chars or less)

Detailed explanation if needed. Wrap at 72 characters.
Explain what the commit does and why.

- Bullet points are fine
- Keep it organized
```

### Pull Request Process

1. Update README.md with any new features or changes
2. Update DEVELOPMENT.md if adding architectural changes
3. Ensure all tests pass and code is linted
4. Submit PR with detailed description
5. Respond to review feedback promptly
6. Once approved, maintainer will merge

## Development Phases

The project is organized into logical commits/phases:

- **Phase 1**: Infrastructure (Constants, Database, API)
- **Phase 2**: Home Assistant Integration (Config, Coordinator, Services)
- **Phase 3**: User Interaction (Webhook, Diagnostics)
- **Phase 4**: Data & Frontend (Entities, Dashboard)
- **Phase 5**: Polish (Localization, Documentation)
- **Phase 6**: Quality (Tests, Validation)

When contributing, indicate which phase your changes relate to.

## Feature Requests

Feature requests should include:

1. **Use Case**: Why you need this feature
2. **Expected Behavior**: How it should work
3. **Alternatives**: Any workarounds you've tried
4. **Compatibility**: Any version requirements

## Questions?

Feel free to open an issue with the `question` label or reach out via:
- GitHub Discussions
- Home Assistant Community Forums

## Recognition

Contributors will be acknowledged in:
- README.md contributors section
- Release notes

Thank you for making Library Catalog better! 🎉
