from abc import ABC, abstractmethod

class Check(ABC):
    @abstractmethod
    def check(self) -> bool:
        """Perform a health check"""

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the check"""
