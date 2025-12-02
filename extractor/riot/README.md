# lp-patchnote-v2

## 실행 방법(로컬)

### 1. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 다음 환경 변수를 설정하세요:

```env
# [필수] Riot API 키
RIOT_API_KEY=your_riot_api_key_here

# [필수] MongoDB 연결 URL
MONGO_DB_URL=mongodb://username:password@host:port/database

# [선택] Redis 설정 (docker-compose.yml에 기본 설정값이 있음)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# 초기 user_id 목록 (선택사항, docker-compose에서 기본값 사용)
INITIAL_USER_IDS=user_id_1,user_id_2
```

### 2. Docker Compose 실행

```bash
docker compose up
```

또는 백그라운드로 실행:

```bash
docker compose up -d
```

### 3. 서비스 확인

- **Redis**: 포트 6379
- **app**: Redis 큐 초기화 및 테스트
- **celery**: Celery worker + beat (2분마다 자동 실행)

## 주요 기능

- Redis 큐에서 user_id를 가져와서 Riot API로 match_id list 및 match 상세 데이터 수집
- MongoDB에 match 데이터 저장
- match 참가자 user_id를 자동으로 큐에 추가(Redis Set 캐싱으로 중복 제거)
- Rate limit: 1초당 20개, 2분당 100개 요청 제한