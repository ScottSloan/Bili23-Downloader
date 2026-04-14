from util.common.timestamp import get_timestamp_ms
import json

def get_exclimbwuzhi_payload(user_agent: str, uuid: str):
    payload = {
        "3064": 1,
        "5062": str(get_timestamp_ms()),
        "03bf": "https%3A%2F%2Fwww.bilibili.com%2F",
        "39c8": "333.1007.fp.risk",
        "34f1": "",
        "d402": "",
        "654a": "",
        "6e7c": "1699x794",
        "3c43": {
            "2673": 0,
            "5766": 32,
            "6527": 0,
            "7003": 1,
            "807e": 1,
            "b8ce": user_agent,
            "641c": 0,
            "07a4": "zh-CN",
            "1c57": 32,
            "0bd0": 20,
            "748e": [
                960,
                1707
            ],
            "d61f": [
                912,
                1707
            ],
            "fc9d": -480,
            "6aa9": "Asia/Shanghai",
            "75b8": 1,
            "3b21": 1,
            "8a1c": 0,
            "d52f": "not available",
            "adca": "Win32",
            "80c9": [
                [
                    "PDF Viewer",
                    "Portable Document Format",
                    [
                        [
                            "application/pdf",
                            "pdf"
                        ],
                        [
                            "text/pdf",
                            "pdf"
                        ]
                    ]
                ],
                [
                    "Chrome PDF Viewer",
                    "Portable Document Format",
                    [
                        [
                            "application/pdf",
                            "pdf"
                        ],
                        [
                            "text/pdf",
                            "pdf"
                        ]
                    ]
                ],
                [
                    "Chromium PDF Viewer",
                    "Portable Document Format",
                    [
                        [
                            "application/pdf",
                            "pdf"
                        ],
                        [
                            "text/pdf",
                            "pdf"
                        ]
                    ]
                ],
                [
                    "Microsoft Edge PDF Viewer",
                    "Portable Document Format",
                    [
                        [
                            "application/pdf",
                            "pdf"
                        ],
                        [
                            "text/pdf",
                            "pdf"
                        ]
                    ]
                ],
                [
                    "WebKit built-in PDF",
                    "Portable Document Format",
                    [
                        [
                            "application/pdf",
                            "pdf"
                        ],
                        [
                            "text/pdf",
                            "pdf"
                        ]
                    ]
                ]
            ],
            "13ab": "EPQAAAAASUVORK5CYII=",
            "bfe9": "//TgNIfAAAAAZJREFUAwBde+3wgcxEHQAAAABJRU5ErkJggg==",
            "a3c1": [
                "extensions:ANGLE_instanced_arrays;EXT_blend_minmax;EXT_clip_control;EXT_color_buffer_half_float;EXT_depth_clamp;EXT_disjoint_timer_query;EXT_float_blend;EXT_frag_depth;EXT_polygon_offset_clamp;EXT_shader_texture_lod;EXT_texture_compression_bptc;EXT_texture_compression_rgtc;EXT_texture_filter_anisotropic;EXT_texture_mirror_clamp_to_edge;EXT_sRGB;KHR_parallel_shader_compile;OES_element_index_uint;OES_fbo_render_mipmap;OES_standard_derivatives;OES_texture_float;OES_texture_float_linear;OES_texture_half_float;OES_texture_half_float_linear;OES_vertex_array_object;WEBGL_blend_func_extended;WEBGL_color_buffer_float;WEBGL_compressed_texture_s3tc;WEBGL_compressed_texture_s3tc_srgb;WEBGL_debug_renderer_info;WEBGL_debug_shaders;WEBGL_depth_texture;WEBGL_draw_buffers;WEBGL_lose_context;WEBGL_multi_draw;WEBGL_polygon_mode",
                "webgl aliased line width range:[1, 1]",
                "webgl aliased point size range:[1, 1024]",
                "webgl alpha bits:8",
                "webgl antialiasing:yes",
                "webgl blue bits:8",
                "webgl depth bits:24",
                "webgl green bits:8",
                "webgl max anisotropy:16",
                "webgl max combined texture image units:32",
                "webgl max cube map texture size:16384",
                "webgl max fragment uniform vectors:1024",
                "webgl max render buffer size:16384",
                "webgl max texture image units:16",
                "webgl max texture size:16384",
                "webgl max varying vectors:30",
                "webgl max vertex attribs:16",
                "webgl max vertex texture image units:16",
                "webgl max vertex uniform vectors:4095",
                "webgl max viewport dims:[32767, 32767]",
                "webgl red bits:8",
                "webgl renderer:WebKit WebGL",
                "webgl shading language version:WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)",
                "webgl stencil bits:0",
                "webgl vendor:WebKit",
                "webgl version:WebGL 1.0 (OpenGL ES 2.0 Chromium)",
                "webgl unmasked vendor:Google Inc. (NVIDIA)",
                "webgl unmasked renderer:ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Laptop GPU (0x000028E0) Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "webgl vertex shader high float precision:23",
                "webgl vertex shader high float precision rangeMin:127",
                "webgl vertex shader high float precision rangeMax:127",
                "webgl vertex shader medium float precision:23",
                "webgl vertex shader medium float precision rangeMin:127",
                "webgl vertex shader medium float precision rangeMax:127",
                "webgl vertex shader low float precision:23",
                "webgl vertex shader low float precision rangeMin:127",
                "webgl vertex shader low float precision rangeMax:127",
                "webgl fragment shader high float precision:23",
                "webgl fragment shader high float precision rangeMin:127",
                "webgl fragment shader high float precision rangeMax:127",
                "webgl fragment shader medium float precision:23",
                "webgl fragment shader medium float precision rangeMin:127",
                "webgl fragment shader medium float precision rangeMax:127",
                "webgl fragment shader low float precision:23",
                "webgl fragment shader low float precision rangeMin:127",
                "webgl fragment shader low float precision rangeMax:127",
                "webgl vertex shader high int precision:0",
                "webgl vertex shader high int precision rangeMin:31",
                "webgl vertex shader high int precision rangeMax:30",
                "webgl vertex shader medium int precision:0",
                "webgl vertex shader medium int precision rangeMin:31",
                "webgl vertex shader medium int precision rangeMax:30",
                "webgl vertex shader low int precision:0",
                "webgl vertex shader low int precision rangeMin:31",
                "webgl vertex shader low int precision rangeMax:30",
                "webgl fragment shader high int precision:0",
                "webgl fragment shader high int precision rangeMin:31",
                "webgl fragment shader high int precision rangeMax:30",
                "webgl fragment shader medium int precision:0",
                "webgl fragment shader medium int precision rangeMin:31",
                "webgl fragment shader medium int precision rangeMax:30",
                "webgl fragment shader low int precision:0",
                "webgl fragment shader low int precision rangeMin:31",
                "webgl fragment shader low int precision rangeMax:30"
            ],
            "6bc5": "Google Inc. (NVIDIA)~ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Laptop GPU (0x000028E0) Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "ed31": 0,
            "72bd": 0,
            "097b": 0,
            "52cd": [
                0,
                0,
                0
            ],
            "a658": [
                "Arial",
                "Arial Black",
                "Arial Narrow",
                "Book Antiqua",
                "Bookman Old Style",
                "Calibri",
                "Cambria",
                "Cambria Math",
                "Century",
                "Century Gothic",
                "Century Schoolbook",
                "Comic Sans MS",
                "Consolas",
                "Courier",
                "Courier New",
                "Georgia",
                "Helvetica",
                "Impact",
                "Lucida Bright",
                "Lucida Calligraphy",
                "Lucida Console",
                "Lucida Fax",
                "Lucida Handwriting",
                "Lucida Sans",
                "Lucida Sans Typewriter",
                "Lucida Sans Unicode",
                "Microsoft Sans Serif",
                "Monotype Corsiva",
                "MS Gothic",
                "MS PGothic",
                "MS Reference Sans Serif",
                "MS Sans Serif",
                "MS Serif",
                "Palatino Linotype",
                "Segoe Print",
                "Segoe Script",
                "Segoe UI",
                "Segoe UI Light",
                "Segoe UI Semibold",
                "Segoe UI Symbol",
                "Tahoma",
                "Times",
                "Times New Roman",
                "Trebuchet MS",
                "Verdana",
                "Wingdings",
                "Wingdings 2",
                "Wingdings 3"
            ],
            "d02f": "124.04347527516074"
        },
        "54ef": "{\"b_ut\":\"\",\"home_version\":\"V8\",\"in_new_ab\":true,\"ab_version\":{\"for_ai_home_version\":\"V8\",\"in_theme_version\":\"OPEN\",\"enable_web_push\":\"DISABLE\",\"enable_ai_floor_api\":\"ENABLE\",\"enable_shortcut_key\":\"DISABLE\",\"rcmd_timeout_config\":\"550\",\"home_performance_opt\":\"ssr_fetch_opt\",\"infra_projection\":\"OFF\"},\"ab_split_num\":{\"for_ai_home_version\":54,\"in_theme_version\":30,\"enable_web_push\":10,\"enable_ai_floor_api\":137,\"enable_shortcut_key\":54,\"rcmd_timeout_config\":49,\"home_performance_opt\":49,\"infra_projection\":49},\"uniq_page_id\":\"1671272756362\",\"is_modern\":true}",
        "8b94": "",
        "df35": uuid,
        "07a4": "zh-CN",
        "5f45": None,
        "db46": 0
    }

    return json.dumps(
        {"payload": json.dumps(payload, separators = (",", ":"))},
        separators = (",", ":"),
    )
