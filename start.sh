#!/bin/bash
# =============================================================================
# UGV-MON Dashboard 실행 스크립트
# 
# 사용법:
#   ./start.sh mock     - Mock 모드 (가짜 데이터)
#   ./start.sh live     - Live 모드 (lo 인터페이스)
#   ./start.sh eno2     - Live 모드 (eno2 인터페이스)
#   ./start.sh eno3     - Live 모드 (eno3 인터페이스)
# =============================================================================

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 스크립트 위치로 이동
cd "$(dirname "$0")"

# 가상환경 활성화
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 사용법 출력
show_usage() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}           UGV-MON Dashboard 실행 스크립트                  ${BLUE}║${NC}"
    echo -e "${BLUE}╠════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${BLUE}║${NC}                                                            ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  ${GREEN}./start.sh mock${NC}     Mock 모드 (가짜 데이터)             ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  ${GREEN}./start.sh live${NC}     Live 모드 (lo 인터페이스)          ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  ${GREEN}./start.sh eno2${NC}     Live 모드 (eno2 인터페이스)        ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  ${GREEN}./start.sh eno3${NC}     Live 모드 (eno3 인터페이스)        ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}                                                            ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  ${YELLOW}참고: Live 모드는 root 권한이 필요합니다.${NC}              ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
}

# 인자 확인
MODE=${1:-"help"}

case $MODE in
    "mock")
        echo -e "${GREEN}[Mock 모드]${NC} 가짜 데이터로 실행합니다..."
        unset UGV_MON_USE_LIVE
        unset UGV_MON_INTERFACE
        python3 run.py
        ;;
    
    "live"|"lo")
        echo -e "${GREEN}[Live 모드]${NC} lo 인터페이스에서 패킷 캡처..."
        export UGV_MON_USE_LIVE=true
        export UGV_MON_INTERFACE=lo
        
        # root 권한 확인
        if [ "$EUID" -ne 0 ]; then
            echo -e "${YELLOW}⚠ root 권한이 필요합니다. sudo로 재실행합니다...${NC}"
            sudo -E python3 run.py
        else
            python3 run.py
        fi
        ;;
    
    "eno2")
        echo -e "${GREEN}[Live 모드]${NC} eno2 인터페이스에서 패킷 캡처..."
        export UGV_MON_USE_LIVE=true
        export UGV_MON_INTERFACE=eno2
        
        if [ "$EUID" -ne 0 ]; then
            echo -e "${YELLOW}⚠ root 권한이 필요합니다. sudo로 재실행합니다...${NC}"
            sudo -E python3 run.py
        else
            python3 run.py
        fi
        ;;
    
    "eno3")
        echo -e "${GREEN}[Live 모드]${NC} eno3 인터페이스에서 패킷 캡처..."
        export UGV_MON_USE_LIVE=true
        export UGV_MON_INTERFACE=eno3
        
        if [ "$EUID" -ne 0 ]; then
            echo -e "${YELLOW}⚠ root 권한이 필요합니다. sudo로 재실행합니다...${NC}"
            sudo -E python3 run.py
        else
            python3 run.py
        fi
        ;;
    
    *)
        show_usage
        ;;
esac
