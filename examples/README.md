# Examples

## Run the demo session

```bash
live-decision run ../demo/session_001
```

## Build a new session from a VTT transcript

```bash
python ../scripts/build_demo_data.py --source-vtt /path/to/live.vtt --out ../demo/session_002 --max-minutes 30
```

## Validate input before running

```bash
live-decision validate ../demo/session_001
```
