from utils.parse.video import InteractVideoInfo

class Graph:
    @classmethod
    def get_graph_json(cls, font_name: str):
        return {
            "graph": cls.get_graph_viz_dot(font_name),
            "title": InteractVideoInfo.title
        }
    
    @staticmethod
    def get_graph_viz_dot(font_name: str):
        dot = [
            "rankdir=LR;",
            f'node [shape = box, fontname = "{font_name}", width=1.5, height = 0.5];',
            f'edge [fontname="{font_name}"];'
        ]

        node_name = {}

        for node in InteractVideoInfo.node_list:
            node_name[node.cid] = node.title

            for option in node.options:
                if option.show:
                    label = f' [label = "{option.name}"];'
                else:
                    label = ''

                dot.append(f'"{node.cid}" -> "{option.target_node_cid}"{label}')

        result = "".join(dot)

        for key, value in node_name.items():
            result = result.replace(str(key), value)

        return "digraph {" + result + "}"