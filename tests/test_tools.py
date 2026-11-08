"""ツールのテスト（LLMもAPIキーも使わない）。"""

import json

from app import tools


def test_glossary_ids_are_unique_and_related_links_exist():
    terms = tools.load_glossary()
    ids = [t["id"] for t in terms]
    assert len(ids) == len(set(ids))
    for t in terms:
        for r in t["related"]:
            assert r in ids, f"{t['id']} の related に存在しない id: {r}"


def test_search_finds_term_by_name_and_alias():
    for query in ["LoRA", "lora", "Low-Rank Adaptation"]:
        hits = json.loads(tools.search_glossary(query))
        assert hits[0]["term"] == "LoRA", query


def test_search_finds_course_specific_term():
    hits = json.loads(tools.search_glossary("lecNN-start"))
    assert hits[0]["term"] == "lecNN-start タグ"


def test_search_limits_number_of_results():
    hits = json.loads(tools.search_glossary("エージェント"))
    assert 1 <= len(hits) <= tools.MAX_RESULTS


def test_search_reports_not_found():
    assert "見つかりませんでした" in tools.search_glossary("存在しない用語xyz")


def test_lecture_summary():
    assert "エージェント" in tools.get_lecture_summary(3)
    assert "まだありません" in tools.get_lecture_summary(99)


def test_default_question_of_lecture1_is_answerable_from_glossary():
    """第1回の既定の質問（app.ask）は、第3回のエージェントが用語集で正しく答えられること。"""
    from app.ask import DEFAULT_QUESTION

    assert "3レベル" in DEFAULT_QUESTION
    hits = json.loads(tools.search_glossary("3レベル"))
    assert hits[0]["term"] == "宿題の3レベル"



# ---- 第3回 演習: make_quiz ----

def test_make_quiz_returns_question_and_answer_from_the_lecture():
    quiz = json.loads(tools.make_quiz(2))
    terms = {t["term"]: t for t in tools.load_glossary() if t["lecture"] == 2}
    term = quiz["question"].removeprefix("「").removesuffix("」の意味は？")
    assert term in terms
    assert quiz["answer"] == terms[term]["definition"]


def test_make_quiz_reports_lecture_without_terms():
    assert "ありません" in tools.make_quiz(0)
    assert "ありません" in tools.make_quiz(99)


# ---- 第3回 宿題（実装）: save_learning_log ----

def test_save_learning_log_writes_markdown(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LOG_DIR", tmp_path / "learning_log")
    message = tools.save_learning_log("LoRAとQLoRAの違い", "- LoRAは差分だけを学習する")
    files = list((tmp_path / "learning_log").glob("*.md"))
    assert len(files) == 1 and files[0].name in message
    text = files[0].read_text(encoding="utf-8")
    assert text.startswith("# LoRAとQLoRAの違い") and "差分だけを学習" in text


def test_save_learning_log_does_not_overwrite_or_escape(tmp_path, monkeypatch):
    log_dir = tmp_path / "learning_log"
    monkeypatch.setattr(tools, "LOG_DIR", log_dir)
    tools.save_learning_log("../../evil", "a")
    tools.save_learning_log("../../evil", "b")
    files = list(log_dir.glob("*.md"))
    assert len(files) == 2  # 同じ見出しでも上書きしない
    assert all(f.parent == log_dir and ".." not in f.name for f in files)  # フォルダの外に出ない
    assert list(tmp_path.glob("*.md")) == []


def test_save_learning_log_rejects_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LOG_DIR", tmp_path / "learning_log")
    assert "保存はしていません" in tools.save_learning_log("  ", "本文")
    assert not (tmp_path / "learning_log").exists()
