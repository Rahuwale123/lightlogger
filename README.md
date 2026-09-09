# lightlogger

Live web dashboard for your Python logs — pip install, add one line, open localhost:4356. Zero dependencies.

> Full README (badges, demo GIF, features, "why lightlogger") lands in Phase 7 once the product is built. This is a placeholder so packaging metadata (`readme = "README.md"`) has a valid target during early development.

## Quickstart (target API — not yet functional, see CLAUDE.md build phases)

```bash
pip install lightlogger
```

```python
import lightlogger
lightlogger.start()
lightlogger.info("user logged in")
```
