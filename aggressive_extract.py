import pandas as pd
import requests
import re
import dns.resolver
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
import time
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv('건대_tech_manufacturing_hubspot.csv')
no_email = df[df['email'].isna()].copy()
print(f"이메일 없는 회사: {len(no_email)}개")
print("="*60)

def get_domain(url):
    """URL에서 도메인 추출"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return None

def check_mx_record(domain):
    """MX 레코드 확인 - 이메일 서버가 있는지"""
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        return True
    except:
        return False

def google_search_email(company_name, domain):
    """Google 검색으로 이메일 찾기"""
    emails = set()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    # 검색 쿼리들
    queries = [
        f'site:{domain} email OR mail OR 문의',
        f'site:{domain} contact',
        f'"{company_name}" email',
    ]

    for query in queries[:2]:  # 첫 2개만
        try:
            # Google 검색 대신 DuckDuckGo 사용 (rate limit 덜 함)
            url = f"https://html.duckduckgo.com/html/?q={query}"
            resp = requests.get(url, headers=headers, timeout=10)

            # 이메일 패턴 찾기
            pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            for e in re.findall(pattern, resp.text):
                e = e.lower()
                if domain in e or company_name[:3].lower() in e:
                    emails.add(e)
            time.sleep(0.5)
        except:
            pass

    return emails

def try_common_emails(domain):
    """일반적인 이메일 패턴 생성"""
    common_prefixes = ['info', 'contact', 'hello', 'support', 'sales', 'help',
                       'admin', 'webmaster', 'marketing', 'service', 'inquiry']
    return [f"{prefix}@{domain}" for prefix in common_prefixes]

def verify_email_smtp(email, timeout=5):
    """간단한 이메일 형식 검증"""
    # SMTP 검증은 스팸으로 오인될 수 있어서 형식만 체크
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def scrape_deeper(url, domain):
    """더 깊은 스크래핑"""
    emails = set()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    # 시도할 페이지들
    pages = [
        url,
        f"{url}/contact",
        f"{url}/contact-us",
        f"{url}/about",
        f"{url}/company",
        f"https://{domain}/contact",
        f"https://{domain}/about",
        f"https://www.{domain}/contact",
    ]

    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    bad = ['png', 'jpg', 'gif', 'svg', 'css', 'js', 'wix', 'schema', 'example', 'test@']

    for page_url in pages[:5]:
        try:
            resp = requests.get(page_url, headers=headers, timeout=5, verify=False)
            for e in re.findall(pattern, resp.text):
                e = e.lower()
                if not any(b in e for b in bad) and len(e) < 50:
                    emails.add(e)
        except:
            pass

    return emails

def extract_email(row):
    idx = row.name
    url = row['website']
    company = row['company_name']

    if pd.isna(url):
        return idx, None, company, "웹사이트없음"

    domain = get_domain(url)
    if not domain:
        return idx, None, company, "도메인파싱실패"

    emails = set()

    # 1. 깊은 스크래핑
    scraped = scrape_deeper(url, domain)
    emails.update(scraped)

    # 2. MX 레코드 확인 후 일반 이메일 추천
    if check_mx_record(domain) and not emails:
        common = try_common_emails(domain)
        # info@, contact@ 중 하나 추천
        emails.add(common[0])  # info@domain

    # 3. 검색 엔진으로 찾기
    if not emails:
        searched = google_search_email(company, domain)
        emails.update(searched)

    # 필터링
    bad = ['aem-kakao', 'example', 'test@', 'wix', 'schema', '@2x', 'sentry']
    clean = [e for e in emails if not any(b in e.lower() for b in bad)]

    if clean:
        return idx, '; '.join(list(clean)[:3]), company, "추출성공"
    return idx, None, company, "실패"

print("\n적극적 추출 시작...\n")

results = []
found = 0
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(extract_email, row): row for _, row in no_email.iterrows()}
    done = 0
    for future in as_completed(futures):
        idx, email, company, status = future.result()
        results.append((idx, email))
        done += 1
        if email:
            found += 1
            print(f"[{done}/{len(no_email)}] ✓ {company}: {email}")
        if done % 20 == 0:
            print(f"... {done}/{len(no_email)} 완료 (새로 찾음: {found}개)")

# 결과 업데이트
for idx, email in results:
    if email:
        emails = email.split('; ')
        df.at[idx, 'email'] = emails[0]
        if len(emails) > 1:
            df.at[idx, 'email2'] = emails[1]
        if len(emails) > 2:
            df.at[idx, 'email3'] = emails[2]

df.to_csv('건대_tech_manufacturing_hubspot.csv', index=False, encoding='utf-8-sig')

# 이메일 있는 것만 저장
with_email = df[df['email'].notna()].copy()
with_email.to_csv('건대_tech_manufacturing_clean.csv', index=False, encoding='utf-8-sig')

print("\n" + "="*60)
print("완료!")
print(f"총: {len(df)}개 | 이메일 있음: {len(with_email)}개 | 새로 찾음: {found}개")
