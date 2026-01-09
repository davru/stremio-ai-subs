"""
Centralized logging utility for consistent console output across the application.
"""

class Logger:
    """Standardized logger with emoji prefixes and severity levels."""
    
    # Color codes for terminal output
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    
    @staticmethod
    def info(message: str, emoji: str = "ℹ️"):
        """Log informational message."""
        print(f"{Logger.CYAN}INFO:    {Logger.RESET} {emoji} {message}")
    
    @staticmethod
    def success(message: str, emoji: str = "✅"):
        """Log success message."""
        print(f"{Logger.GREEN}SUCCESS: {Logger.RESET} {emoji} {message}")
    
    @staticmethod
    def warning(message: str, emoji: str = "⚠️"):
        """Log warning message."""
        print(f"{Logger.YELLOW}WARNING: {Logger.RESET} {emoji} {message}")
    
    @staticmethod
    def error(message: str, emoji: str = "❌"):
        """Log error message."""
        print(f"{Logger.RED}ERROR:   {Logger.RESET} {emoji} {message}")
    
    @staticmethod
    def debug(message: str, emoji: str = "🔍"):
        """Log debug message."""
        print(f"{Logger.BLUE}DEBUG:   {Logger.RESET} {emoji} {message}")
    
    @staticmethod
    def process(message: str, emoji: str = "🔄"):
        """Log process/progress message."""
        print(f"{Logger.CYAN}PROCESS: {Logger.RESET} {emoji} {message}")
    
    # Specific domain loggers with custom emojis
    @staticmethod
    def search(message: str):
        """Log search operations."""
        Logger.info(message, "🔍")
    
    @staticmethod
    def download(message: str):
        """Log download operations."""
        Logger.info(message, "📥")
    
    @staticmethod
    def upload(message: str):
        """Log upload operations."""
        Logger.info(message, "📤")
    
    @staticmethod
    def translate(message: str):
        """Log translation operations."""
        Logger.info(message, "🌍")
    
    @staticmethod
    def auth(message: str):
        """Log authentication operations."""
        Logger.info(message, "🔑")
    
    @staticmethod
    def file(message: str):
        """Log file operations."""
        Logger.info(message, "📄")
    
    @staticmethod
    def batch(message: str, batch_num: int = None, total: int = None):
        """Log batch processing."""
        if batch_num and total:
            print(f"{Logger.CYAN}BATCH:   {Logger.RESET} 📦 [Batch {batch_num}/{total}] {message}")
        else:
            print(f"{Logger.CYAN}BATCH:   {Logger.RESET} 📦 {message}")
    
    @staticmethod
    def ai(message: str):
        """Log AI/model operations."""
        Logger.info(message, "🤖")
    
    @staticmethod
    def web(message: str):
        """Log web/network operations."""
        Logger.info(message, "🌐")


# Convenience instance for importing
log = Logger()
