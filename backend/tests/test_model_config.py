import os
import unittest
from unittest.mock import patch

from app.config import Settings


class ModelConfigTests(unittest.TestCase):
    def test_spark_model_is_default_and_legacy_alias_is_ignored(self):
        with patch.dict(
            os.environ,
            {"MUSE_WONDER_MODEL_NAME": "muse-wonder-1.0"},
            clear=True,
        ):
            settings = Settings(_env_file=None)

        self.assertEqual(settings.model_name, "muse-spark-1.3-contributor")


if __name__ == "__main__":
    unittest.main()
