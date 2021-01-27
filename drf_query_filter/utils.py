from enum import Enum


class QueryType(Enum):
    AND = 1
    OR = 2
    
    @classmethod
    def has_value(cls, value: int) -> bool:
        return value in cls._value2member_map_