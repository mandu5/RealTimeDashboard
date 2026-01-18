# 변경 이력 (Changelog)

## 최근 변경사항 (Latest Updates)

### UI/UX 개선

#### 통신 품질 차트
- ✅ 시간 범위 선택 버튼 추가 (30초, 1분, 5분)
- ✅ 범례 표시 (PPS 좌, 지터 우)
- ✅ 하단 실시간 값 표시 (PPS, 지터)
- ✅ X축 시간 레이블 최적화 (겹치지 않도록 동적 조정)
- ✅ 시간 범위에 따른 데이터 필터링
- ✅ 차트 간격 조정 (vertical_spacing: 0.15)

#### 가용성 타임라인
- ✅ 마지막 세그먼트가 타임윈도우 끝까지 유지되도록 수정
- ✅ 세그먼트 전체 영역에서 hover 정보 표시 (중간점 추가)
- ✅ Down 세그먼트가 항상 보이도록 개선

#### 장치 연결 상태
- ✅ 경고/오류 상태 시 hover tooltip으로 원인 표시
- ✅ HTML `title` 속성 사용 (레이아웃 영향 없음)
- ✅ `DeviceStatus` 모델에 `error_reason` 필드 추가
- ✅ 모든 박스 크기 동일 유지 보장

#### 로그 테이블
- ✅ Time 포맷 변경: `HH:MM:SS` (밀리초 제거)
- ❌ Auto-scroll 기능 제거

### 데이터 모델 변경

#### `DeviceStatus` (`ugv_mon/data/models.py`)
```python
@dataclass
class DeviceStatus:
    # ... 기존 필드 ...
    error_reason: Optional[str] = None  # 추가: tooltip 메시지
```

#### `LogEntry` (`ugv_mon/data/models.py`)
```python
def to_dict(self) -> Dict:
    return {
        "time": self.timestamp.strftime("%H:%M:%S"),  # 변경: 밀리초 제거
        # ... 기타 필드 ...
    }
```

### 콜백 변경

#### `update_callbacks.py`
- ✅ 시간 범위 선택 콜백 추가 (`update_time_range`)
- ✅ `update_all_components`에 시간 범위 및 실시간 값 업데이트 추가
- ❌ Auto-scroll 관련 콜백 제거

### Store 변경

#### `main_layout.py`
- ✅ `chart-time-range` Store 추가 (기본값: 60초)

---

## 주요 수정 사항

### 1. 통신 품질 차트 기능 확장
- **파일**: `ugv_mon/layouts/charts.py`, `ugv_mon/layouts/main_layout.py`
- **변경**: 시간 범위 선택, 범례, 실시간 값 표시 추가
- **영향**: 차트 패널 UI 확장, 사용자 경험 개선

### 2. 가용성 타임라인 안정화
- **파일**: `ugv_mon/data/mock_data.py`, `ugv_mon/layouts/charts.py`
- **변경**: 마지막 세그먼트 유지 로직 개선, hover 개선
- **영향**: 차트 데이터 일관성 유지, 사용자 상호작용 개선

### 3. 장치 연결 상태 tooltip
- **파일**: `ugv_mon/components/device_grid.py`, `ugv_mon/data/models.py`
- **변경**: HTML `title` 속성 기반 tooltip, `error_reason` 필드 추가
- **영향**: 사용자가 오류 원인을 쉽게 확인 가능

### 4. 로그 테이블 포맷 개선
- **파일**: `ugv_mon/data/models.py`
- **변경**: 타임스탬프에서 밀리초 제거
- **영향**: 가독성 향상

---

## 제거된 기능

- ❌ 로그 테이블 Auto-scroll 기능
  - 이유: 사용자 경험상 불필요
  - 제거 파일: `ugv_mon/app.py`, `ugv_mon/callbacks/update_callbacks.py`, `ugv_mon/layouts/main_layout.py`, `ugv_mon/components/log_table.py`
