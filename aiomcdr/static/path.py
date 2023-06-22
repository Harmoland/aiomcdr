from pathlib import Path

root_path: Path = Path.cwd()
logs_path: Path = Path(root_path, "logs")
plugin_path: Path = Path(root_path, "plugins")
config_path: Path = Path(root_path, "config")

logs_path.mkdir(parents=True, exist_ok=True)
plugin_path.mkdir(parents=True, exist_ok=True)
config_path.mkdir(parents=True, exist_ok=True)
