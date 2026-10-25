from util.parse.parser.favorite import FavoriteParser


def _capture_callback(parser):
    captured = []
    parser.success_callback = captured.append

    return captured


def test_favorite_list_empty_folder_still_queries_cover(monkeypatch):
    # 收藏夹没有视频（media_count = 0）但用户设置过封面时，仍应走 __query__ 懒加载去
    # folder/info 取封面。此前 count > 0 才走 __query__，这类收藏夹的封面永远拿不到
    import util.parse.parser.favorite as favorite_module

    monkeypatch.setattr(favorite_module, "post_to_main_thread", lambda cb, *args: cb(*args))

    parser = FavoriteParser()
    captured = _capture_callback(parser)

    parser.on_get_favorite_list_success({
        "data": {
            "list": [
                {"id": 123, "title": "空收藏夹", "mid": 1, "media_count": 0},
            ]
        }
    })

    assert len(captured) == 1
    assert captured[0][0]["cover_id"] == "__query__123"
    assert captured[0][0]["cover"] == 123


def test_favorite_list_non_empty_folder_queries_cover(monkeypatch):
    # 有视频的收藏夹行为不变，防止改动 2 时误伤原路径
    import util.parse.parser.favorite as favorite_module

    monkeypatch.setattr(favorite_module, "post_to_main_thread", lambda cb, *args: cb(*args))

    parser = FavoriteParser()
    captured = _capture_callback(parser)

    parser.on_get_favorite_list_success({
        "data": {
            "list": [
                {"id": 456, "title": "有视频的收藏夹", "mid": 1, "media_count": 10},
            ]
        }
    })

    assert captured[0][0]["cover_id"] == "__query__456"


def test_favorite_list_fid_zero_produces_query_cover_id(monkeypatch):
    # fid 为 0 是接口不会返回的边界值。此处只陈述 parser 的产出：cover_id 为
    # "__query__0"、cover 为 0。0 在 worker 侧 _run 的 if not self.cover_url
    # 中走"无需请求"路径的语义，由 test_cover_query_worker.py 钉死
    import util.parse.parser.favorite as favorite_module

    monkeypatch.setattr(favorite_module, "post_to_main_thread", lambda cb, *args: cb(*args))

    parser = FavoriteParser()
    captured = _capture_callback(parser)

    parser.on_get_favorite_list_success({
        "data": {
            "list": [
                {"id": 0, "title": "无效收藏夹", "mid": 1, "media_count": 0},
            ]
        }
    })

    assert captured[0][0]["cover_id"] == "__query__0"
    assert captured[0][0]["cover"] == 0