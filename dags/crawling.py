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


def parse_v1_champion_block(block):
    champ_title = block.find("h3", class_="change-title")
    if not champ_title:
        return []

    champ_name = champ_title.get_text(strip=True)
    skills = []

    for h4 in block.find_all("h4", class_="change-detail-title"):
        skill_name = h4.get_text(strip=True)
        ul = h4.find_next_sibling("ul")
        changes = extract_changes(ul)
        if changes:
            skills.append({"skill_name": skill_name, "changes": changes})

    return [{"name": champ_name, "skills": skills}]


def parse_v1_item_block(block):
    item_title = block.find("h4", class_="change-detail-title ability-title")
    if not item_title:
        return []

    item_name = item_title.get_text(strip=True)
    uls = block.find_all("ul")
    changes = []

    for ul in uls:
        changes += extract_changes(ul)

    return [{"name": item_name, "changes": changes}]


def parse_patchnote_v1(soup, patch_version):
    champion_data, item_data = [], []
    patch_blocks = soup.find_all("div", class_="patch-change-block")

    for block in patch_blocks:
        champion_data += parse_v1_champion_block(block)
        item_data += parse_v1_item_block(block)

    save_patch_data(patch_version, champion_data, item_data)

    print("champion_data:", champion_data)
    print("item_data:", item_data)

    return True


def parse_v2_champion_block(tags):
    champion_data = []
    champ_name = None
    skills = []
    skill_name = None

    def flush_champ():
        nonlocal champ_name, skills
        if champ_name:
            champion_data.append({"name": champ_name, "skills": skills})
        champ_name = None
        skills = []

    for tag in tags:
        if tag.name == 'h3':
            flush_champ()
            champ_name = tag.get_text(strip=True)
            skills = []
        elif tag.name == 'h4':
            skill_name = tag.get_text(strip=True)
        elif tag.name == 'ul' and champ_name and skill_name:
            changes = extract_changes(tag)
            skills.append({"skill_name": skill_name, "changes": changes})
            skill_name = None

    flush_champ()
    return  champion_data


def parse_v2_item_block(tags):
    item_data = []
    item_name = None
    for tag in tags:
        if tag.name in ['h3', 'h4']:
            item_name = tag.get_text(strip=True)
        elif tag.name == 'ul' and item_name:
            changes = extract_changes(tag)
            item_data.append({"name": item_name, "changes": changes})
            item_name = None
    return item_data


def parse_patchnote_v2(soup, patch_version):
    champion_data, item_data = [], []
    body = soup.find('section', {'data-testid': 'RichTextPatchNotesBlade'})
    if not body:
        return False

    section_map = {
        'champion': [],
        'item': []
    }
    current_section = None
    tags = list(body.find_all(['h2', 'h3', 'h4', 'ul']))

    for tag in tags:
        if tag.name == 'h2':
            txt = tag.get_text(strip=True)
            if '챔피언' in txt:
                current_section = 'champion'
            elif '아이템' in txt:
                current_section = 'item'
            else:
                current_section = None
        elif current_section in section_map:
            section_map[current_section].append(tag)

    champion_data += parse_v2_champion_block(section_map['champion'])
    item_data += parse_v2_item_block(section_map['item'])

    save_patch_data(patch_version, champion_data, item_data)

    print("champion_data:", champion_data)
    print("item_data:", item_data)

    return True


def save_patch_data(patch_version, champion_data, item_data):
    with open(f'patchnotes/champion_patch_{patch_version}.json', 'w', encoding='utf-8') as f:
        json.dump(champion_data, f, ensure_ascii=False, indent=2)
    with open(f'patchnotes/item_patch_{patch_version}.json', 'w', encoding='utf-8') as f:
        json.dump(item_data, f, ensure_ascii=False, indent=2)


def crawl_all():
    os.makedirs('../patchnotes', exist_ok=True)
    patch_list = get_patch_list()

    for patch in patch_list:
        if not already_crawled(patch['version']):
            print(f"Crawling {patch['version']} ({patch['url']}) ...")
            try:
                crawl_patch(patch['url'], patch['version'])
                print(f"Crawled! {patch['version']}")
            except Exception as e:
                print(f"Failed {patch['version']}: {e}")


if __name__ == "__main__":
    crawl_all()