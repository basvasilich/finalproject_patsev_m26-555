import json
import os
import tempfile
from pathlib import Path

from valutatrade_hub.core.exceptions import StorageError


class JsonRepository:
    """Чтение JSON и атомарная замена файла."""

    def __init__(self, path, default_factory=list):
        self.path = Path(path)
        self.default_factory = default_factory

    def load(self):
        """Прочитать файл; отсутствующий или пустой считать новым."""
        try:
            if not self.path.exists() or self.path.stat().st_size == 0:
                return self.default_factory()
            with self.path.open(encoding="utf-8") as stream:
                data = json.load(stream)
            if not isinstance(data, type(self.default_factory())):
                raise ValueError("неверный формат")
            return data
        except (OSError, ValueError) as error:
            raise StorageError(f"Не удалось прочитать {self.path.name}") from error

    def save(self, data):
        """Записать JSON через временный файл в том же каталоге."""
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent, delete=False
            ) as stream:
                temporary = Path(stream.name)
                json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except (OSError, ValueError, TypeError) as error:
            raise StorageError(f"Не удалось сохранить {self.path.name}") from error
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
