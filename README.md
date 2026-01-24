# Email Crawler

B2B 회사 웹사이트에서 이메일을 자동 추출하는 도구

## 추출 로직

### 1단계: 웹 스크래핑
- 메인 페이지 + 서브 페이지 (/contact, /about, /company) 탐색
- 정규식으로 이메일 패턴 추출

### 2단계: DNS MX 레코드 확인
- 도메인에 메일 서버가 있는지 확인
- MX 레코드 있으면 `info@도메인.com` 생성

### 3단계: 검색 엔진 (DuckDuckGo)
- `site:도메인 email OR contact` 검색
- 검색 결과에서 이메일 추출

## 사용법

```bash
# 빠른 추출 (병렬 처리)
python fast_extract.py

# 깊은 추출 (서브페이지 탐색)
python deep_extract.py

# 적극적 추출 (검색엔진 + MX 레코드)
python aggressive_extract.py
```

## 필요 패키지

```bash
pip install pandas requests beautifulsoup4 dnspython
```

## 출력 형식

HubSpot 매핑용 CSV:
- `email`, `email2`, `email3`, `email4`, `email5`
- `company_name`
- `company_address`
- `record_source_detail_1`
- `description`
