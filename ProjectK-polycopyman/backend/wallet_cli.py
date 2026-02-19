import argparse
import getpass
import os
import sys

from .repositories.vault import list_key_refs, upsert_key_ref


def _read_passphrase() -> str:
    from_env = os.environ.get("PROJECTK_VAULT_PASSPHRASE", "").strip()
    if from_env:
        return from_env

    p1 = getpass.getpass("Vault 비밀번호 입력: ").strip()
    p2 = getpass.getpass("Vault 비밀번호 다시 입력: ").strip()
    if not p1:
        raise SystemExit("Vault 비밀번호는 비어 있을 수 없습니다.")
    if p1 != p2:
        raise SystemExit("Vault 비밀번호가 서로 다릅니다.")
    return p1


def _read_mnemonic(cli_value: str | None) -> str:
    if cli_value:
        return cli_value.strip()
    value = getpass.getpass("니모닉 입력(화면 비표시): ").strip()
    if not value:
        raise SystemExit("니모닉은 비어 있을 수 없습니다.")
    return value


def _to_key_ref(name: str) -> str:
    key_name = name.strip()
    if not key_name:
        raise SystemExit("지갑 이름이 비어 있습니다.")
    if " " in key_name:
        raise SystemExit("지갑 이름에 공백을 넣을 수 없습니다.")
    if key_name.startswith("vault://"):
        return key_name
    return f"vault://{key_name}"


def cmd_add(args: argparse.Namespace) -> int:
    key_ref = _to_key_ref(args.name)
    passphrase = _read_passphrase()
    mnemonic = _read_mnemonic(args.mnemonic)
    upsert_key_ref(key_ref=key_ref, mnemonic=mnemonic, passphrase=passphrase)
    print("저장 완료")
    print(f"key_ref: {key_ref}")
    print("이제 텔레그램 /addpair 단계에서 위 key_ref를 입력하세요.")
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    rows = list_key_refs()
    if not rows:
        print("등록된 key_ref가 없습니다.")
        return 0
    for idx, row in enumerate(rows, start=1):
        print(f"{idx}. {row['key_ref']} | status={row['status']} | updated_at={row['updated_at']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ProjectK wallet vault CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="니모닉을 암호화 저장하고 key_ref를 발급합니다.")
    add_p.add_argument("name", help="지갑 이름 또는 key_ref(vault://...)")
    add_p.add_argument(
        "--mnemonic",
        help="니모닉 평문 (보안상 권장하지 않음, 미입력 시 숨김 입력)",
    )
    add_p.set_defaults(func=cmd_add)

    list_p = sub.add_parser("list", help="등록된 key_ref 목록을 보여줍니다.")
    list_p.set_defaults(func=cmd_list)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    func = getattr(args, "func", None)
    if not func:
        parser.print_help(sys.stderr)
        return 2
    return int(func(args))


if __name__ == "__main__":
    raise SystemExit(main())
