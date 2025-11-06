"""数据库迁移工具"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


class Migration:
    """单个迁移"""

    def __init__(
        self,
        version: str,
        description: str,
        up_sql: str,
        down_sql: str = "",
    ):
        self.version = version
        self.description = description
        self.up_sql = up_sql
        self.down_sql = down_sql
        self.checksum = self._calculate_checksum()

    def _calculate_checksum(self) -> str:
        """计算迁移的校验和"""
        content = f"{self.version}{self.up_sql}{self.down_sql}"
        return hashlib.sha256(content.encode()).hexdigest()


class MigrationManager:
    """数据库迁移管理器"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._ensure_migration_table()

    def _ensure_migration_table(self) -> None:
        """确保迁移记录表存在"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    execution_time_ms INTEGER
                )
            """)
            conn.commit()

    def get_applied_migrations(self) -> List[Tuple[str, str]]:
        """获取已应用的迁移"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT version, checksum
                FROM schema_migrations
                ORDER BY version
            """)
            return cursor.fetchall()

    def is_applied(self, version: str) -> bool:
        """检查迁移是否已应用"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?",
                (version,)
            )
            return cursor.fetchone() is not None

    def apply_migration(self, migration: Migration) -> None:
        """应用迁移"""
        if self.is_applied(migration.version):
            print(f"⏭️  跳过已应用的迁移: {migration.version}")
            return

        print(f"🔄 应用迁移: {migration.version} - {migration.description}")

        start_time = datetime.utcnow()

        with sqlite3.connect(self.db_path) as conn:
            try:
                # 开始事务
                conn.execute("BEGIN")

                # 执行迁移
                conn.executescript(migration.up_sql)

                # 记录迁移
                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                conn.execute("""
                    INSERT INTO schema_migrations
                    (version, description, checksum, applied_at, execution_time_ms)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    migration.version,
                    migration.description,
                    migration.checksum,
                    datetime.utcnow().isoformat() + "Z",
                    int(execution_time),
                ))

                conn.commit()
                print(f"✅ 迁移成功 ({execution_time:.0f}ms)")

            except Exception as e:
                conn.rollback()
                print(f"❌ 迁移失败: {e}")
                raise

    def rollback_migration(self, migration: Migration) -> None:
        """回滚迁移"""
        if not self.is_applied(migration.version):
            print(f"⏭️  迁移未应用，无需回滚: {migration.version}")
            return

        if not migration.down_sql:
            raise ValueError(f"迁移 {migration.version} 没有定义回滚脚本")

        print(f"⏪ 回滚迁移: {migration.version} - {migration.description}")

        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("BEGIN")

                # 执行回滚
                conn.executescript(migration.down_sql)

                # 删除迁移记录
                conn.execute(
                    "DELETE FROM schema_migrations WHERE version = ?",
                    (migration.version,)
                )

                conn.commit()
                print(f"✅ 回滚成功")

            except Exception as e:
                conn.rollback()
                print(f"❌ 回滚失败: {e}")
                raise

    def verify_migrations(self, migrations: List[Migration]) -> bool:
        """验证迁移完整性"""
        print("🔍 验证迁移完整性...")

        applied = dict(self.get_applied_migrations())
        all_valid = True

        for migration in migrations:
            if migration.version in applied:
                stored_checksum = applied[migration.version]
                if stored_checksum != migration.checksum:
                    print(f"❌ 迁移校验和不匹配: {migration.version}")
                    print(f"   预期: {migration.checksum}")
                    print(f"   实际: {stored_checksum}")
                    all_valid = False

        if all_valid:
            print("✅ 所有迁移完整性验证通过")
        else:
            print("❌ 迁移完整性验证失败")

        return all_valid

    def get_migration_status(self, migrations: List[Migration]) -> None:
        """显示迁移状态"""
        applied = {version for version, _ in self.get_applied_migrations()}

        print("\n" + "=" * 70)
        print("数据库迁移状态")
        print("=" * 70)

        for migration in migrations:
            status = "✅ 已应用" if migration.version in applied else "⏸️  待应用"
            print(f"{status} | {migration.version} | {migration.description}")

        print("=" * 70 + "\n")


