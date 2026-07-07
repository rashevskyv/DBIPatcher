"""Custom exceptions and error handling for the DBI Patcher pipeline."""


class DBIPatcherError(Exception):
    """Base exception for all DBI Patcher errors."""
    pass


class ConfigurationError(DBIPatcherError):
    """Raised when configuration files are missing or invalid."""
    pass


class DataValidationError(DBIPatcherError):
    """Raised when data validation fails."""
    pass


class TranslationError(DBIPatcherError):
    """Raised when translation operations fail."""
    pass


class ExportError(DBIPatcherError):
    """Raised when export/build operations fail."""
    pass


class GitError(DBIPatcherError):
    """Raised when Git operations fail."""
    pass


def check_file_exists(path, description: str) -> None:
    """Validate that a file exists, raise ConfigurationError if not.
    
    Args:
        path: Path to check
        description: Human-readable description of the file
        
    Raises:
        ConfigurationError: If file does not exist
    """
    if not path.exists():
        raise ConfigurationError(
            f"[ERROR] {description} not found: {path}\n"
            f"       Make sure you've run the necessary setup steps."
        )


def check_file_readable(path, description: str) -> None:
    """Validate that a file exists and is readable.
    
    Args:
        path: Path to check
        description: Human-readable description of the file
        
    Raises:
        ConfigurationError: If file doesn't exist or isn't readable
    """
    check_file_exists(path, description)
    if not path.is_file():
        raise ConfigurationError(f"[ERROR] {description} is not a file: {path}")
    try:
        # Just check if we can read the file
        with open(path, 'r', encoding='utf-8') as f:
            f.read(1)
    except (PermissionError, IOError) as e:
        raise ConfigurationError(f"[ERROR] Cannot read {description}: {e}")


def check_dependencies() -> None:
    """Validate that all required Python packages are installed.
    
    Raises:
        ConfigurationError: If any required package is missing
    """
    try:
        import openpyxl
    except ImportError:
        raise ConfigurationError(
            "[ERROR] Required package 'openpyxl' is not installed.\n"
            "        Run: pip install -r requirements.txt"
        )
    
    try:
        import requests
    except ImportError:
        raise ConfigurationError(
            "[ERROR] Required package 'requests' is not installed.\n"
            "        Run: pip install -r requirements.txt"
        )


def check_ai_service(provider: str) -> None:
    """Validate that the AI service is accessible.
    
    Args:
        provider: AI provider name ('OMNIROAD' or 'GEMINI_PROXY')
        
    Raises:
        ConfigurationError: If AI service is not accessible
    """
    import requests
    
    if provider == "OMNIROAD":
        url = "http://localhost:20128/v1/chat/completions"
        service_name = "OmniRoad"
    elif provider == "GEMINI_PROXY":
        url = "http://127.0.0.1:2048/v1/chat/completions"
        service_name = "Gemini Proxy"
    else:
        return
    
    try:
        response = requests.head(url.rsplit("/", 1)[0], timeout=5)
        if response.status_code >= 500:
            raise ConfigurationError(
                f"[ERROR] {service_name} is not responding correctly.\n"
                f"        Status: {response.status_code}\n"
                f"        Please ensure the service is running."
            )
    except requests.ConnectionError:
        raise ConfigurationError(
            f"[ERROR] Cannot connect to {service_name} at {url.rsplit('/v1', 1)[0]}\n"
            f"        Please start the service and try again."
        )
    except requests.Timeout:
        raise ConfigurationError(
            f"[ERROR] {service_name} is not responding (timeout).\n"
            f"        Please check if the service is running and responding."
        )


def handle_command_error(cmd_name: str, error: Exception) -> None:
    """Print a formatted error message for command failures.
    
    Args:
        cmd_name: Name of the command that failed
        error: The exception that occurred
    """
    print(f"\n{'='*60}")
    print(f"  [ERROR] Command '{cmd_name}' failed!")
    print(f"{'='*60}")
    print(f"\n{str(error)}")
    print(f"\n{'='*60}\n")
