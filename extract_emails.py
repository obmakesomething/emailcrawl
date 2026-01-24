import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin
import warnings
warnings.filterwarnings('ignore')

# CSV 파일 읽기
df = pd.read_csv('b2b_최종결과_v2.csv')

# 건대점 + Tech/Startup/SaaS 또는 Manufacturing/Industrial Ops 필터링
filtered = df[
    (df['지점'] == '건대') &
    (df['new_cluster'].isin(['Tech/Startup/SaaS', 'Manufacturing/Industrial Ops']))
].copy()

print(f"필터링된 회사 수: {len(filtered)}")
print(f"이미 이메일이 있는 회사: {filtered['emails'].notna().sum()}")
print(f"이메일 추출 필요: {filtered['emails'].isna().sum()}")
print("\n" + "="*80)

def extract_emails_from_url(url, timeout=10):
    """웹사이트에서 이메일 추출"""
    emails = set()
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout, verify=False)
        response.encoding = response.apparent_encoding

        # 이메일 패턴 추출
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        found = re.findall(email_pattern, response.text)

        # 유효한 이메일 필터링 (이미지 파일 등 제외)
        for email in found:
            email = email.lower()
            if not any(ext in email for ext in ['.png', '.jpg', '.gif', '.svg', '.css', '.js']):
                emails.add(email)

        # 연락처 페이지 찾기
        soup = BeautifulSoup(response.text, 'html.parser')
        contact_links = []
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            text = link.get_text().lower()
            if any(kw in href or kw in text for kw in ['contact', 'about', '문의', '연락', 'company', '회사']):
                full_url = urljoin(url, link['href'])
                if full_url not in contact_links:
                    contact_links.append(full_url)

        # 연락처 페이지에서 추가 이메일 추출 (최대 3개)
        for contact_url in contact_links[:3]:
            try:
                resp = requests.get(contact_url, headers=headers, timeout=5, verify=False)
                resp.encoding = resp.apparent_encoding
                found = re.findall(email_pattern, resp.text)
                for email in found:
                    email = email.lower()
                    if not any(ext in email for ext in ['.png', '.jpg', '.gif', '.svg', '.css', '.js']):
                        emails.add(email)
            except:
                pass

    except Exception as e:
        print(f"  오류: {str(e)[:50]}")

    return list(emails)

# 이메일 추출
print("\n이메일 추출 시작...\n")

for idx, row in filtered.iterrows():
    company = row['account_name']
    website = row['found_website']
    existing_email = row['emails']

    print(f"[{company}]")
    print(f"  웹사이트: {website}")

    if pd.notna(existing_email) and existing_email.strip():
        print(f"  기존 이메일: {existing_email}")
    else:
        if pd.notna(website):
            new_emails = extract_emails_from_url(website)
            if new_emails:
                filtered.at[idx, 'emails'] = '; '.join(new_emails)
                print(f"  추출된 이메일: {'; '.join(new_emails)}")
            else:
                print(f"  이메일 없음")
        else:
            print(f"  웹사이트 없음")

    print()
    time.sleep(0.5)  # 서버 부하 방지

# HubSpot 매핑용 결과 저장
hubspot_df = filtered[['account_name', 'industry_name', 'new_cluster', 'address_road', 'employee_count', 'found_website', 'emails']].copy()
hubspot_df.columns = ['company_name', 'industry', 'category', 'company_address', 'employee_count', 'website', 'email']

# 결과 저장
hubspot_df.to_csv('건대_tech_manufacturing_hubspot.csv', index=False, encoding='utf-8-sig')
print("\n" + "="*80)
print(f"결과 저장: 건대_tech_manufacturing_hubspot.csv")
print(f"총 {len(hubspot_df)}개 회사")
print(f"이메일 있는 회사: {hubspot_df['email'].notna().sum()}개")

# HubSpot 필수 필드 매핑 안내
print("\n" + "="*80)
print("HubSpot 필수 필드 매핑:")
print("-" * 40)
print("수신자(email) -> email 컬럼")
print("회사 이름(company_name) -> company_name 컬럼")
print("회사 주소(company_street_address_1) -> company_address 컬럼")
print("unsubscribe_link -> HubSpot에서 자동 생성")
print("\n추가 필드:")
print("- 레코드 소스 세부 정보 1: 건대점")
print("- 설명: Tech/Startup/SaaS 또는 Manufacturing/Industrial Ops")

# 카테고리별 통계
print("\n카테고리별 회사 수:")
print(filtered['new_cluster'].value_counts().to_string())
