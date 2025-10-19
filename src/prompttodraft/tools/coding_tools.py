from abc import ABC, abstractmethod

class Output:
    pass

class CodingTool(ABC):   
    @abstractmethod
    def bash_tool(self, command: str, timeout: int | None = None) -> Output:
        pass
    
    @abstractmethod
    def edit_tool(self, file_path: str, old_string: str, new_string: str) -> Output:
        pass
    
    @abstractmethod
    def glob_tool(self, pattern: str, path: str | None = None) -> Output:
        pass
    
    @abstractmethod
    def grep_tool(self, pattern: str, include: str | None = None, path: str | None = None) -> Output:
        pass
    
    @abstractmethod
    def ls_tool(self, path: str) -> Output:
        pass
        
    @abstractmethod
    def replace_tool(self, file_path: str, content: str) -> Output:
        pass
        
    @abstractmethod
    def user_input_tool(self, question: str) -> Output:
        pass
    
    @abstractmethod
    def view_tool(self, file_path: str) -> Output:
        pass
    
    
class CodingToolDocker(CodingTool):
    pass

class CodingToolE2B(CodingTool):
    pass

class CodingToolLocal(CodingTool):
    pass