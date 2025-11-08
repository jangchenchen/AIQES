"""数据库备份和恢复工具"""

from __future__ import annotations

import gzip
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional


class BackupManager:
    """数据库备份管理器"""

    def __init__(
        self,
        db_path: Path,
        backup_dir: Path,
        max_backups: int = 30,
        compress: bool = True,
    ):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.max_backups = max_backups
        self.compress = compress
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, description: str = "") -> Path:
        """创建数据库备份"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"

        if description:
            safe_desc = "".join(c for c in description if c.isalnum() or c in "._- ")
            backup_name += f"_{safe_desc}"

        backup_path = self.backup_dir / f"{backup_name}.db"

        print(f"🔄 创建备份: {backup_path.name}")

        # 使用 SQLite 的备份 API（在线备份，不锁定数据库）
        try:
            source_conn = sqlite3.connect(self.db_path)
            backup_conn = sqlite3.connect(backup_path)

            with backup_conn:
                source_conn.backup(backup_conn)

            source_conn.close()
            backup_conn.close()

            # 压缩备份
            if self.compress:
                compressed_path = self._compress_backup(backup_path)
                backup_path.unlink()  # 删除未压缩版本
                backup_path = compressed_path

            file_size = backup_path.stat().st_size
            print(f"✅ 备份成功: {backup_path.name} ({file_size // 1024}KB)")

            # 清理旧备份
            self._cleanup_old_backups()

            return backup_path

        except Exception as e:
            print(f"❌ 备份失败: {e}")
            if backup_path.exists():
                backup_path.unlink()
            raise

    def _compress_backup(self, backup_path: Path) -> Path:
        """压缩备份文件"""
        compressed_path = backup_path.with_suffix(".db.gz")

        with open(backup_path, "rb") as f_in:
            with gzip.open(compressed_path, "wb", compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)

        return compressed_path

    def _decompress_backup(self, compressed_path: Path, output_path: Path) -> None:
        """解压备份文件"""
        with gzip.open(compressed_path, "rb") as f_in:
            with open(output_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

    def restore_backup(
        self, backup_path: Path, target_path: Optional[Path] = None
    ) -> None:
        """恢复备份"""
        if target_path is None:
            target_path = self.db_path

        print(f"🔄 恢复备份: {backup_path.name} -> {target_path.name}")

        # 创建当前数据库的备份
        if target_path.exists():
            safety_backup = self.create_backup(description="pre_restore")
            print(f"💾 已创建安全备份: {safety_backup.name}")

        try:
            # 解压（如果需要）
            if backup_path.suffix == ".gz":
                temp_path = self.backup_dir / "temp_restore.db"
                self._decompress_backup(backup_path, temp_path)
                backup_path = temp_path

            # 验证备份完整性
            if not self._verify_backup(backup_path):
                raise ValueError("备份文件损坏或无效")

            # 恢复数据库
            shutil.copy2(backup_path, target_path)

            # 清理临时文件
            if backup_path.name == "temp_restore.db":
                backup_path.unlink()

            print(f"✅ 恢复成功")

        except Exception as e:
            print(f"❌ 恢复失败: {e}")
            raise

    def _verify_backup(self, backup_path: Path) -> bool:
        """验证备份完整性"""
        try:
            conn = sqlite3.connect(backup_path)
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            conn.close()
            return result == "ok"
        except Exception as e:
            print(f"⚠️  备份验证失败: {e}")
            return False

    def list_backups(self) -> List[Path]:
        """列出所有备份"""
        backups = []

        for pattern in ["backup_*.db", "backup_*.db.gz"]:
            backups.extend(self.backup_dir.glob(pattern))

        return sorted(backups, key=lambda p: p.stat().st_mtime, reverse=True)

    def _cleanup_old_backups(self) -> None:
        """清理旧备份"""
        backups = self.list_backups()

        if len(backups) <= self.max_backups:
            return

        to_delete = backups[self.max_backups :]
        print(f"🗑️  清理 {len(to_delete)} 个旧备份...")

        for backup in to_delete:
            backup.unlink()
            print(f"   删除: {backup.name}")

    def get_backup_info(self) -> List[dict]:
        """获取备份信息"""
        backups = self.list_backups()
        info = []

        for backup in backups:
            stat = backup.stat()
            info.append(
                {
                    "name": backup.name,
                    "path": backup,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime),
                    "age_days": (
                        datetime.now() - datetime.fromtimestamp(stat.st_mtime)
                    ).days,
                }
            )

        return info

    def auto_backup(self, interval_hours: int = 24) -> None:
        """自动备份（如果距离上次备份超过指定时间）"""
        backups = self.list_backups()

        if not backups:
            # 没有备份，立即创建
            self.create_backup(description="auto")
            return

        latest_backup = backups[0]
        latest_time = datetime.fromtimestamp(latest_backup.stat().st_mtime)
        age = datetime.now() - latest_time

        if age > timedelta(hours=interval_hours):
            print(
                f"⏰ 距上次备份已过 {age.total_seconds() / 3600:.1f} 小时，执行自动备份..."
            )
            self.create_backup(description="auto")
        else:
            print(f"✓ 备份仍然新鲜（{age.total_seconds() / 3600:.1f} 小时前）")


def scheduled_backup(
    db_path: Path,
    backup_dir: Path,
    interval_hours: int = 24,
) -> None:
    """定时备份任务"""
    import threading
    import time

    def backup_loop():
        manager = BackupManager(db_path, backup_dir)

        while True:
            try:
                manager.auto_backup(interval_hours)
            except Exception as e:
                print(f"❌ 自动备份失败: {e}")

            time.sleep(3600)  # 每小时检查一次

    thread = threading.Thread(target=backup_loop, daemon=True)
    thread.start()
    print(f"✅ 自动备份线程已启动（间隔: {interval_hours}小时）")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python backup.py create [db_path] [backup_dir]  # 创建备份")
        print("  python backup.py restore <backup_file> [db_path] # 恢复备份")
        print("  python backup.py list [backup_dir]               # 列出备份")
        print("  python backup.py cleanup [backup_dir]            # 清理旧备份")
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        db_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/records.db")
        backup_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("data/backups")

        manager = BackupManager(db_path, backup_dir)
        manager.create_backup(description="manual")

    elif command == "restore":
        if len(sys.argv) < 3:
            print("❌ 请指定备份文件")
            sys.exit(1)

        backup_file = Path(sys.argv[2])
        db_path = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("data/records.db")

        manager = BackupManager(db_path, backup_file.parent)
        manager.restore_backup(backup_file)

    elif command == "list":
        backup_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/backups")
        manager = BackupManager(Path("data/records.db"), backup_dir)

        backups = manager.get_backup_info()
        print("\n" + "=" * 80)
        print("可用备份")
        print("=" * 80)

        for backup in backups:
            size_kb = backup["size"] // 1024
            age = backup["age_days"]
            print(f"{backup['name']:<50} {size_kb:>8}KB  {age:>3}天前")

        print("=" * 80 + "\n")

    elif command == "cleanup":
        backup_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/backups")
        manager = BackupManager(Path("data/records.db"), backup_dir, max_backups=7)
        manager._cleanup_old_backups()

    else:
        print(f"❌ 未知命令: {command}")
        sys.exit(1)
