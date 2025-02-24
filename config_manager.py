import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime
import shutil
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self, base_path: str = None):
        self.base_path = base_path or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.env_files = {
            'dev': '.env.dev',
            'prod': '.env.prod',
            'test': '.env.test',
            'default': '.env'
        }

    def validate_paths(self) -> Dict[str, bool]:
        """Validate all paths specified in configuration files"""
        results = {}
        for env, file in self.env_files.items():
            env_path = os.path.join(self.base_path, file)
            if not os.path.exists(env_path):
                logger.warning(f"Environment file {file} not found")
                continue

            with open(env_path, 'r') as f:
                config = f.readlines()

            paths = [
                line.split('=')[1].strip().strip('"\'')
                for line in config
                if any(key in line for key in ['_DIR', '_FILE', 'DATABASE_URL'])
                   and '=' in line
            ]

            valid_paths = []
            invalid_paths = []
            for path in paths:
                if path.startswith(('http://', 'https://', 'sqlite:///')):
                    valid_paths.append(path)
                else:
                    path_obj = Path(path)
                    if path_obj.exists():
                        valid_paths.append(str(path_obj))
                    else:
                        invalid_paths.append(str(path_obj))

            results[env] = {
                'valid': valid_paths,
                'invalid': invalid_paths
            }

        return results

    def create_required_directories(self) -> None:
        """Create required directories from configuration"""
        dirs_to_create = [
            'uploads', 'uploads_dev', 'uploads_prod', 'uploads_test',
            'templates', 'templates_dev', 'templates_prod', 'templates_test',
            'backups', 'test_reports', 'ssl'
        ]

        for dir_name in dirs_to_create:
            dir_path = os.path.join(self.base_path, dir_name)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                logger.info(f"Created directory: {dir_path}")

    def backup_config(self) -> str:
        """Backup all configuration files"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(self.base_path, 'backups', f'config_backup_{timestamp}')

        os.makedirs(backup_dir, exist_ok=True)

        for env_file in self.env_files.values():
            src = os.path.join(self.base_path, env_file)
            if os.path.exists(src):
                dst = os.path.join(backup_dir, env_file)
                shutil.copy2(src, dst)
                logger.info(f"Backed up {env_file}")

        return backup_dir

    def validate_config_values(self) -> Dict[str, List[str]]:
        """Validate configuration values"""
        issues = {env: [] for env in self.env_files.keys()}

        required_fields = {
            'DATABASE_URL': str,
            'SECRET_KEY': str,
            'API_V1_STR': str,
            'PORT': int,
            'HOST': str
        }

        for env, file in self.env_files.items():
            env_path = os.path.join(self.base_path, file)
            if not os.path.exists(env_path):
                continue

            with open(env_path, 'r') as f:
                config = {}
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            key, value = line.split('=', 1)
                            config[key.strip()] = value.strip().strip('"\'')
                        except ValueError:
                            issues[env].append(f"Invalid line format: {line}")

            # Check required fields
            for field, field_type in required_fields.items():
                if field not in config:
                    issues[env].append(f"Missing required field: {field}")
                else:
                    try:
                        if field_type == int:
                            int(config[field])
                    except ValueError:
                        issues[env].append(f"Invalid value type for {field}: expected {field_type.__name__}")

        return issues

    def switch_environment(self, env: str) -> bool:
        """Switch to specified environment"""
        if env not in self.env_files:
            logger.error(f"Invalid environment: {env}")
            return False

        src = os.path.join(self.base_path, self.env_files[env])
        dst = os.path.join(self.base_path, '.env')

        if not os.path.exists(src):
            logger.error(f"Environment file not found: {src}")
            return False

        try:
            shutil.copy2(src, dst)
            logger.info(f"Switched to {env} environment")
            return True
        except Exception as e:
            logger.error(f"Failed to switch environment: {str(e)}")
            return False


def main():
    """CLI interface for ConfigManager"""
    config_manager = ConfigManager()

    if len(sys.argv) < 2:
        print("Available commands:")
        print("  validate        - Validate all configurations")
        print("  create-dirs    - Create required directories")
        print("  backup         - Backup configuration files")
        print("  switch <env>   - Switch to specified environment (dev/prod/test)")
        sys.exit(1)

    command = sys.argv[1]

    if command == "validate":
        path_results = config_manager.validate_paths()
        value_results = config_manager.validate_config_values()

        print("\nPath Validation Results:")
        for env, results in path_results.items():
            print(f"\n{env.upper()} Environment:")
            print("Valid paths:", json.dumps(results['valid'], indent=2))
            print("Invalid paths:", json.dumps(results['invalid'], indent=2))

        print("\nValue Validation Results:")
        for env, issues in value_results.items():
            print(f"\n{env.upper()} Environment:")
            if issues:
                print("Issues found:")
                for issue in issues:
                    print(f"- {issue}")
            else:
                print("No issues found")

    elif command == "create-dirs":
        config_manager.create_required_directories()
        print("Created all required directories")

    elif command == "backup":
        backup_dir = config_manager.backup_config()
        print(f"Configuration backed up to: {backup_dir}")

    elif command == "switch" and len(sys.argv) == 3:
        env = sys.argv[2]
        if config_manager.switch_environment(env):
            print(f"Switched to {env} environment")
        else:
            print("Failed to switch environment")
            sys.exit(1)
    else:
        print("Invalid command")
        sys.exit(1)


if __name__ == "__main__":
    main()
