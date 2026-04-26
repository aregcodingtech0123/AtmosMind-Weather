import re

ko_map = {
  'london': '런던', 'newyorkcity': '뉴욕', 'tokyo': '도쿄', 'istanbul': '이스탄불',
  'sydney': '시드니', 'paris': '파리', 'dubai': '두바이', 'bangkok': '방콕',
  'rome': '로마', 'berlin': '베를린', 'seoul': '서울', 'doha': '도하',
  'riodejaneiro': '리우데자네이루', 'cairo': '카이로', 'toronto': '토론토',
  'auckland': '오클랜드', 'amsterdam': '암스테르담', 'macau': '마카오',
  'hongkong': '홍콩', 'singapore': '싱가포르', 'kualalumpur': '쿠알라룸푸르',
  'antalya': '안탈리아', 'mecca': '메카', 'venice': '베네치아',
  'buenosaires': '부에노스아이레스', 'losangeles': '로스앤젤레스', 'capetown': '케이프타운',
  'edinburgh': '에든버러', 'lisbon': '리스본', 'madrid': '마드리드',
  'munich': '뮌헨', 'budapest': '부다페스트', 'vienna': '빈', 
  'marrakesh': '마라케시', 'frankfurt': '프랑크푸르트', 'warsaw': '바르샤바',
  'mumbai': '뭄바이', 'newdelhi': '뉴델리', 'mexicocity': '멕시코시티'
}

with open('frontend/src/App.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

def replacer(match):
    id_str = match.group(1)
    ko_name = ko_map.get(id_str, id_str)
    names_str = match.group(2)
    new_names = names_str.replace('}', f", ko: '{ko_name}'}}")
    return match.group(0).replace(names_str, new_names)

new_text = re.sub(r"\{ id: '([^']+)', defaultName.+?names: (\{[^}]+\}),.+?\},", replacer, text)

with open('frontend/src/App.tsx', 'w', encoding='utf-8') as f:
    f.write(new_text)

print('Updated App.tsx with Korean translations.')
