import re

class Regex:
    @staticmethod
    def search(pattern: str, string: str):
        return re.search(pattern, string)
    
    @staticmethod
    def findall(pattern: str, string: str):
        return re.findall(pattern, string)
    
    @classmethod
    def re_findall_in_group(cls, pattern: str, string: str, group: int):
        result = re.findall(pattern, string)

        return cls.check_result(result[0], group) if result else cls.fill_empty(group)

    @classmethod
    def re_match_in_group(cls, pattern: str, string: str, group: int):
        match = re.search(pattern, string)

        return cls.check_result(cls.split(match.group(1)), group) if match else cls.fill_empty(group)
    
    @classmethod
    def find_illegal_chars(cls, string: str):
        return re.findall(r'[<>:"|?*\x00-\x1F]', string)
    
    @classmethod
    def find_illegal_chars_ex(cls, string: str):
        return re.findall(r'[<>:"\\/|?*\x00-\x1F]', string)
    
    @classmethod
    def find_output_format(cls, acodec: str):
        return re.findall(r"\w+", acodec)
    
    @classmethod
    def find_string(cls, pattern: str, string: str):
        find = re.findall(pattern, string)
    
        if find:
            return find[0]
        else:
            return None
    
    @classmethod
    def check_result(cls, result: list, group: int):
        if len(result) < group:
            result.extend(cls.fill_empty(group - len(result)))

        return result
    
    @staticmethod
    def fill_empty(group):
        return ["--" for i in range(group)]
    
    @staticmethod
    def split(text):
        result = []
        current = []
        stack = []
        
        for char in text:
            if char in '([{':
                stack.append(char)
                current.append(char)
                continue
                
            if char in ')]}':
                if stack:
                    stack.pop()
                current.append(char)
                continue
                
            if char == ',' and not stack:
                result.append(''.join(current).strip())
                current = []
                continue
                
            current.append(char)
        
        if current:
            result.append(''.join(current).strip())
        
        return result
    
    @staticmethod
    def sub(pattern: str, repl: str, string: str):
        return re.sub(pattern, repl, string)