import textwrap

class Utils:
    @staticmethod
    def indent(text: str, prefix: str):
        return textwrap.indent(textwrap.dedent(text), prefix)