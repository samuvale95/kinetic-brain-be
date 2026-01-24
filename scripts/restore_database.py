#!/usr/bin/env python3
"""
Database restore script for Kinetic Brain
Restores database from backup file
"""
import os
import sys
import subprocess
import gzip
from pathlib import Path
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from loguru import logger

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings


class DatabaseRestore:
    """Database restore manager"""
    
    def __init__(self, s3_bucket: Optional[str] = None, s3_prefix: str = "backups/"):
        self.s3_bucket = s3_bucket or os.getenv("S3_BACKUP_BUCKET")
        self.s3_prefix = s3_prefix
        
        # Initialize S3 client if bucket is configured
        self.s3_client = None
        if self.s3_bucket:
            try:
                self.s3_client = boto3.client('s3')
                logger.info(f"S3 restore configured: bucket={self.s3_bucket}, prefix={self.s3_prefix}")
            except Exception as e:
                logger.warning(f"Failed to initialize S3 client: {e}")
                self.s3_client = None
    
    def _get_database_url(self) -> str:
        """Get database URL from settings"""
        return settings.database_url
    
    def _parse_database_url(self, url: str) -> dict:
        """Parse database URL into components"""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        return {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "database": parsed.path.lstrip('/'),
            "user": parsed.username,
            "password": parsed.password
        }
    
    def _download_from_s3(self, s3_key: str, local_path: Path) -> bool:
        """Download backup from S3"""
        if not self.s3_client:
            return False
        
        try:
            logger.info(f"Downloading from S3: s3://{self.s3_bucket}/{s3_key}")
            self.s3_client.download_file(self.s3_bucket, s3_key, str(local_path))
            logger.info(f"Download complete: {local_path}")
            return True
        except ClientError as e:
            logger.error(f"Failed to download from S3: {e}")
            return False
    
    def _decompress_backup(self, compressed_path: Path) -> Path:
        """Decompress backup file"""
        decompressed_path = compressed_path.with_suffix('.sql')
        
        logger.info(f"Decompressing backup: {compressed_path}")
        
        with gzip.open(compressed_path, 'rb') as f_in:
            with open(decompressed_path, 'wb') as f_out:
                f_out.write(f_in.read())
        
        logger.info(f"Decompression complete: {decompressed_path}")
        return decompressed_path
    
    def restore(self, backup_path: str, drop_existing: bool = False) -> bool:
        """
        Restore database from backup file
        
        Args:
            backup_path: Path to backup file (local or S3 key)
            drop_existing: If True, drop existing database before restore
        
        Returns:
            True if restore successful, False otherwise
        """
        backup_file = Path(backup_path)
        local_backup = None
        
        # Check if it's an S3 key
        if not backup_file.exists() and self.s3_client:
            # Try to download from S3
            s3_key = backup_path if backup_path.startswith(self.s3_prefix) else f"{self.s3_prefix}{backup_path}"
            local_backup = Path(f"/tmp/{backup_file.name}")
            if not self._download_from_s3(s3_key, local_backup):
                logger.error(f"Backup file not found: {backup_path}")
                return False
            backup_file = local_backup
        
        if not backup_file.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        db_config = self._parse_database_url(self._get_database_url())
        
        # Decompress if needed
        if backup_file.suffix == '.gz':
            logger.info("Decompressing backup file...")
            decompressed_file = self._decompress_backup(backup_file)
            sql_file = decompressed_file
            cleanup_decompressed = True
        else:
            sql_file = backup_file
            cleanup_decompressed = False
        
        try:
            # Set PGPASSWORD environment variable
            env = os.environ.copy()
            if db_config["password"]:
                env["PGPASSWORD"] = db_config["password"]
            
            # Drop existing database if requested
            if drop_existing:
                logger.warning(f"⚠️  Dropping existing database: {db_config['database']}")
                drop_cmd = [
                    "psql",
                    "-h", db_config["host"],
                    "-p", str(db_config["port"]),
                    "-U", db_config["user"],
                    "-d", "postgres",  # Connect to postgres database to drop target
                    "-c", f"DROP DATABASE IF EXISTS {db_config['database']};"
                ]
                
                subprocess.run(
                    drop_cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                # Recreate database
                create_cmd = [
                    "psql",
                    "-h", db_config["host"],
                    "-p", str(db_config["port"]),
                    "-U", db_config["user"],
                    "-d", "postgres",
                    "-c", f"CREATE DATABASE {db_config['database']};"
                ]
                
                subprocess.run(
                    create_cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=True
                )
            
            # Restore database
            logger.info(f"Restoring database from: {sql_file}")
            restore_cmd = [
                "psql",
                "-h", db_config["host"],
                "-p", str(db_config["port"]),
                "-U", db_config["user"],
                "-d", db_config["database"],
                "-f", str(sql_file)
            ]
            
            result = subprocess.run(
                restore_cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info("✅ Database restore completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Restore failed: {e.stderr}")
            return False
        except FileNotFoundError:
            logger.error("psql not found. Please install PostgreSQL client tools.")
            return False
        finally:
            # Cleanup decompressed file if we created it
            if cleanup_decompressed and sql_file.exists():
                sql_file.unlink()
                logger.info(f"Cleaned up temporary file: {sql_file}")
            
            # Cleanup downloaded S3 file
            if local_backup and local_backup.exists():
                local_backup.unlink()
                logger.info(f"Cleaned up downloaded file: {local_backup}")


def list_backups(backup_dir: str = "backups", s3_bucket: Optional[str] = None, s3_prefix: str = "backups/"):
    """List available backups"""
    backups = []
    
    # List local backups
    backup_path = Path(backup_dir)
    if backup_path.exists():
        for backup_file in sorted(backup_path.glob("backup_*.sql.gz"), reverse=True):
            size_mb = backup_file.stat().st_size / 1024 / 1024
            backups.append({
                "type": "local",
                "path": str(backup_file),
                "name": backup_file.name,
                "size_mb": size_mb
            })
    
    # List S3 backups
    if s3_bucket:
        try:
            s3_client = boto3.client('s3')
            response = s3_client.list_objects_v2(
                Bucket=s3_bucket,
                Prefix=s3_prefix
            )
            
            if 'Contents' in response:
                for obj in sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True):
                    key = obj['Key']
                    backups.append({
                        "type": "s3",
                        "path": key,
                        "name": key.replace(s3_prefix, ''),
                        "size_mb": obj['Size'] / 1024 / 1024,
                        "last_modified": obj['LastModified'].isoformat()
                    })
        except Exception as e:
            logger.warning(f"Failed to list S3 backups: {e}")
    
    return backups


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Restore Kinetic Brain database from backup")
    parser.add_argument("backup_path", nargs="?", help="Path to backup file (local or S3 key)")
    parser.add_argument("--backup-dir", help="Backup directory for listing", default="backups")
    parser.add_argument("--s3-bucket", help="S3 bucket for backups", default=None)
    parser.add_argument("--s3-prefix", help="S3 prefix for backups", default="backups/")
    parser.add_argument("--drop-existing", action="store_true", help="Drop existing database before restore")
    parser.add_argument("--list", action="store_true", help="List available backups")
    
    args = parser.parse_args()
    
    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    if args.list:
        backups = list_backups(args.backup_dir, args.s3_bucket, args.s3_prefix)
        if backups:
            print("\nAvailable backups:")
            print("-" * 80)
            for backup in backups:
                print(f"[{backup['type'].upper()}] {backup['name']} ({backup['size_mb']:.2f} MB)")
                if 'last_modified' in backup:
                    print(f"  Last modified: {backup['last_modified']}")
        else:
            print("No backups found")
        return
    
    if not args.backup_path:
        parser.error("backup_path is required (or use --list to see available backups)")
    
    try:
        restore_manager = DatabaseRestore(
            s3_bucket=args.s3_bucket,
            s3_prefix=args.s3_prefix
        )
        
        if restore_manager.restore(args.backup_path, drop_existing=args.drop_existing):
            logger.info("✅ Restore process completed successfully")
        else:
            logger.error("❌ Restore failed")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Restore failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
