import re

class REUtils:
    @classmethod
    def re_findall_in_group(cls, pattern: str, string: str, group: int):
        result = re.findall(pattern, string)

        return cls.check_result(result[0], group) if result else cls.fill_empty(group)

    @classmethod
    def re_match_in_group(cls, pattern: str, string: str, group: int):
        match = re.search(pattern, string)

        return cls.check_result(match.group(1).split(", "), group) if match else cls.fill_empty(group)
    
    @classmethod
    def find_illegal_chars(cls, string: str):
        return re.search(r'[<>:"|?*\x00-\x1F]', string)
    
    @classmethod
    def check_result(cls, result: list, group: int):
        if len(result) < group:
            result.extend(cls.fill_empty(group - len(result)))

        return result
    
    @staticmethod
    def fill_empty(group):
        return ["--" for i in range(group)]