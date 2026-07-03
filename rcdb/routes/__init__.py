"""Blueprint registration."""
from . import (
    auth, categories, data, health, items, manuals, media, notes, pages,
    specs, tasks,
)

_MODULES = (pages, auth, health, items, categories, notes, tasks, specs,
            media, manuals, data)


def register_blueprints(app) -> None:
    for mod in _MODULES:
        app.register_blueprint(mod.bp)
