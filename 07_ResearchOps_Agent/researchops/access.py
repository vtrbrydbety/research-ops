"""Local administration: python -m researchops.access --help."""

import argparse
import json
from uuid import UUID

from researchops.core.config import get_settings
from researchops.services.access_store import AccessStore


def main():
    parser = argparse.ArgumentParser(description="本地邀请码管理；不会向公网提供管理员接口")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="生成邀请码，明文仅显示一次")
    create.add_argument("--label", required=True)
    create.add_argument("--days", type=int)
    create.add_argument("--limit", type=int)
    commands.add_parser("list", help="仅列出元数据")
    revoke = commands.add_parser("revoke", help="停用邀请码及所有会话")
    revoke.add_argument("principal", type=UUID)
    update = commands.add_parser("update", help="修改额度或有效期")
    update.add_argument("principal", type=UUID)
    update.add_argument("--days", type=int)
    update.add_argument("--limit", type=int)
    bind = commands.add_parser("bind", help="显式认领旧评估；执行前备份数据")
    bind.add_argument("assessment", type=UUID)
    bind.add_argument("principal", type=UUID)
    args = parser.parse_args()
    settings = get_settings()
    store = AccessStore(settings)
    if args.command == "create":
        principal, token = store.create_invitation(args.label, days=args.days, limit=args.limit)
        print(json.dumps({"principal_id": principal, "invitation_code": token}, ensure_ascii=False))
    elif args.command == "list":
        print(json.dumps(store.list_invitations(), ensure_ascii=False, indent=2))
    elif args.command == "bind":
        path = settings.assessment_review_store_dir / f"{args.assessment}.json"
        if not path.is_file() or path.is_symlink():
            parser.error("评估文件不存在")
        document = json.loads(path.read_text())
        expires = float(document["expires_at"])
        if expires <= store.clock():
            parser.error("评估已经过期")
        store.bind("assessment", args.assessment, str(args.principal), expires=expires)
        print("归属绑定完成。")
    else:
        store.update_invitation(
            str(args.principal),
            revoke=args.command == "revoke",
            limit=getattr(args, "limit", None),
            days=getattr(args, "days", None),
        )
        print("邀请码已更新。")


if __name__ == "__main__":
    main()
