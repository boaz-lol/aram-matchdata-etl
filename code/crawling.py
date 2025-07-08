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


# patch list들에서 version 동적으로 추출
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


# Patch 구조에 따라 분기 처리 후 크롤링
def crawl_patch(url, patch_version):
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    if soup.find("div", class_="patch-change-block"):
        return parse_patchnote_v1(soup, patch_version)
    elif soup.find("section", {"data-testid": "RichTextPatchNotesBlade"}):
        return parse_patchnote_v2(soup, patch_version)
    else:
        print("지원하지 않는 구조입니다.")
        return False

# ul 태그 파헤치기
def extract_changes(ul):
    changes = []
    if not ul:
        return changes
    for li in ul.find_all("li"):
        strong = li.find("strong")
        key = strong.get_text(strip=True) if strong else ""
        if strong:
            strong.extract()

        # li 내부 모든 텍스트(직접 텍스트 + p, span, br 등 하위 텍스트 전부) 추출
        # li 전체에서 공백 없이 텍스트를 순서대로 다 뽑아버리기
        value = " ".join(t.strip() for t in li.stripped_strings)

        # key 값은 value에 또 들어있을 수 있으니 빼주기
        if key and value.startswith(key):
            value = value[len(key):].lstrip(":").strip()

        if key:
            changes.append({key: value})
        else:
            changes.append(value)
    return changes

# v1 : patch-change-block
def parse_patchnote_v1(soup, patch_version):
    champion_data, item_data = [], []
    patch_blocks = soup.find_all("div", class_="patch-change-block")

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

    # for champ in champion_data:
    #     print(f"챔피언: {champ['name']}")
    #     for skill in champ['skills']:
    #         print(f"  - {skill['skill_name']}:")
    #         for c in skill['changes']:
    #             print(f"    • {c}")
    #     print()
    #
    # for item in item_data:
    #     print(f"아이템: {item['name']}")
    #     for c in item['changes']:
    #         print(f"  • {c}")
    #     print()

    with open(f'patchnotes/champion_patch_{patch_version}.json', 'w', encoding='utf-8') as f:
        json.dump(champion_data, f, ensure_ascii=False, indent=2)

    with open(f'patchnotes/item_patch_{patch_version}.json', 'w', encoding='utf-8') as f:
        json.dump(item_data, f, ensure_ascii=False, indent=2)

    return True

# v2 : RichTextPatchNotesBlade
def parse_patchnote_v2(soup, patch_version):
    champion_data, item_data = [], []
    body = soup.find('section', {'data-testid': 'RichTextPatchNotesBlade'})

    current_section = None
    champ_name = None
    skills = []
    skill_name = None
    item_name = None

    # champion_data 리스트에 현재 champ_name과 skills를 추가하고, 초기화값 반환.
    def flush_champion(champion_data, champ_name, skills):
        if champ_name:
            champion_data.append({
                "name": champ_name,
                "skills": skills
            })
        # 항상 None, [] 반환해서 변수 초기화
        return None, []

    # 각 h2/h3/h4 태그를 순회하며 챔피언과 아이템 파싱
    for tag in body.find_all(['h2', 'h3', 'h4', 'ul']):
        # 챔피언/아이템 블록 구분
        if tag.name == 'h2':
            txt = tag.get_text(strip=True)
            if '챔피언' in txt:
                current_section = 'champion'
                champ_name, skills = flush_champion(champion_data, champ_name, skills)
                skill_name = None
            elif '아이템' in txt:
                current_section = 'item'
                champ_name, skills = flush_champion(champion_data, champ_name, skills)
                skill_name = None
            else:
                current_section = None

        elif current_section == 'champion':
            if tag.name == 'h3':
                champ_name, skills = flush_champion(champion_data, champ_name, skills)
                champ_name = tag.get_text(strip=True)
                skills = []
                skill_name = None

            elif tag.name == 'h4':
                skill_name = tag.get_text(strip=True)

            elif tag.name == 'ul' and champ_name and skill_name:
                changes = extract_changes(tag)
                skills.append({
                    "skill_name": skill_name,
                    "changes": changes
                })
                skill_name = None

        elif current_section == 'item':
            if tag.name == 'h4':
                item_name = tag.get_text(strip=True)
            elif tag.name == 'ul' and item_name:
                changes = extract_changes(tag)
                item_data.append({
                    "name": item_name,
                    "changes": changes
                })
                item_name = None

    champ_name, skills = flush_champion(champion_data, champ_name, skills)

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

