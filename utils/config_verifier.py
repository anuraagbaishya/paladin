import tomllib
from pathlib import Path


class ConfigVerifier:
    REQUIRED_STRUCTURE = {
        "paths": {"semgrep_rules_dir": str, "clone_base_dir": str},
        "mongo": {"mongo_path": str},
        "deployment": {"host": str, "port": int},
    }

    def __init__(self, toml_path: str):
        self.toml_path = Path(toml_path)
        self.data = {}

    def load(self):
        if not self.toml_path.exists():
            raise FileNotFoundError(f"TOML file not found: {self.toml_path}")
        with open(self.toml_path, "rb") as f:
            self.data = tomllib.load(f)

    def verify_section(self, section_name: str, schema: dict):
        if section_name not in self.data:
            raise ValueError(f"Missing required section: [{section_name}]")
        section = self.data[section_name]
        if not isinstance(section, dict):
            raise TypeError(f"Section [{section_name}] must be a table")
        for key, expected_type in schema.items():
            if key not in section:
                raise ValueError(
                    f"Missing required key '{key}' in section [{section_name}]"
                )
            if not isinstance(section[key], expected_type):
                raise TypeError(
                    f"Key '{key}' in section [{section_name}] must be of type {expected_type.__name__}"
                )

    def verify(self):
        self.load()
        try:
            for section, schema in self.REQUIRED_STRUCTURE.items():
                self.verify_section(section, schema)
            return self.data

        except ValueError as e:
            print(f"config.toml is not valid, {e}")
            return None
