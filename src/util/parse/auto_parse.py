from dataclasses import dataclass

from ..common.enum import ParserType

@dataclass(frozen = True)
class AutoParsePayload:
    url: str = None
    start_page: int = None
    end_page: int = None
    parser_type: ParserType = None
    data: dict = None
    auto_parse: bool = True