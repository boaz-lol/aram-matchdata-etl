import json
import requests
import re
import os
from bs4 import BeautifulSoup

PATCH_LIST_URL = 'https://www.leagueoflegends.com/ko-kr/news/tags/patch-notes/'

# version pattern 추출 -> 25.12, 25-12, 2025.S1.1, 2025-s1-1, 14.17...
def extract_patch_version(title):
    match = re.search(r'(\d{2,4}(?:[.\-][Ss]?\d+)*|\d{2,4}(?:[.\-][Ss]?\d+)*)', title)
    if match:
        # - 로 통일, 소문자로 통일
        return match.group(1).replace('.', '-').lower()
    return None


def get_patch_list():
    response = requests.get(PATCH_LIST_URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    patch_list = []

    for patch_card in soup.find_all('a', attrs={'data-testid': 'articlefeaturedcard-component'}):
        url = f"https://www.leagueoflegends.com{patch_card['href']}"
        title_tag = patch_card.find('div', class_='sc-ce9b75fd-0 lmZfRs')
        if not title_tag:
            continue
        title = title_tag.text
        version = extract_patch_version(title)
        if version:
            patch_list.append({'url': url, 'version': version, 'title': title})

    return patch_list


def already_crawled(version):
    return os.path.exists(f'patchnotes/champion_patch_{version}.json')

# 크롤링
def crawl_patch(url, patch_version):
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    # patch-change-block로 변경 사항 구분
    patch_blocks = soup.find_all("div", class_="patch-change-block")
    champion_data, item_data = [], []

    def extract_changes(ul):
        changes = []
        if not ul:
            return changes
        for li in ul.find_all("li"):
            strong = li.find("strong")
            key = strong.get_text(strip=True) if strong else ""
            if strong:
                strong.extract()
            value = li.get_text(strip=True)
            if key:
                changes.append({key: value})
            else:
                changes.append(value)
        return changes

    for block in patch_blocks:
        # 챔피언/아이템 블록 구분
        champ_title = block.find("h3", class_="change-title")
        if champ_title:
            champ_name = champ_title.get_text(strip=True)
            skills = []

            for h4 in block.find_all("h4", class_="change-detail-title"):
                skill_name = h4.get_text(strip=True)
                ul = h4.find_next_sibling("ul")
                changes = extract_changes(ul)
                if changes:
                    skills.append({
                        "skill_name": skill_name,
                        "changes": changes
                    })
            champion_data.append({
                "name": champ_name,
                "skills": skills
            })
            continue

        item_title = block.find("h4", class_="change-detail-title ability-title")
        if item_title:
            item_name = item_title.get_text(strip=True)
            uls = block.find_all("ul")
            changes = []
            for ul in uls:
                changes += extract_changes(ul)
            item_data.append({
                "name": item_name,
                "changes": changes
            })
            continue

    for champ in champion_data:
        print(f"챔피언: {champ['name']}")
        for skill in champ['skills']:
            print(f"  - {skill['skill_name']}:")
            for c in skill['changes']:
                print(f"    • {c}")
        print()

    for item in item_data:
        print(f"아이템: {item['name']}")
        for c in item['changes']:
            print(f"  • {c}")
        print()

    with open(f'patchnotes/champion_patch_{patch_version}.json', 'w', encoding='utf-8') as f:
        json.dump(champion_data, f, ensure_ascii=False, indent=2)

    with open(f'patchnotes/item_patch_{patch_version}.json', 'w', encoding='utf-8') as f:
        json.dump(item_data, f, ensure_ascii=False, indent=2)

    return True


if __name__ == "__main__":
    os.makedirs('patchnotes', exist_ok=True)
    patch_list = get_patch_list()

    for patch in patch_list:
        if not already_crawled(patch['version']):
            print(f"Crawling {patch['version']} ({patch['url']}) ...")
            try:
                crawl_patch(patch['url'], patch['version'])
                print(f"Crawled! {patch['version']}")
            except Exception as e:
                print(f"Failed {patch['version']}: {e}")

