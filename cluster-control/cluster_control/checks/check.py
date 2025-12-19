from abc import ABC, abstractmethod

class Check(ABC):
    
    @abstractmethod
    def check(self,) -> bool:
        """Perform a health check"""
        pass

    @abstractmethod
    def get_name(self,) -> str:
        pass