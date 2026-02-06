import tomllib
from pathlib import Path
from typing import Any


class Config:
    """Configuration class for Paladin application with validation."""

    REQUIRED_STRUCTURE = {
        "paths": {"semgrep_rules_dir": str, "clone_base_dir": str},
        "deployment": {"host": str, "port": int, "workers": int},
    }

    def __init__(self, config_path: str | Path = "config.toml"):
        """
        Initialize Config by loading and validating a TOML file.

        Args:
            config_path: Path to the config.toml file

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If required sections or keys are missing
            TypeError: If values are of wrong type
        """
        self.config_path = Path(config_path)
        self._config: dict[str, Any] = self._load_config()
        self._verify_structure()
        self._initialize_attributes()

    def _load_config(self) -> dict[str, Any]:
        """Load and parse the TOML configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"TOML file not found: {self.config_path}")

        with open(self.config_path, "rb") as f:
            return tomllib.load(f)

    def _verify_section(self, section_name: str, schema: dict) -> None:
        """Verify a section has required keys and correct types."""
        if section_name not in self._config:
            raise ValueError(f"Missing required section: [{section_name}]")

        section = self._config[section_name]
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

    def _verify_structure(self) -> None:
        """Verify all required sections and keys exist with correct types."""
        for section, schema in self.REQUIRED_STRUCTURE.items():
            self._verify_section(section, schema)

    def _initialize_attributes(self) -> None:
        """Initialize all configuration attributes from loaded data."""
        # Paths section (required)
        paths = self._config["paths"]
        self.semgrep_rules_dir: Path = Path(paths["semgrep_rules_dir"])
        self.clone_base_dir: Path = Path(paths["clone_base_dir"])
        self.sarif_write_dir: Path = Path(paths["sarif_write_dir"])

        # Settings section (optional)
        settings = self._config.get("settings", {})
        self.write_sarif_to_file: bool = settings.get("write_sarif_to_file", False)
        self.exclude_langs: list[str] = settings.get("exclude_langs", [])
        self.suppress_paths: list[str] = settings.get("suppress_paths", [])
        self.suppress_rules: list[str] = settings.get("suppress_rules", [])
        self.gemini_model: str = settings.get("gemini_model", "")

        # Tokens section (optional)
        tokens = self._config.get("tokens", {})
        self.github_token: str = tokens.get("github_token", "")
        self.gemini_api_key: str = tokens.get("gemini_api_key", "")

        # MongoDB section (optional, with defaults)
        mongo = self._config.get("mongo", {})
        self.mongo_host: str = mongo.get("host", "localhost")
        self.mongo_port: int = mongo.get("port", 27017)

        # Deployment section (required)
        deployment = self._config["deployment"]
        self.host: str = deployment["host"]
        self.port: int = deployment["port"]
        self.workers: int = deployment["workers"]
