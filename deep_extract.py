import pandas as pd
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv('건대_tech_manufacturing_hubspot.csv')

# 이메일 없는 회사만 추출
no_email = df[df['email'].isna()].copy()
print(f"이메일 없는 회사: {len(no_email)}개")
print("="*60)

def deep_extract(row):
    idx = row.name
    url = row['website']
    company = row['company_name']

    if pd.isna(url):
        return idx, None, company

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = set()

    # 불량 패턴
    bad = ['aem-kakao', 'example.com', 'test@', '@2x.', 'webpack', 'sentry',
           '@qq.com', 'wixpress', 'schema.org', '.png', '.jpg', '.gif']

    def is_valid(e):
        e = e.lower()
        return not any(b in e for b in bad) and len(e) < 50

    try:
        # 메인 페이지
        resp = requests.get(url, headers=headers, timeout=8, verify=False)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, 'html.parser')

        for e in re.findall(email_pattern, resp.text):
            if is_valid(e):
                emails.add(e.lower())

        # 서브 페이지 탐색
        contact_keywords = ['contact', 'about', 'company', '문의', '연락', '회사소개',
                          'support', 'inquiry', 'info', 'customer', 'help']

        links_to_check = []
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            text = (link.get_text() or '').lower()
            if any(kw in href or kw in text for kw in contact_keywords):
                full_url = urljoin(url, link['href'])
                if full_url.startswith('http') and full_url not in links_to_check:
                    links_to_check.append(full_url)

        # 최대 5개 서브페이지 확인
        for sub_url in links_to_check[:5]:
            try:
                sub_resp = requests.get(sub_url, headers=headers, timeout=5, verify=False)
                sub_resp.encoding = sub_resp.apparent_encoding
                for e in re.findall(email_pattern, sub_resp.text):
                    if is_valid(e):
                        emails.add(e.lower())
            except:
                pass

        # mailto: 링크 특별 처리
        for mailto in soup.find_all('a', href=re.compile(r'^mailto:')):
            href = mailto['href']
            match = re.search(email_pattern, href)
            if match and is_valid(match.group()):
                emails.add(match.group().lower())

    except Exception as e:
        pass

    # 결과 정리
    clean_emails = [e for e in emails if is_valid(e)]
    return idx, '; '.join(clean_emails[:5]) if clean_emails else None, company

print("\n깊은 탐색 시작...\n")

results = []
with ThreadPoolExecutor(max_workers=15) as executor:
    futures = {executor.submit(deep_extract, row): row for _, row in no_email.iterrows()}
    done = 0
    found = 0
    for future in as_completed(futures):
        idx, email, company = future.result()
        results.append((idx, email))
        done += 1
        if email:
            found += 1
            print(f"[{done}/{len(no_email)}] ✓ {company}: {email[:50]}..." if len(str(email)) > 50 else f"[{done}/{len(no_email)}] ✓ {company}: {email}")
        if done % 20 == 0:
            print(f"... {done}/{len(no_email)} 완료 (새로 찾음: {found}개)")

# 결과 업데이트
for idx, email in results:
    if email:
        df.at[idx, 'email'] = email

# 저장
df.to_csv('건대_tech_manufacturing_hubspot.csv', index=False, encoding='utf-8-sig')

print("\n" + "="*60)
print("완료!")
print(f"총 회사: {len(df)}개")
print(f"이메일 있는 회사: {df['email'].notna().sum()}개")
print(f"이메일 없는 회사: {df['email'].isna().sum()}개")
