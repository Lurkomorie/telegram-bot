#!/usr/bin/env python3
"""
Delta sync selected production tables from OLD DB -> NEW DB.

Behavior:
- Inserts rows that exist in old DB but not in new DB for:
  - users
  - chats
  - payment_transactions
  - chat_purchases
- Optionally patches premium entitlement fields on shared users when old DB
  has strictly stronger entitlement data.

Safe-by-default:
- Dry run unless --apply is provided.
- Insert-only for table rows (no overwrite).
- Premium patch only upgrades entitlement (never downgrades).
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple

import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json


TABLE_ORDER = ("users", "personas", "chats", "payment_transactions", "chat_purchases")
PK_BY_TABLE = {
    "users": "id",
    "personas": "id",
    "chats": "id",
    "payment_transactions": "id",
    "chat_purchases": "id",
}

TIER_RANK = {
    "free": 0,
    "plus": 1,
    "premium": 2,
    "pro": 3,
    "legendary": 4,
}


@dataclass
class InsertStats:
    table: str
    missing_in_new: int = 0
    skipped_fk: int = 0
    inserted: int = 0


def load_old_url_from_env_file(repo_root: Path) -> str:
    env_file = repo_root / ".env"
    if not env_file.exists():
        raise RuntimeError(f"Missing .env file: {env_file}")
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("DATABASE_URL was not found in .env")


def get_columns(conn: psycopg2.extensions.connection, table: str) -> List[str]:
    query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
    """
    with conn.cursor() as cur:
        cur.execute(query, (table,))
        return [row[0] for row in cur.fetchall()]


def get_id_set(conn: psycopg2.extensions.connection, table: str, id_col: str = "id") -> Set[Any]:
    query = sql.SQL("SELECT {} FROM {}").format(sql.Identifier(id_col), sql.Identifier(table))
    with conn.cursor() as cur:
        cur.execute(query)
        return {row[0] for row in cur.fetchall()}


def fetch_rows_by_ids(
    conn: psycopg2.extensions.connection,
    table: str,
    pk_col: str,
    columns: Sequence[str],
    ids: Sequence[Any],
) -> List[Tuple[Any, ...]]:
    if not ids:
        return []
    query = sql.SQL("SELECT {} FROM {} WHERE {}::text = ANY(%s)").format(
        sql.SQL(", ").join(sql.Identifier(c) for c in columns),
        sql.Identifier(table),
        sql.Identifier(pk_col),
    )
    with conn.cursor() as cur:
        cur.execute(query, ([str(v) for v in ids],))
        return cur.fetchall()


def build_insert_statement(table: str, columns: Sequence[str], pk_col: str) -> sql.Composed:
    return sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT ({}) DO NOTHING").format(
        sql.Identifier(table),
        sql.SQL(", ").join(sql.Identifier(c) for c in columns),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
        sql.Identifier(pk_col),
    )


def adapt_value_for_insert(value: Any) -> Any:
    if isinstance(value, dict):
        return Json(value)
    return value


def can_insert_row(table: str, row_map: Dict[str, Any], refs: Dict[str, Set[Any]]) -> bool:
    if table == "personas":
        owner_user_id = row_map.get("owner_user_id")
        return owner_user_id is None or owner_user_id in refs["users"]
    if table == "chats":
        return (
            row_map.get("user_id") in refs["users"]
            and row_map.get("persona_id") in refs["personas"]
        )
    if table == "payment_transactions":
        return row_map.get("user_id") in refs["users"]
    if table == "chat_purchases":
        chat_id = row_map.get("chat_id")
        return (
            row_map.get("user_id") in refs["users"]
            and (chat_id is None or chat_id in refs["chats"])
        )
    return True


def tier_rank(tier: Any) -> int:
    key = (tier or "free").strip().lower() if isinstance(tier, str) else "free"
    return TIER_RANK.get(key, 0)


def max_dt(a: datetime | None, b: datetime | None) -> datetime | None:
    if a is None:
        return b
    if b is None:
        return a
    return a if a >= b else b


