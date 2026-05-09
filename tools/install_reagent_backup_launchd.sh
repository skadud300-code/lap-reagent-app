#!/usr/bin/env bash
# install_reagent_backup_launchd.sh — 시약장부 로컬 자동 백업 launchd 설치
#
# 사용법:
#   bash ~/reagent/tools/install_reagent_backup_launchd.sh
#
# 수동 백업:
#   python3 ~/reagent/tools/reagent_local_backup.py
#
# dry-run 테스트:
#   python3 ~/reagent/tools/reagent_local_backup.py --dry-run

set -euo pipefail

LABEL="com.iny.reagent.backup"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_PLIST="${SCRIPT_DIR}/com.iny.reagent.backup.plist"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
DEST_PLIST="${LAUNCH_AGENTS_DIR}/${LABEL}.plist"
BACKUP_SCRIPT="${SCRIPT_DIR}/reagent_local_backup.py"
BACKUP_ROOT="${HOME}/Reagent_Backups"

echo "============================================================"
echo "시약장부 로컬 자동 백업 — launchd 설치"
echo "  HOME         : ${HOME}"
echo "  스크립트     : ${BACKUP_SCRIPT}"
echo "  plist 대상   : ${DEST_PLIST}"
echo "  백업 루트    : ${BACKUP_ROOT}"
echo "============================================================"

# 1. Python 스크립트 실행 권한 부여
echo ""
echo "[1] reagent_local_backup.py 실행 권한 설정..."
chmod +x "${BACKUP_SCRIPT}"
echo "    완료"

# 2. ~/Library/LaunchAgents 폴더 확인
echo ""
echo "[2] LaunchAgents 폴더 확인..."
mkdir -p "${LAUNCH_AGENTS_DIR}"
echo "    ${LAUNCH_AGENTS_DIR}"

# 3. 백업 루트 사전 생성 (stdout/stderr 로그 경로가 없으면 launchd 실패 방지)
echo ""
echo "[3] 백업 루트 폴더 생성..."
mkdir -p "${BACKUP_ROOT}"
echo "    ${BACKUP_ROOT}"

# 4. 템플릿 plist에서 __HOME__ 치환 → 실제 경로로 복사
echo ""
echo "[4] plist 생성 (HOME 경로 치환)..."
sed "s|__HOME__|${HOME}|g" "${TEMPLATE_PLIST}" > "${DEST_PLIST}"
echo "    ${DEST_PLIST}"

# 5. 기존 항목 unload (실패해도 계속)
echo ""
echo "[5] 기존 launchd 항목 제거 시도..."
if launchctl list "${LABEL}" &>/dev/null; then
    launchctl unload "${DEST_PLIST}" 2>/dev/null || true
    echo "    기존 항목 unload 완료"
else
    echo "    기존 항목 없음 — 건너뜀"
fi

# 6. 새 plist load
echo ""
echo "[6] launchd 항목 등록..."
launchctl load "${DEST_PLIST}"
echo "    load 완료"

# 7. 등록 확인
echo ""
echo "[7] 등록 확인..."
if launchctl list | grep -q "${LABEL}"; then
    echo "    [OK] ${LABEL} 등록됨"
    launchctl list "${LABEL}" 2>/dev/null || true
else
    echo "    [경고] launchctl list 에서 항목을 찾지 못했습니다."
    echo "           잠시 후 다시 확인하거나 수동으로 확인하세요:"
    echo "           launchctl list | grep reagent"
fi

# 8. 완료 메시지
echo ""
echo "============================================================"
echo "설치 완료"
echo ""
echo "  자동 실행 : 매일 오후 8시"
echo "  절전/종료 : 다음 로그인 시 즉시 실행 (RunAtLoad)"
echo ""
echo "  수동 백업 테스트:"
echo "    python3 ~/reagent/tools/reagent_local_backup.py --dry-run"
echo "    python3 ~/reagent/tools/reagent_local_backup.py"
echo ""
echo "  백업 결과 확인:"
echo "    ls -lh ~/Reagent_Backups"
echo ""
echo "  launchd 로그 확인:"
echo "    cat ~/Reagent_Backups/reagent_backup_stdout.log"
echo "    cat ~/Reagent_Backups/reagent_backup_stderr.log"
echo ""
echo "  launchd 항목 제거:"
echo "    launchctl unload ~/Library/LaunchAgents/${LABEL}.plist"
echo "============================================================"
