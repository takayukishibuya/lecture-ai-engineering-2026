"""第1回: 素のLLMに質問するスクリプト。

使い方:
    uv run python -m app.ask "LoRAとは何ですか？"
    uv run python -m app.ask            # 質問を省略すると、講座に固有の質問をする
    uv run python -m app.ask --temperature 1.5 "LoRAとは何ですか？"
    uv run python -m app.ask --chat     # 会話履歴を保ったまま続けて質問する（宿題・実装）

ツールを持たない「素の」呼び出し。
講座に固有のことを聞くと、「分からない」と答えるか、一般論でもっともらしく答える
（講座の実際とは違う）ことを確かめよう。
（第3回で、用語集を検索できるエージェントにして改善する）
"""

import argparse
import time

from google import genai
from google.genai import errors, types

from app.config import MODEL, api_error_message, get_api_key

# 講座に固有の質問。正しい答えは data/glossary.json の homework-levels にある
DEFAULT_QUESTION = "AIE2026の講座の宿題にある「3レベル」とは何ですか？"

# 対話モードを終了する入力
EXIT_WORDS = {"exit", "quit", "q", "終了"}


def make_config(temperature: float | None) -> types.GenerateContentConfig | None:
    """temperature が指定されたときだけ config を作る（未指定ならモデルの既定値）。"""
    if temperature is None:
        return None
    return types.GenerateContentConfig(temperature=temperature)


def print_usage(response: types.GenerateContentResponse, elapsed: float) -> None:
    """response.usage_metadata から入力・出力トークン数と応答時間を表示する。"""
    usage = response.usage_metadata
    if usage is None:
        print(f"\n[usage] トークン数を取得できませんでした / 応答時間 {elapsed:.2f} 秒")
        return
    # 思考（thinking）するモデルでは、出力とは別に思考トークンが数えられる
    thoughts = usage.thoughts_token_count or 0
    print(
        f"\n[usage] 入力 {usage.prompt_token_count} / "
        f"出力 {usage.candidates_token_count} / "
        f"思考 {thoughts} / 合計 {usage.total_token_count} トークン / "
        f"応答時間 {elapsed:.2f} 秒"
    )


def ask(question: str, temperature: float | None = None) -> str:
    """1回だけ質問し、回答を表示したあとトークン数と応答時間を表示する。"""
    client = genai.Client(api_key=get_api_key())
    start = time.perf_counter()
    response = client.models.generate_content(
        model=MODEL, contents=question, config=make_config(temperature)
    )
    elapsed = time.perf_counter() - start

    print(response.text)
    # 第1回 演習: response.usage_metadata から入力・出力トークン数を表示する
    print_usage(response, elapsed)

    return response.text


def chat_loop(first_question: str | None, temperature: float | None = None) -> None:
    """会話履歴を保ったまま、続けて質問できる対話モード（宿題・実装）。

    client.chats.create で作ったチャットは、これまでの質問と回答を履歴として持ち、
    send_message のたびに履歴ごとモデルに送る。そのため、回を重ねるほど入力トークン数が増える。
    """
    client = genai.Client(api_key=get_api_key())
    chat = client.chats.create(model=MODEL, config=make_config(temperature))
    print("会話モードです。続けて質問できます（exit / quit / 終了 で終わる）。\n")

    question = first_question
    while True:
        if question is None:
            try:
                question = input("あなた> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
        if not question:
            question = None
            continue
        if question.lower() in EXIT_WORDS:
            break

        try:
            start = time.perf_counter()
            response = chat.send_message(question)
            elapsed = time.perf_counter() - start
        except errors.APIError as e:
            # レート制限などで失敗しても、会話は続けられるようにする
            print(api_error_message(e.code, e.message))
        else:
            print(f"\nモデル> {response.text}")
            print_usage(response, elapsed)
            print(f"[history] 履歴のメッセージ数 {len(chat.get_history())}\n")
        question = None


def main() -> None:
    parser = argparse.ArgumentParser(description="素のLLMに質問する")
    parser.add_argument("question", nargs="?", default=None)
    parser.add_argument(
        "--chat", action="store_true", help="会話履歴を保ったまま続けて質問する"
    )
    parser.add_argument(
        "--temperature", type=float, default=None, help="生成の温度（例: 0.0〜2.0）"
    )
    args = parser.parse_args()

    print(f"[model] {MODEL}")
    if args.temperature is not None:
        print(f"[temperature] {args.temperature}")

    if args.chat:
        chat_loop(args.question, args.temperature)
        return

    question = args.question or DEFAULT_QUESTION
    print(f"[質問] {question}\n")
    try:
        ask(question, args.temperature)
    except errors.APIError as e:
        print(api_error_message(e.code, e.message))
        raise SystemExit(1)


if __name__ == "__main__":
    main()