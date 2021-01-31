from enum import Enum


class ConnectorType(Enum):
    AND = 'AND'
    OR = 'OR'
    
    @classmethod
    def has_value(cls, value: int) -> bool:
        return value in cls._value2member_map_
