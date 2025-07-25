# Marcus CLI Migration Notes

## Old vs New Commands

### Previous (Deprecated)
```bash
python run_marcus.py --http
python setup_marcus_demo.py
```

### New (Recommended)
```bash
marcus start --http
marcus status
marcus logs
marcus stop
```

## Migrated Files

The following files have been moved to `.old` extensions and are no longer used:

- `run_marcus.py` → `run_marcus.py.old`

## Installation

Run the installation script to set up the new CLI:

```bash
./install.sh
```

This installs the `marcus` command to your PATH.

## Benefits of New CLI

1. **Standard Commands**: Follows Unix conventions (`start`, `stop`, `status`)
2. **Process Management**: Proper daemon mode with PID tracking
3. **Better Logging**: Structured log files with timestamps
4. **Status Monitoring**: CPU, memory, uptime information
5. **Configuration Management**: Built-in config viewing and editing

## Backward Compatibility

The old scripts are preserved as `.old` files in case you need them for reference or emergency use.
