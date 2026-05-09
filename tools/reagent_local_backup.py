#!/usr/bin/env python3
"""
reagent_local_backup.py — 시약장부 로컬 자동 백업 스크립트

보안 원칙:
- 백업은 로컬 ~/Reagent_Backups 에만 저장
- GitHub / Firebase / 외부 전송 없음
- .git, node_modules, .firebase 캐시 제외
- dist / cache / temp 계열 제외
- 개인정보·민감정보 의심 파일 제외
"""

import argparse
import shutil
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

# ── 경로 상수 ──────────────────────────────────────────────────────────────────
HOME = Path.home()
PROJECT_ROOT = HOME / "reagent"
BACKUP_ROOT = HOME / "Reagent_Backups"

# ── 백업 포함 대상 (루트 단일 파일) ────────────────────────────────────────────
INCLUDE_ROOT_FILES = [
    "index.html",
    ".gitignore",
    ".firebaserc",
    "firebase.json",
    "deploy_reagent.sh",
    "404.html",
]

# ── 백업 포함 대상 (폴더 — 재귀 복사) ────────────────────────────────────────────
INCLUDE_DIRS = [
    "public",
]

# ── 항상 제외할 폴더명 ────────────────────────────────────────────────────────
EXCLUDE_DIR_NAMES = {
    ".git",
    "node_modules",
    ".firebase",
    "dist",
    "cache",
    "temp",
    ".cache",
    "__pycache__",
}

# ── 항상 제외할 파일명 / 확장자 ───────────────────────────────────────────────
EXCLUDE_FILE_NAMES = {
    ".DS_Store",
    "Thumbs.db",
}

EXCLUDE_FILE_SUFFIXES = {
    ".log",
    ".tmp",
    ".bak",
}

# ── 개인정보 의심 파일명 패턴 (소문자 포함 여부 검사) ─────────────────────────
SENSITIVE_PATTERNS = [
    "patient", "환자", "주민", "ssn", "personal",
]

DEFAULT_RETENTION_DAYS = 60


# ── 유틸 ───────────────────────────────────────────────────────────────────────

