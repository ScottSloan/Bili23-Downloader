import textwrap

from utils.common.model.task_info import DownloadTaskInfo

class MetadataNFOFile:
    class Movie:
        def __init__(self):
            pass

        def get_contents(self):
            return textwrap.dedent("""\
                <?xml version="1.0" encoding="UTF-8"?>
                <movie>
                    <title>Example Movie</title>
                    <runtime>120</runtime>
                    <year>2023</year>
                    <studio>Bilibili</studio>
                    <actor>
                        <name>Actor Name</name>
                        <role>Creator</role>
                    </actor>
                </movie>\
                """)

    class TVShow:
        def __init__(self):
            pass

    class Episode:
        def __init__(self):
            pass