def sync_missing_rows(
    old_conn: psycopg2.extensions.connection,
    new_conn: psycopg2.extensions.connection,
    apply: bool,
) -> Dict[str, InsertStats]:
    stats: Dict[str, InsertStats] = {t: InsertStats(table=t) for t in TABLE_ORDER}

    refs = {
        "users": get_id_set(new_conn, "users"),
        "personas": get_id_set(new_conn, "personas"),
        "chats": get_id_set(new_conn, "chats"),
    }

    for table in TABLE_ORDER:
        pk_col = PK_BY_TABLE[table]
        cols_old = get_columns(old_conn, table)
        cols_new = get_columns(new_conn, table)
        if cols_old != cols_new:
            raise RuntimeError(
                f"Column mismatch for table '{table}'.\nold={cols_old}\nnew={cols_new}"
            )

        old_ids = get_id_set(old_conn, table, pk_col)
        new_ids = get_id_set(new_conn, table, pk_col)
        missing_ids = sorted(old_ids - new_ids)
        table_stats = stats[table]
        table_stats.missing_in_new = len(missing_ids)

        if not missing_ids:
            continue

        rows = fetch_rows_by_ids(old_conn, table, pk_col, cols_old, missing_ids)
        insert_sql = build_insert_statement(table, cols_old, pk_col)

        with new_conn.cursor() as cur:
            for row in rows:
                row_map = dict(zip(cols_old, row))
                if not can_insert_row(table, row_map, refs):
                    table_stats.skipped_fk += 1
                    continue

                if apply:
                    adapted_row = tuple(adapt_value_for_insert(v) for v in row)
                    cur.execute(insert_sql, adapted_row)
                    if cur.rowcount > 0:
                        table_stats.inserted += 1
                else:
                    table_stats.inserted += 1

                if table == "users":
                    refs["users"].add(row_map["id"])
                elif table == "personas":
                    refs["personas"].add(row_map["id"])
                elif table == "chats":
                    refs["chats"].add(row_map["id"])

    return stats


def sync_premium_entitlements(
    old_conn: psycopg2.extensions.connection,
    new_conn: psycopg2.extensions.connection,
    apply: bool,
) -> Tuple[int, int]:
    """
    Returns (users_needing_patch, users_patched_or_would_patch)
    """
    query = """
        SELECT id, is_premium, premium_until, premium_tier, last_daily_token_addition
        FROM users
    """
    with old_conn.cursor() as cur_old:
        cur_old.execute(query)
        old_map = {row[0]: row[1:] for row in cur_old.fetchall()}
    with new_conn.cursor() as cur_new:
        cur_new.execute(query)
        new_map = {row[0]: row[1:] for row in cur_new.fetchall()}

    shared_ids = set(old_map) & set(new_map)

    to_patch: List[Tuple[Any, bool, datetime | None, str, datetime | None]] = []
    for user_id in shared_ids:
        old_is, old_until, old_tier, old_last_daily = old_map[user_id]
        new_is, new_until, new_tier, new_last_daily = new_map[user_id]

        target_is = bool(old_is or new_is)
        target_until = max_dt(old_until, new_until)
        target_tier = old_tier if tier_rank(old_tier) > tier_rank(new_tier) else new_tier
        target_last_daily = max_dt(old_last_daily, new_last_daily)

        needs_patch = (
            target_is != new_is
            or target_until != new_until
            or (target_tier or "free") != (new_tier or "free")
            or target_last_daily != new_last_daily
        )
        if needs_patch:
            to_patch.append((user_id, target_is, target_until, target_tier, target_last_daily))

    if apply and to_patch:
        update_sql = """
            UPDATE users
            SET
                is_premium = %s,
                premium_until = %s,
                premium_tier = %s,
                last_daily_token_addition = %s
            WHERE id = %s
        """
        with new_conn.cursor() as cur:
            for user_id, target_is, target_until, target_tier, target_last_daily in to_patch:
                cur.execute(
                    update_sql,
                    (target_is, target_until, target_tier, target_last_daily, user_id),
                )

    return (len(to_patch), len(to_patch))


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync missing core rows old DB -> new DB")
    parser.add_argument("--old-url", default=None, help="Old/source PostgreSQL URL")
    parser.add_argument("--new-url", required=True, help="New/target PostgreSQL URL")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes. Default is dry run.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    old_url = args.old_url or load_old_url_from_env_file(repo_root)
    new_url = args.new_url

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"[{mode}] Starting core delta sync old -> new")

    with psycopg2.connect(old_url) as old_conn, psycopg2.connect(new_url) as new_conn:
        old_conn.autocommit = False
        new_conn.autocommit = False

        insert_stats = sync_missing_rows(old_conn, new_conn, apply=args.apply)
        users_need_patch, users_patched = sync_premium_entitlements(
            old_conn, new_conn, apply=args.apply
        )

        if args.apply:
            new_conn.commit()
        else:
            new_conn.rollback()

    print("\nTable sync results:")
    for table in TABLE_ORDER:
        st = insert_stats[table]
        print(
            f"- {table}: missing_in_new={st.missing_in_new}, "
            f"insertable={st.inserted}, skipped_fk={st.skipped_fk}"
        )

    print("\nPremium entitlement patch:")
    print(f"- users_needing_patch={users_need_patch}")
    print(f"- users_patched={'(dry-run) ' if not args.apply else ''}{users_patched}")
    print(f"\nCompleted in {mode} mode.")


if __name__ == "__main__":
    main()
