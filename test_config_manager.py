import os
import pytest
import shutil
from pathlib import Path

from config_manager import ConfigManager

# Test data
TEST_ENV_CONTENT = """
# API Configuration
API_V1_STR=/api
PROJECT_NAME=Test API
VERSION=1.0.0
HOST=0.0.0.0
PORT=8000
DATABASE_URL=C:/Users/User/Desktop/PycharmProjects/pythonProject5/test_invoices.db
SECRET_KEY=test-key
"""


@pytest.fixture
def config_manager(tmp_path):
    """Fixture to create a ConfigManager instance with temporary directory"""
    # Create temporary test environment
    test_dir = tmp_path / "test_project"
    test_dir.mkdir()

    # Create test environment files
    env_files = {
        '.env': TEST_ENV_CONTENT,
        '.env.dev': TEST_ENV_CONTENT.replace('8000', '8001'),
        '.env.prod': TEST_ENV_CONTENT.replace('8000', '8002'),
        '.env.test': TEST_ENV_CONTENT.replace('8000', '8003')
    }

    for filename, content in env_files.items():
        (test_dir / filename).write_text(content)

    # Create test directories
    test_dirs = ['uploads', 'templates', 'backups']
    for dir_name in test_dirs:
        (test_dir / dir_name).mkdir()

    # Initialize ConfigManager with test directory
    manager = ConfigManager(base_path=str(test_dir))

    yield manager

    # Cleanup
    shutil.rmtree(str(test_dir))


def test_validate_paths(config_manager, tmp_path):
    """Test path validation"""
    # Create test directories and files
    test_dir = Path(config_manager.base_path)
    (test_dir / "uploads").mkdir(exist_ok=True)
    (test_dir / "templates").mkdir(exist_ok=True)

    # Validate paths
    results = config_manager.validate_paths()

    # Check results
    assert 'dev' in results
    assert 'prod' in results
    assert 'test' in results
    assert 'default' in results

    # Verify valid paths are detected
    for env in results:
        assert 'valid' in results[env]
        assert 'invalid' in results[env]


def test_create_required_directories(config_manager):
    """Test directory creation"""
    # Remove existing directories
    test_dir = Path(config_manager.base_path)
    for dir_name in ['uploads', 'templates', 'backups']:
        if (test_dir / dir_name).exists():
            shutil.rmtree(str(test_dir / dir_name))

    # Create directories
    config_manager.create_required_directories()

    # Verify directories were created
    required_dirs = [
        'uploads', 'uploads_dev', 'uploads_prod', 'uploads_test',
        'templates', 'templates_dev', 'templates_prod', 'templates_test',
        'backups', 'test_reports', 'ssl'
    ]

    for dir_name in required_dirs:
        assert (test_dir / dir_name).exists()
        assert (test_dir / dir_name).is_dir()


def test_backup_config(config_manager):
    """Test configuration backup"""
    # Create backup
    backup_dir = config_manager.backup_config()

    # Verify backup directory exists
    assert os.path.exists(backup_dir)

    # Verify backup files
    for env_file in config_manager.env_files.values():
        backup_file = os.path.join(backup_dir, env_file)
        assert os.path.exists(backup_file)

        # Verify content was copied correctly
        original = os.path.join(config_manager.base_path, env_file)
        with open(original, 'r') as f1, open(backup_file, 'r') as f2:
            assert f1.read() == f2.read()


def test_validate_config_values(config_manager):
    """Test configuration value validation"""
    # Validate configurations
    issues = config_manager.validate_config_values()

    # Check results structure
    assert all(env in issues for env in ['dev', 'prod', 'test', 'default'])

    # Verify no issues with valid config
    assert all(len(issues[env]) == 0 for env in issues)

    # Test with invalid config
    invalid_content = """
    API_V1_STR=/api
    PORT=invalid_port
    """
    invalid_env = os.path.join(config_manager.base_path, '.env.invalid')
    with open(invalid_env, 'w') as f:
        f.write(invalid_content)

    config_manager.env_files['invalid'] = '.env.invalid'
    issues = config_manager.validate_config_values()

    assert 'invalid' in issues
    assert len(issues['invalid']) > 0
    assert any('PORT' in issue for issue in issues['invalid'])


def test_switch_environment(config_manager):
    """Test environment switching"""
    # Test switching to each environment
    for env in ['dev', 'prod', 'test']:
        assert config_manager.switch_environment(env)

        # Verify switch was successful
        current_env = os.path.join(config_manager.base_path, '.env')
        target_env = os.path.join(config_manager.base_path, config_manager.env_files[env])

        with open(current_env, 'r') as f1, open(target_env, 'r') as f2:
            assert f1.read() == f2.read()


def test_invalid_environment_switch(config_manager):
    """Test switching to invalid environment"""
    assert not config_manager.switch_environment('invalid_env')


def test_missing_environment_file(config_manager):
    """Test handling of missing environment file"""
    # Remove an environment file
    os.remove(os.path.join(config_manager.base_path, '.env.dev'))

    # Verify switch fails gracefully
    assert not config_manager.switch_environment('dev')


def test_backup_rotation(config_manager):
    """Test multiple backups"""
    # Create multiple backups
    backup_dirs = [config_manager.backup_config() for _ in range(3)]

    # Verify all backups exist and are unique
    assert len(backup_dirs) == len(set(backup_dirs))
    for backup_dir in backup_dirs:
        assert os.path.exists(backup_dir)


if __name__ == '__main__':
    pytest.main([__file__])