def human_size(num_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes //= 1024
    return f"{num_bytes:.1f} TB"


def is_sensitive_file(path: Path) -> bool:
    name_lower = path.name.lower()
    return any(pat in name_lower for pat in SENSITIVE_PATTERNS)


def should_exclude_path(rel: Path) -> Optional[str]:
    """제외 이유 반환. None 이면 포함."""
    for part in rel.parts[:-1]:  # 폴더 부분만 검사
        if part in EXCLUDE_DIR_NAMES:
            return f"[제외폴더] {rel}"
    name = rel.name
    if name in EXCLUDE_FILE_NAMES:
        return f"[제외파일] {rel}"
    if rel.suffix.lower() in EXCLUDE_FILE_SUFFIXES:
        return f"[제외확장자] {rel}"
    if is_sensitive_file(rel):
        return f"[민감의심] {rel}"
    return None


# ── 파일 수집 ─────────────────────────────────────────────────────────────────

def collect_files() -> Tuple[List[Tuple[Path, Path]], List[str]]:
    """
    Returns:
        included: list of (src_absolute, relative_to_project_root)
        skipped:  list of human-readable skip reasons
    """
    included: List[Tuple[Path, Path]] = []
    skipped: List[str] = []

    # 루트 단일 파일
    for name in INCLUDE_ROOT_FILES:
        src = PROJECT_ROOT / name
        if src.exists():
            included.append((src, Path(name)))
        else:
            skipped.append(f"[없음] {name}")

    # 폴더 재귀
    for dir_name in INCLUDE_DIRS:
        src_dir = PROJECT_ROOT / dir_name
        if not src_dir.exists():
            skipped.append(f"[없음] {dir_name}/")
            continue
        for f in sorted(src_dir.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(PROJECT_ROOT)
            reason = should_exclude_path(rel)
            if reason:
                skipped.append(reason)
                continue
            included.append((f, rel))

    return included, skipped


# ── 백업 실행 ─────────────────────────────────────────────────────────────────

def run_backup(dry_run: bool = False, retention_days: int = DEFAULT_RETENTION_DAYS) -> int:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = BACKUP_ROOT / f"reagent-backup-{timestamp}"
    zip_path = BACKUP_ROOT / f"reagent-backup-{timestamp}.zip"

    print("=" * 60)
    print("시약장부 로컬 백업")
    print(f"  실행 시각  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  프로젝트   : {PROJECT_ROOT}")
    print(f"  백업 루트  : {BACKUP_ROOT}")
    if dry_run:
        print("  [DRY-RUN 모드 — 실제 복사/삭제 없음]")
    print("=" * 60)

    if not dry_run:
        BACKUP_ROOT.mkdir(parents=True, exist_ok=True)

    included, skipped = collect_files()

    print(f"\n[포함 대상] {len(included)}개 파일")
    for _, rel in included:
        print(f"  + {rel}")

    print(f"\n[제외 대상] {len(skipped)}개")
    for reason in skipped:
        print(f"  - {reason}")

    if dry_run:
        print("\n[DRY-RUN] 백업을 실제로 수행하지 않았습니다.")
        return 0

    # 파일 복사
    total_bytes = 0
    copied = 0
    errors = []

    for src, rel in included:
        dst = backup_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src, dst)
            total_bytes += src.stat().st_size
            copied += 1
        except Exception as e:
            errors.append(f"{rel}: {e}")

    # BACKUP_MANIFEST.txt
    manifest_lines = [
        "BACKUP_MANIFEST",
        "=" * 50,
        f"백업 실행 시각 : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"프로젝트 경로  : {PROJECT_ROOT}",
        f"백업 폴더      : {backup_dir}",
        f"zip 경로       : {zip_path}",
        "",
        "[포함 대상]",
    ]
    for _, rel in included:
        manifest_lines.append(f"  + {rel}")
    manifest_lines += ["", "[제외 대상]"]
    for reason in skipped:
        manifest_lines.append(f"  - {reason}")
    manifest_lines += [
        "",
        f"복사된 파일 수 : {copied}개",
        f"총 용량        : {human_size(total_bytes)}",
        "",
        "[보안 확인]",
        "  GitHub 업로드  : 없음",
        "  Firebase 업로드: 없음",
        "  외부 전송      : 없음",
        "  .git 제외      : 확인",
        "  .firebase 캐시 제외: 확인",
        "  node_modules 제외: 확인",
        "  개인정보 의심 파일 제외: 확인",
    ]
    if errors:
        manifest_lines += ["", "[오류]"]
        for e in errors:
            manifest_lines.append(f"  ! {e}")

    (backup_dir / "BACKUP_MANIFEST.txt").write_text(
        "\n".join(manifest_lines), encoding="utf-8"
    )

    # zip 압축
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for f in sorted(backup_dir.rglob("*")):
                if f.is_file():
                    zf.write(f, f.relative_to(backup_dir))
        zip_size = zip_path.stat().st_size
    except Exception as e:
        print(f"\n[오류] zip 생성 실패: {e}", file=sys.stderr)
        zip_size = 0

    print(f"\n[완료]")
    print(f"  백업 폴더  : {backup_dir}")
    print(f"  zip 파일   : {zip_path}")
    print(f"  복사 파일  : {copied}개 / {human_size(total_bytes)}")
    print(f"  zip 크기   : {human_size(zip_size)}")

    if errors:
        print(f"\n[경고] {len(errors)}개 오류 발생:")
        for e in errors:
            print(f"  ! {e}", file=sys.stderr)

    cleanup_old_backups(retention_days)
    return 0 if not errors else 1


# ── 오래된 백업 정리 ──────────────────────────────────────────────────────────

def cleanup_old_backups(retention_days: int) -> None:
    cutoff = datetime.now() - timedelta(days=retention_days)
    print(f"\n[정리] {retention_days}일 초과 백업 정리 중 (기준: {cutoff.strftime('%Y-%m-%d')})")

    removed = 0
    for entry in sorted(BACKUP_ROOT.iterdir()):
        # 안전 확인: 반드시 BACKUP_ROOT 내부
        try:
            entry.resolve().relative_to(BACKUP_ROOT.resolve())
        except ValueError:
            print(f"  [경고] 경로 이상 — 삭제 건너뜀: {entry}", file=sys.stderr)
            continue

        name = entry.name
        if not name.startswith("reagent-backup-"):
            continue

        try:
            date_part = name.replace("reagent-backup-", "").replace(".zip", "")
            entry_dt = datetime.strptime(date_part, "%Y%m%d-%H%M%S")
        except ValueError:
            continue

        if entry_dt < cutoff:
            try:
                if entry.is_dir():
                    shutil.rmtree(entry)
                else:
                    entry.unlink()
                print(f"  [삭제] {name}")
                removed += 1
            except Exception as e:
                print(f"  [경고] 삭제 실패 {name}: {e}", file=sys.stderr)

    if removed == 0:
        print("  삭제 대상 없음.")
    else:
        print(f"  {removed}개 항목 삭제 완료.")


# ── 진입점 ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="시약장부 로컬 자동 백업 (로컬 전용 — 외부 전송 없음)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 복사/삭제 없이 백업 대상과 제외 대상만 출력",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        metavar="N",
        help=f"오래된 백업 보존 기간 (기본값: {DEFAULT_RETENTION_DAYS}일)",
    )
    args = parser.parse_args()
    return run_backup(dry_run=args.dry_run, retention_days=args.retention_days)


if __name__ == "__main__":
    sys.exit(main())
