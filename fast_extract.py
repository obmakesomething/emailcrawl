import pandas as pd
import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv('b2b_최종결과_v2.csv')
filtered = df[
    (df['지점'] == '건대') &
    (df['new_cluster'].isin(['Tech/Startup/SaaS', 'Manufacturing/Industrial Ops']))
].copy()

def extract_emails(row):
    idx = row.name
    url = row['found_website']
    existing = row['emails']
    company = row['account_name']

    if pd.notna(existing) and str(existing).strip():
        return idx, existing, company, "기존"

    if pd.isna(url):
        return idx, None, company, "웹사이트없음"

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=5, verify=False)
        resp.encoding = resp.apparent_encoding

        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = set()
        for e in re.findall(pattern, resp.text):
            e = e.lower()
            if not any(x in e for x in ['.png', '.jpg', '.gif', '.svg', '.css', '.js', 'sentry', 'webpack']):
                emails.add(e)

        if emails:
            return idx, '; '.join(list(emails)[:5]), company, "추출성공"
        return idx, None, company, "이메일없음"
    except Exception as e:
        return idx, None, company, f"오류"

print(f"총 {len(filtered)}개 회사 처리 중...")
print("="*60)

results = []
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(extract_emails, row): row for _, row in filtered.iterrows()}
    done = 0
    for future in as_completed(futures):
        idx, email, company, status = future.result()
        results.append((idx, email))
        done += 1
        if email:
            print(f"[{done}/{len(filtered)}] {company}: {email[:50]}..." if len(str(email)) > 50 else f"[{done}/{len(filtered)}] {company}: {email}")
        if done % 20 == 0:
            print(f"... {done}/{len(filtered)} 완료")

# 결과 업데이트
for idx, email in results:
    if email:
        filtered.at[idx, 'emails'] = email

# HubSpot용 파일 저장
hubspot_df = pd.DataFrame({
    'email': filtered['emails'],
    'company_name': filtered['account_name'],
    'company_street_address_1': filtered['address_road'],
    'industry': filtered['industry_name'],
    'category': filtered['new_cluster'],
    'employee_count': filtered['employee_count'],
    'website': filtered['found_website'],
    'record_source_detail_1': '건대점',
    'description': filtered['new_cluster']
})

hubspot_df.to_csv('건대_tech_manufacturing_hubspot.csv', index=False, encoding='utf-8-sig')

print("\n" + "="*60)
print("완료!")
print(f"총 회사: {len(hubspot_df)}개")
print(f"이메일 있는 회사: {hubspot_df['email'].notna().sum()}개")
print("파일: 건대_tech_manufacturing_hubspot.csv")
