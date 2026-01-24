#!/usr/bin/env python3
"""
Database backup script for Kinetic Brain
Creates compressed backups with retention policy
"""
import os
import sys
import subprocess
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from loguru import logger

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings


class DatabaseBackup:
    """Database backup manager"""
    
    def __init__(
        self,
        backup_dir: Optional[str] = None,
        s3_bucket: Optional[str] = None,
        s3_prefix: str = "backups/",
        retention_days: int = 7,
        retention_weeks: int = 4,
        retention_months: int = 12
    ):
        self.backup_dir = Path(backup_dir or os.getenv("BACKUP_DIR", "backups"))
        self.s3_bucket = s3_bucket or os.getenv("S3_BACKUP_BUCKET")
        self.s3_prefix = s3_prefix
        self.retention_days = retention_days
        self.retention_weeks = retention_weeks
        self.retention_months = retention_months
        
        # Create backup directory if it doesn't exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize S3 client if bucket is configured
        self.s3_client = None
        if self.s3_bucket:
            try:
                self.s3_client = boto3.client('s3')
                logger.info(f"S3 backup configured: bucket={self.s3_bucket}, prefix={self.s3_prefix}")
            except Exception as e:
                logger.warning(f"Failed to initialize S3 client: {e}")
                self.s3_client = None
    
    def _get_database_url(self) -> str:
        """Get database URL from settings"""
        return settings.database_url
    
    def _parse_database_url(self, url: str) -> dict:
        """Parse database URL into components"""
        # Format: postgresql://user:password@host:port/database
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        return {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "database": parsed.path.lstrip('/'),
            "user": parsed.username,
            "password": parsed.password
        }
    
    def create_backup(self) -> Path:
        """Create a new database backup"""
        db_config = self._parse_database_url(self._get_database_url())
        
        # Generate backup filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.sql"
        backup_path = self.backup_dir / backup_filename
        
        logger.info(f"Creating database backup: {backup_path}")
        
        # Set PGPASSWORD environment variable
        env = os.environ.copy()
        if db_config["password"]:
            env["PGPASSWORD"] = db_config["password"]
        
        # Run pg_dump
        pg_dump_cmd = [
            "pg_dump",
            "-h", db_config["host"],
            "-p", str(db_config["port"]),
            "-U", db_config["user"],
            "-d", db_config["database"],
            "-F", "plain",  # Plain SQL format
            "-f", str(backup_path)
        ]
        
        try:
            result = subprocess.run(
                pg_dump_cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Backup created successfully: {backup_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"pg_dump failed: {e.stderr}")
            raise
        except FileNotFoundError:
            logger.error("pg_dump not found. Please install PostgreSQL client tools.")
            raise
        
        # Compress backup
        compressed_path = self._compress_backup(backup_path)
        
        # Remove uncompressed backup
        backup_path.unlink()
        
        # Upload to S3 if configured
        if self.s3_client:
            self._upload_to_s3(compressed_path)
        
        return compressed_path
    
    def _compress_backup(self, backup_path: Path) -> Path:
        """Compress backup file using gzip"""
        compressed_path = backup_path.with_suffix('.sql.gz')
        
        logger.info(f"Compressing backup: {compressed_path}")
        
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Get file sizes
        original_size = backup_path.stat().st_size
        compressed_size = compressed_path.stat().st_size
        compression_ratio = (1 - compressed_size / original_size) * 100
        
        logger.info(
            f"Compression complete: {original_size / 1024 / 1024:.2f} MB -> "
            f"{compressed_size / 1024 / 1024:.2f} MB ({compression_ratio:.1f}% reduction)"
        )
        
        return compressed_path
    
    def _upload_to_s3(self, backup_path: Path):
        """Upload backup to S3"""
        if not self.s3_client:
            return
        
        s3_key = f"{self.s3_prefix}{backup_path.name}"
        
        try:
            logger.info(f"Uploading to S3: s3://{self.s3_bucket}/{s3_key}")
            self.s3_client.upload_file(
                str(backup_path),
                self.s3_bucket,
                s3_key,
                ExtraArgs={'ServerSideEncryption': 'AES256'}
            )
            logger.info(f"Upload complete: s3://{self.s3_bucket}/{s3_key}")
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise
    
    def cleanup_old_backups(self):
        """Remove old backups based on retention policy"""
        logger.info("Cleaning up old backups...")
        
        now = datetime.utcnow()
        cutoff_daily = now - timedelta(days=self.retention_days)
        cutoff_weekly = now - timedelta(weeks=self.retention_weeks)
        cutoff_monthly = now - timedelta(days=self.retention_months * 30)
        
        backups = list(self.backup_dir.glob("backup_*.sql.gz"))
        deleted_count = 0
        
        for backup_path in backups:
            # Parse timestamp from filename: backup_YYYYMMDD_HHMMSS.sql.gz
            try:
                timestamp_str = backup_path.stem.replace('.sql', '')
                timestamp_str = timestamp_str.replace('backup_', '')
                backup_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                # Determine if we should keep this backup
                keep = False
                
                # Keep if within daily retention
                if backup_time >= cutoff_daily:
                    keep = True
                # Keep if it's a weekly backup (Sunday) and within weekly retention
                elif backup_time.weekday() == 6 and backup_time >= cutoff_weekly:
                    keep = True
                # Keep if it's a monthly backup (1st of month) and within monthly retention
                elif backup_time.day == 1 and backup_time >= cutoff_monthly:
                    keep = True
                
                if not keep:
                    logger.info(f"Deleting old backup: {backup_path.name}")
                    backup_path.unlink()
                    deleted_count += 1
            except ValueError:
                logger.warning(f"Could not parse timestamp from backup: {backup_path.name}")
                continue
        
        logger.info(f"Cleanup complete: {deleted_count} backups deleted")
        
        # Also cleanup S3 if configured
        if self.s3_client:
            self._cleanup_s3_backups(cutoff_daily, cutoff_weekly, cutoff_monthly)
    
    def _cleanup_s3_backups(self, cutoff_daily, cutoff_weekly, cutoff_monthly):
        """Cleanup old backups from S3"""
        try:
            # List all backups in S3
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=self.s3_prefix
            )
            
            if 'Contents' not in response:
                return
            
            deleted_count = 0
            for obj in response['Contents']:
                key = obj['Key']
                backup_name = key.replace(self.s3_prefix, '')
                
                # Parse timestamp
                try:
                    timestamp_str = backup_name.replace('backup_', '').replace('.sql.gz', '')
                    backup_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    # Determine if we should keep this backup (same logic as local)
                    keep = False
                    if backup_time >= cutoff_daily:
                        keep = True
                    elif backup_time.weekday() == 6 and backup_time >= cutoff_weekly:
                        keep = True
                    elif backup_time.day == 1 and backup_time >= cutoff_monthly:
                        keep = True
                    
                    if not keep:
                        logger.info(f"Deleting old S3 backup: {key}")
                        self.s3_client.delete_object(Bucket=self.s3_bucket, Key=key)
                        deleted_count += 1
                except ValueError:
                    logger.warning(f"Could not parse timestamp from S3 backup: {key}")
                    continue
            
            logger.info(f"S3 cleanup complete: {deleted_count} backups deleted")
        except ClientError as e:
            logger.error(f"Failed to cleanup S3 backups: {e}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Backup Kinetic Brain database")
    parser.add_argument("--backup-dir", help="Backup directory", default=None)
    parser.add_argument("--s3-bucket", help="S3 bucket for backups", default=None)
    parser.add_argument("--s3-prefix", help="S3 prefix for backups", default="backups/")
    parser.add_argument("--retention-days", type=int, default=7, help="Daily backup retention (days)")
    parser.add_argument("--retention-weeks", type=int, default=4, help="Weekly backup retention (weeks)")
    parser.add_argument("--retention-months", type=int, default=12, help="Monthly backup retention (months)")
    parser.add_argument("--cleanup-only", action="store_true", help="Only cleanup old backups, don't create new one")
    
    args = parser.parse_args()
    
    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        "logs/backup.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="INFO",
        rotation="10 MB",
        retention="30 days"
    )
    
    try:
        backup_manager = DatabaseBackup(
            backup_dir=args.backup_dir,
            s3_bucket=args.s3_bucket,
            s3_prefix=args.s3_prefix,
            retention_days=args.retention_days,
            retention_weeks=args.retention_weeks,
            retention_months=args.retention_months
        )
        
        if not args.cleanup_only:
            backup_path = backup_manager.create_backup()
            logger.info(f"✅ Backup completed: {backup_path}")
        
        backup_manager.cleanup_old_backups()
        logger.info("✅ Backup process completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Backup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