# 定义所有迁移
MIGRATIONS: List[Migration] = [
    Migration(
        version="001_initial_schema",
        description="初始化数据库结构",
        up_sql="""
            CREATE TABLE IF NOT EXISTS answer_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                question_type TEXT NOT NULL,
                question_prompt TEXT NOT NULL,
                user_answer TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                plain_explanation TEXT,
                knowledge_source TEXT,
                mode TEXT,
                extra TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_answer_history_session
                ON answer_history(session_id);
            CREATE INDEX IF NOT EXISTS idx_answer_history_timestamp
                ON answer_history(timestamp);
            CREATE INDEX IF NOT EXISTS idx_answer_history_type
                ON answer_history(question_type);

            CREATE TABLE IF NOT EXISTS wrong_questions (
                identifier TEXT PRIMARY KEY,
                question_type TEXT NOT NULL,
                question_prompt TEXT NOT NULL,
                question_data TEXT NOT NULL,
                last_plain_explanation TEXT,
                last_wrong_at TEXT NOT NULL,
                wrong_count INTEGER DEFAULT 1
            );

            CREATE INDEX IF NOT EXISTS idx_wrong_questions_type
                ON wrong_questions(question_type);
            CREATE INDEX IF NOT EXISTS idx_wrong_questions_timestamp
                ON wrong_questions(last_wrong_at);
        """,
        down_sql="""
            DROP INDEX IF EXISTS idx_wrong_questions_timestamp;
            DROP INDEX IF EXISTS idx_wrong_questions_type;
            DROP TABLE IF EXISTS wrong_questions;

            DROP INDEX IF EXISTS idx_answer_history_type;
            DROP INDEX IF EXISTS idx_answer_history_timestamp;
            DROP INDEX IF EXISTS idx_answer_history_session;
            DROP TABLE IF EXISTS answer_history;
        """
    ),

    Migration(
        version="002_add_performance_indexes",
        description="添加性能优化索引",
        up_sql="""
            CREATE INDEX IF NOT EXISTS idx_answer_history_correct
                ON answer_history(is_correct);
            CREATE INDEX IF NOT EXISTS idx_answer_history_composite
                ON answer_history(session_id, timestamp);
        """,
        down_sql="""
            DROP INDEX IF EXISTS idx_answer_history_composite;
            DROP INDEX IF EXISTS idx_answer_history_correct;
        """
    ),

    Migration(
        version="003_add_user_tracking",
        description="添加用户追踪字段",
        up_sql="""
            ALTER TABLE answer_history ADD COLUMN user_ip TEXT;
            ALTER TABLE answer_history ADD COLUMN user_agent TEXT;

            CREATE INDEX IF NOT EXISTS idx_answer_history_user_ip
                ON answer_history(user_ip);
        """,
        down_sql="""
            -- SQLite 不支持 DROP COLUMN，需要重建表
            -- 这里仅作示例，实际使用时需要迁移数据
            DROP INDEX IF EXISTS idx_answer_history_user_ip;
        """
    ),

    Migration(
        version="004_add_ai_metrics",
        description="添加AI调用指标表",
        up_sql="""
            CREATE TABLE IF NOT EXISTS ai_call_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                operation_type TEXT NOT NULL,
                model_name TEXT,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                latency_ms INTEGER,
                success INTEGER NOT NULL,
                error_message TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_ai_metrics_timestamp
                ON ai_call_metrics(timestamp);
            CREATE INDEX IF NOT EXISTS idx_ai_metrics_success
                ON ai_call_metrics(success);
        """,
        down_sql="""
            DROP INDEX IF EXISTS idx_ai_metrics_success;
            DROP INDEX IF EXISTS idx_ai_metrics_timestamp;
            DROP TABLE IF EXISTS ai_call_metrics;
        """
    ),
]


def run_migrations(db_path: Path) -> None:
    """运行所有待应用的迁移"""
    manager = MigrationManager(db_path)

    # 显示当前状态
    manager.get_migration_status(MIGRATIONS)

    # 验证完整性
    if not manager.verify_migrations(MIGRATIONS):
        raise RuntimeError("迁移完整性验证失败，请检查数据库")

    # 应用迁移
    for migration in MIGRATIONS:
        manager.apply_migration(migration)

    print("\n✅ 所有迁移已应用完成\n")


def rollback_latest(db_path: Path) -> None:
    """回滚最新的迁移"""
    manager = MigrationManager(db_path)
    applied = manager.get_applied_migrations()

    if not applied:
        print("⚠️  没有可回滚的迁移")
        return

    latest_version = applied[-1][0]
    migration = next((m for m in MIGRATIONS if m.version == latest_version), None)

    if not migration:
        raise ValueError(f"找不到迁移定义: {latest_version}")

    manager.rollback_migration(migration)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python migrations.py migrate [db_path]  # 应用迁移")
        print("  python migrations.py rollback [db_path] # 回滚最新迁移")
        print("  python migrations.py status [db_path]   # 查看状态")
        sys.exit(1)

    command = sys.argv[1]
    db_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/records.db")

    if command == "migrate":
        run_migrations(db_path)
    elif command == "rollback":
        rollback_latest(db_path)
    elif command == "status":
        manager = MigrationManager(db_path)
        manager.get_migration_status(MIGRATIONS)
    else:
        print(f"❌ 未知命令: {command}")
        sys.exit(1)
