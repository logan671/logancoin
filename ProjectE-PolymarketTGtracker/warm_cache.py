import time

from market_cache import build_token_map


def main() -> None:
    start = time.time()
    token_map = build_token_map()
    elapsed = time.time() - start
    print(f"cache_tokens={len(token_map)} elapsed={elapsed:.2f}s")


if __name__ == "__main__":
    main()
