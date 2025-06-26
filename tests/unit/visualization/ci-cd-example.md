# CI/CD Configuration for Visualization Tests

## GitHub Actions

### Option 1: Separate API tests (Recommended)
```yaml
- name: Run visualization tests (except API)
  run: |
    python -m pytest tests/unit/visualization/ -k "not test_ui_server_api" -v

- name: Run API tests separately
  run: |
    python -m pytest tests/unit/visualization/test_ui_server_api.py -v
```

### Option 2: Use the shell script
```yaml
- name: Run visualization tests with script
  run: |
    chmod +x tests/unit/visualization/run_tests.sh
    ./tests/unit/visualization/run_tests.sh
```

## GitLab CI

```yaml
test-visualization:
  stage: test
  script:
    # Option 1: Separate API tests
    - python -m pytest tests/unit/visualization/ -k "not test_ui_server_api" -v
    - python -m pytest tests/unit/visualization/test_ui_server_api.py -v
    
    # Option 2: Use script
    # - chmod +x tests/unit/visualization/run_tests.sh
    # - ./tests/unit/visualization/run_tests.sh
```

## Jenkins (Jenkinsfile)

```groovy
stage('Visualization Tests') {
    steps {
        script {
            // Option 1: Separate API tests
            sh 'python -m pytest tests/unit/visualization/ -k "not test_ui_server_api" -v'
            sh 'python -m pytest tests/unit/visualization/test_ui_server_api.py -v'
            
            // Option 2: Use script
            // sh 'chmod +x tests/unit/visualization/run_tests.sh'
            // sh './tests/unit/visualization/run_tests.sh'
        }
    }
}
```

## CircleCI

```yaml
- run:
    name: Run visualization tests
    command: |
      # Option 1: Separate API tests
      python -m pytest tests/unit/visualization/ -k "not test_ui_server_api" -v
      python -m pytest tests/unit/visualization/test_ui_server_api.py -v
      
      # Option 2: Use script
      # chmod +x tests/unit/visualization/run_tests.sh
      # ./tests/unit/visualization/run_tests.sh
```

## Azure DevOps

```yaml
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.x'
    
- script: |
    # Option 1: Separate API tests
    python -m pytest tests/unit/visualization/ -k "not test_ui_server_api" -v
    python -m pytest tests/unit/visualization/test_ui_server_api.py -v
  displayName: 'Run visualization tests'
```

## Integration with Main Test Suite

If you want to include visualization tests with your main test suite:

```yaml
# Run all tests except visualization
- name: Run main tests
  run: |
    python -m pytest tests/ --ignore=tests/unit/visualization/ -v

# Run visualization tests separately
- name: Run visualization tests
  run: |
    python -m pytest tests/unit/visualization/ -k "not test_ui_server_api" -v
    python -m pytest tests/unit/visualization/test_ui_server_api.py -v
```

## Notes

1. **Option 1 (Separate API tests)** is recommended because:
   - It's explicit about what's happening
   - It provides better error messages
   - It's easier to debug in CI logs
   - It works with standard pytest commands

2. **Shell script approach** works but:
   - Requires bash (may not work on Windows runners)
   - Harder to debug in CI
   - Exit codes might not propagate correctly

3. **Performance**: Running tests separately adds minimal overhead (~1-2 seconds per invocation)

4. **Test coverage**: All approaches run the same 72 tests