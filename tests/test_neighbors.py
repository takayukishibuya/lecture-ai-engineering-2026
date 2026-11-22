"""第5回 宿題（実装）: 検索結果に前後ページを付ける処理。APIは呼ばない。"""

from app import retrieval


def _pages():
    pages = []
    for doc in ("lec01-main", "lec02-main"):
        for n in range(1, 6):
            pages.append({"page_id": f"{doc}-p{n:03d}", "document_id": doc, "lecture": int(doc[3:5]),
                          "document_title": doc, "section": "章", "title": f"{doc} {n}",
                          "page": n, "content": f"本文 {doc} {n}"})
    return pages


def _hit(page_id, distance):
    page = next(p for p in _pages() if p["page_id"] == page_id)
    return {**page, "distance": distance}


def test_window_zero_returns_hits_unchanged():
    hits = [_hit("lec01-main-p003", 0.1)]
    assert retrieval.add_neighbors(hits, 0, _pages()) == hits


def test_adds_previous_and_next_page_in_reading_order():
    results = retrieval.add_neighbors([_hit("lec01-main-p003", 0.1)], 1, _pages())
    assert [r["page_id"] for r in results] == ["lec01-main-p002", "lec01-main-p003", "lec01-main-p004"]
    assert [r["role"] for r in results] == ["前後ページ", "検索結果", "前後ページ"]
    assert results[0]["neighbor_of"] == "lec01-main-p003"
    assert "distance" not in results[0] and results[1]["distance"] == 0.1


def test_does_not_cross_documents_at_the_edges():
    results = retrieval.add_neighbors([_hit("lec01-main-p005", 0.1), _hit("lec02-main-p001", 0.2)], 1, _pages())
    ids = [r["page_id"] for r in results]
    assert ids == ["lec01-main-p004", "lec01-main-p005", "lec02-main-p001", "lec02-main-p002"]


def test_no_duplicates_and_overlapping_hit_keeps_its_distance():
    hits = [_hit("lec01-main-p002", 0.1), _hit("lec01-main-p003", 0.2)]
    results = retrieval.add_neighbors(hits, 1, _pages())
    ids = [r["page_id"] for r in results]
    assert ids == ["lec01-main-p001", "lec01-main-p002", "lec01-main-p003", "lec01-main-p004"]
    assert len(ids) == len(set(ids))
    p003 = next(r for r in results if r["page_id"] == "lec01-main-p003")
    assert p003["role"] == "検索結果" and p003["distance"] == 0.2


def test_search_with_neighbors_uses_search(monkeypatch):
    monkeypatch.setattr(retrieval, "search", lambda q: [_hit("lec01-main-p003", 0.1)])
    monkeypatch.setattr(retrieval, "load_pages", lambda source=None: _pages())
    assert len(retrieval.search_with_neighbors("q", 1)) == 3
    assert len(retrieval.search_with_neighbors("q", 0)) == 1
