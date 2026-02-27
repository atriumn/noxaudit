# Scheduling

Noxaudit uses a day-of-week schedule to rotate through focus areas. This ensures systematic coverage without overwhelming you with findings.

## Default Schedule

When no schedule is configured, noxaudit uses:

```yaml
schedule:
  monday: security
  tuesday: patterns
  wednesday: docs
  thursday: hygiene
  friday: performance
  saturday: dependencies
  sunday: off
```

Each day runs one focus area. Run `noxaudit schedule` to see the current schedule.

## Customizing the Schedule

### Single Focus Areas

Assign one focus area per day:

```yaml
schedule:
  monday: security
  tuesday: patterns
  wednesday: docs
  thursday: hygiene
  friday: performance
  saturday: off
  sunday: off
```

### Grouped Focus Areas

Run multiple focus areas in a single API call. Files are gathered and deduplicated across all areas, saving ~80% on input tokens:

```yaml
schedule:
  monday: [security, dependencies]
  wednesday: [patterns, hygiene, docs]
  friday: [performance, testing]
  saturday: off
  sunday: off
```

### Using Frames

Frames are named groups of related focus areas:

| Frame | Expands To |
|-------|-----------|
| `does_it_work` | security, testing |
| `does_it_last` | patterns, hygiene, docs, dependencies |
| `can_we_prove_it` | performance |

```yaml
schedule:
  monday: does_it_work        # → security + testing
  tuesday: does_it_last       # → patterns + hygiene + docs + dependencies
  wednesday: does_it_work
  thursday: does_it_last
  friday: can_we_prove_it     # → performance
  saturday: off
  sunday: off
```

### Frame Overrides

Disable specific focus areas within a frame:

```yaml
schedule:
  tuesday: does_it_last

frames:
  does_it_last:
    patterns: true
    hygiene: true
    docs: true
    dependencies: false     # skip dependency audits on this frame
```

### Run Everything

```yaml
schedule:
  monday: all               # all 7 focus areas in one call
```

Or from the CLI:

```bash
noxaudit run --focus all
```

## Viewing the Schedule

```bash
noxaudit schedule
```

```
Weekly Schedule:

  ▶ Monday       Does it work? (security, testing)
  ▶ Tuesday      Does it last? (patterns, hygiene, docs, dependencies)
  ▶ Wednesday    Does it work? (security, testing)
  ▶ Thursday     Does it last? (patterns, hygiene, docs, dependencies)
  ▶ Friday       Can we prove it? (performance) ← today
    Saturday     off
    Sunday       off
```

## Overriding the Schedule

You can always override the schedule on the command line:

```bash
# Run security regardless of what day it is
noxaudit run --focus security

# Run multiple areas
noxaudit run --focus security,performance

# Run everything
noxaudit run --focus all
```

## Token Savings with Combined Runs

When multiple focus areas run in a single call, source files are sent once instead of repeated per area. This typically saves 80% on input tokens:

| Strategy | API Calls | Token Multiplier |
|----------|-----------|-----------------|
| One area per day | 6/week | 1x per area |
| Grouped (2-3 areas) | 3/week | ~1x total (files deduped) |
| All at once | 1/week | ~1x total |

The trade-off: combined runs produce more findings per notification, which can be harder to triage. Many teams find 2-3 areas per call to be the sweet spot.

## Automation

### Cron

```bash
# Run the scheduled focus area(s) for today at 6 AM
0 6 * * * cd /path/to/project && noxaudit run
```

### GitHub Actions

See [GitHub Actions](../integrations/github-actions.md) for the full workflow.

```yaml
on:
  schedule:
    - cron: '0 6 * * *'  # 6am UTC daily
```
