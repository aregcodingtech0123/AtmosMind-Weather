


import { SupportedLanguage } from '../context/SettingsContext';

export interface PopularCity {
  id: string;
  defaultName: string;
  names: Record<SupportedLanguage, string>;
  latitude: number;
  longitude: number;
}

export const POPULAR_CITIES: PopularCity[] = [
  {
    id: "bangkok",
    defaultName: "Bangkok, Thailand",
    names: {"en": "Bangkok", "tr": "Bangkok", "fr": "Bangkok", "es": "Bangkok", "de": "Bangkok", "ja": "バンコク", "zh": "曼谷", "hi": "बैंकॉक", "ru": "Бангкок", "ar": "بانكوك", "it": "Bangkok", "pt": "Banguecoque", "bn": "ব্যাংকক", "ur": "بنکاک", "tl": "Bangkok", "vi": "Bangkok", "uk": "Бангкок", "pl": "Bangkok", "nl": "Bangkok", "fi": "Bangkok", "da": "Bangkok", "no": "Bangkok", "sv": "Bangkok", "ha": "Bangkok", "ta": "பேங்காக்", "ms": "Bangkok", "id": "Bangkok", "jv": "Bangkok", "su": "Bangkok", "hu": "Bangkok", "cs": "Bangkok", "el": "Μπανγκόκ", "ro": "Bangkok", "fa": "بانکوک", "th": "กรุงเทพฯ", "sw": "Bangkok", "az": "Banqkok", "kk": "Бангкок", "uz": "Bangkok", "ky": "Bangkok", "tk": "Bangkok", "ko": "방콕"} as Record<SupportedLanguage, string>,
    latitude: 13.754,
    longitude: 100.5014
  },
    {
    id: "paris",
    defaultName: "Paris, France",
    names: {"en": "Paris", "tr": "Paris", "fr": "Paris", "es": "París", "de": "Paris", "ja": "パリ", "zh": "巴黎", "hi": "पैरिस", "ru": "Париж", "ar": "باريس", "it": "Parigi", "pt": "Paris", "bn": "প্যারিস", "ur": "پیرس", "tl": "Lungsod ng Paris", "vi": "Paris", "uk": "Париж", "pl": "Paryż", "nl": "Parijs", "fi": "Pariisi", "da": "Paris", "no": "Paris", "sv": "Paris", "ha": "Pariis", "ta": "பாரிஸ்", "ms": "Paris", "id": "Paris", "jv": "Paris", "su": "Paris", "hu": "Párizs", "cs": "Paříž", "el": "Παρίσι", "ro": "Paris", "fa": "پاریس", "th": "ปารีส", "sw": "Paris", "az": "Paris", "kk": "Париж", "uz": "Parij", "ky": "Париж", "tk": "Pariž", "ko": "파리"} as Record<SupportedLanguage, string>,
    latitude: 48.8534,
    longitude: 2.3488
  },
    {
    id: "london",
    defaultName: "London, United Kingdom",
    names: {"en": "London", "tr": "Londra", "fr": "Londres", "es": "Londres", "de": "London", "ja": "ロンドン", "zh": "倫敦", "hi": "लंदन", "ru": "Лондон", "ar": "لندن", "it": "Londra", "pt": "Londres", "bn": "লন্ডন", "ur": "لندن", "tl": "Londres", "vi": "Luân Đôn", "uk": "Лондон", "pl": "Londyn", "nl": "Londen", "fi": "Lontoo", "da": "London", "no": "London", "sv": "London", "ha": "London", "ta": "இலண்டன்", "ms": "London", "id": "London", "jv": "London", "su": "London", "hu": "London", "cs": "Londýn", "el": "Λονδίνο", "ro": "Londra", "fa": "لندن", "th": "ลอนดอน", "sw": "London", "az": "London", "kk": "Лондон", "uz": "London", "ky": "Лондон", "tk": "London", "ko": "런던"} as Record<SupportedLanguage, string>,
    latitude: 51.5085,
    longitude: -0.1257
  },
    {
    id: "dubai",
    defaultName: "Dubai, United Arab Emirates",
    names: {"en": "Dubai", "tr": "Dubai", "fr": "Dubaï", "es": "Dubái", "de": "Dubai", "ja": "ドバイ", "zh": "迪拜", "hi": "दुबई", "ru": "Дубай", "ar": "دبي", "it": "Dubai", "pt": "Dubai", "bn": "দুবাই", "ur": "دبئی", "tl": "Dubai", "vi": "Dubai", "uk": "Дубай", "pl": "Dubaj", "nl": "Dubai", "fi": "Dubai", "da": "Dubai", "no": "Dubai", "sv": "Dubai", "ha": "Dubai", "ta": "துபை", "ms": "Dubai", "id": "Dubai", "jv": "Dubai", "su": "Dubai", "hu": "Dubaj", "cs": "Dubaj", "el": "Ντουμπάι", "ro": "Dubai", "fa": "دبی", "th": "ดูไบ", "sw": "Dubai", "az": "Dubay", "kk": "Дубай", "uz": "Dubai", "ky": "Dubai", "tk": "Dubai", "ko": "두바이"} as Record<SupportedLanguage, string>,
    latitude: 25.0772,
    longitude: 55.3093
  },
    {
    id: "singapore",
    defaultName: "Singapore, SG",
    names: {"en": "Singapore", "tr": "Singapur", "fr": "Singapour", "es": "Singapur", "de": "Singapur", "ja": "シンガポール", "zh": "新加坡", "hi": "सिंगापुर", "ru": "Сингапур", "ar": "سنغافورة", "it": "Singapore", "pt": "Singapura", "bn": "সিঙ্গাপুর", "ur": "سنگاپور", "tl": "Singapore", "vi": "Singapore", "uk": "Сінгапур", "pl": "Singapur", "nl": "Singapore", "fi": "Singapore", "da": "Singapore", "no": "Singapore", "sv": "Singapore", "ha": "Singapur", "ta": "சிங்கப்பூர்", "ms": "Singapura", "id": "Singapura", "jv": "Singapura", "su": "Republic of Singapore", "hu": "Szingapúr", "cs": "Singapur", "el": "Σιγκαπούρη", "ro": "Singapore", "fa": "سنگاپور", "th": "สิงคโปร์", "sw": "Singapore", "az": "Sinqapur", "kk": "Сингапур", "uz": "Singapur", "ky": "Сингапур", "tk": "Singapur", "ko": "싱가포르"} as Record<SupportedLanguage, string>,
    latitude: 1.3521,
    longitude: 103.8198
  },
    {
    id: "newyorkcity",
    defaultName: "New York, United States",
    names: {"en": "New York", "tr": "New York", "fr": "New York", "es": "Nueva York", "de": "New York", "ja": "ニューヨーク", "zh": "纽约", "hi": "न्यूयॉर्क", "ru": "Нью-Йорк", "ar": "نيويورك", "it": "New York", "pt": "Nova Iorque", "bn": "নিউ ইয়র্ক", "ur": "نیویارک", "tl": "New York", "vi": "New York", "uk": "Нью-Йорк", "pl": "Nowy Jork", "nl": "New York", "fi": "New York", "da": "New York", "no": "New York", "sv": "New York", "ha": "New York", "ta": "நியூயார்க்", "ms": "New York", "id": "New York", "jv": "New York", "su": "New York", "hu": "New York", "cs": "New York", "el": "Νέα Υόρκη", "ro": "New York", "fa": "نیویورک", "th": "นิวยอร์ก", "sw": "New York", "az": "Nyu-York", "kk": "Нью-Йорк", "uz": "Nyu-York", "ky": "Нью-Йорк", "tk": "Nýu-Ýork", "ko": "뉴욕"} as Record<SupportedLanguage, string>,
    latitude: 40.7143,
    longitude: -74.006
  },
    {
    id: "istanbul",
    defaultName: "Istanbul, Turkiye",
    names: {"en": "Istanbul", "tr": "İstanbul", "fr": "Istanbul", "es": "Estambul", "de": "Istanbul", "ja": "イスタンブール", "zh": "伊斯坦堡", "hi": "इस्तांबुल", "ru": "Стамбул", "ar": "اسطنبول", "it": "Istanbul", "pt": "Istambul", "bn": "ইস্তাম্বুল", "ur": "استنبول", "tl": "Istanbul", "vi": "Istanbul", "uk": "Стамбул", "pl": "Stambuł", "nl": "Istanbul", "fi": "Istanbul", "da": "Istanbul", "no": "Istanbul", "sv": "Istanbul", "ha": "Istanbul", "ta": "இஸ்தான்புல்", "ms": "Istanbul", "id": "Istanbul", "jv": "Istanbul", "su": "Istanbul", "hu": "Isztambul", "cs": "Istanbul", "el": "Ισταμπούλ", "ro": "Istanbul", "fa": "استانبول", "th": "อิสตันบูล", "sw": "Istanbul", "az": "İstanbul", "kk": "Стамбул", "uz": "Istanbul", "ky": "Стамбул", "tk": "Stambul", "ko": "이스탄불"} as Record<SupportedLanguage, string>,
    latitude: 41.0138,
    longitude: 28.9603
  },
    {
    id: "tokyo",
    defaultName: "Tokyo, Japan",
    names: {"en": "Tokyo", "tr": "Tokyo", "fr": "Tokyo", "es": "Tokio", "de": "Tokio", "ja": "東京", "zh": "東京", "hi": "टोक्यो", "ru": "Токио", "ar": "طوكيو", "it": "Tokyo", "pt": "Tóquio", "bn": "টোকিও", "ur": "ٹوکیو", "tl": "Tokyo", "vi": "Tokyo", "uk": "Токіо", "pl": "Tokio", "nl": "Tokio", "fi": "Tokio", "da": "Tokyo", "no": "Tokyo", "sv": "Tokyo", "ha": "Tokyo", "ta": "டோக்கியோ", "ms": "Tokyo", "id": "Tokyo", "jv": "Tokyo", "su": "Tokyo", "hu": "Tokió", "cs": "Tokio", "el": "Τόκιο", "ro": "Tokio", "fa": "توکیو", "th": "โตเกียว", "sw": "Tokyo", "az": "Tokyo", "kk": "Токио", "uz": "Tokio", "ky": "Токио", "tk": "Tokio", "ko": "도쿄"} as Record<SupportedLanguage, string>,
    latitude: 35.6895,
    longitude: 139.6917
  },
    {
    id: "hongkong",
    defaultName: "Hong Kong",
    names: {"en": "Hong Kong", "tr": "Hong Kong", "fr": "Hong Kong", "es": "Hong Kong", "de": "Hongkong", "ja": "香港", "zh": "香港", "hi": "हाँग काँग", "ru": "Гонконг", "ar": "هونغ كونغ", "it": "Hong Kong", "pt": "Hong Kong", "bn": "হংকং", "ur": "ہانگ کانگ", "tl": "Hong Kong", "vi": "Hồng Kông", "uk": "Гонконг", "pl": "Hong Kong", "nl": "Hong Kong", "fi": "Hong Kong", "da": "Hongkong", "no": "Hongkong", "sv": "Hong Kong", "ha": "Hong Kong", "ta": "ஆங்காங்", "ms": "Hong Kong", "id": "Hong Kong", "jv": "Hong Kong", "su": "Hong Kong", "hu": "Hongkong", "cs": "Hong Kong", "el": "Χονγκ Κονγκ", "ro": "Hong Kong", "fa": "هنگ کنگ", "th": "ฮ่องกง", "sw": "Hong Kong", "az": "Hong Kong", "kk": "Гонконг", "uz": "Gon Kong", "ky": "Гонконг", "tk": "Hong Kong", "ko": "홍콩"} as Record<SupportedLanguage, string>,
    latitude: 22.3193,
    longitude: 114.1694
  },
    {
    id: "rome",
    defaultName: "Rome, Italy",
    names: {"en": "Rome", "tr": "Roma", "fr": "Rome", "es": "Roma", "de": "Rom", "ja": "ローマ", "zh": "罗马市", "hi": "रोम", "ru": "Рим", "ar": "روما", "it": "Roma", "pt": "Roma", "bn": "রোম", "ur": "روم", "tl": "Lungsod ng Roma", "vi": "Roma", "uk": "Рим", "pl": "Rzym", "nl": "Rome", "fi": "Rooma", "da": "Rom", "no": "Roma", "sv": "Rom", "ha": "Rome", "ta": "Rome", "ms": "Rom", "id": "Roma", "jv": "Rome", "su": "Rome", "hu": "Róma", "cs": "Řím", "el": "Ρώμη", "ro": "Roma", "fa": "رم", "th": "โรม", "sw": "Mji wa Roma", "az": "Rome", "kk": "Rome", "uz": "Rome", "ky": "Rome", "tk": "Rome", "ko": "로마"} as Record<SupportedLanguage, string>,
    latitude: 41.8947,
    longitude: 12.4839
  },
    {
    id: "losangeles",
    defaultName: "Los Angeles, United States",
    names: {"en": "Los Angeles", "tr": "Los Angeles", "fr": "Los Angeles", "es": "Los Ángeles", "de": "Los Angeles", "ja": "ロサンゼルス", "zh": "洛杉矶", "hi": "लॉस एंजेलिस", "ru": "Лос-Анджелес", "ar": "لوس أنجلوس", "it": "Los Angeles", "pt": "Los Angeles", "bn": "লস অ্যাঞ্জেলেস", "ur": "لاس اینجلس", "tl": "Lungsod ng Los Angeles", "vi": "Los Angeles", "uk": "Лос-Анджелес", "pl": "Los Angeles", "nl": "Los Angeles", "fi": "Los Angeles", "da": "Los Angeles", "no": "Los Angeles", "sv": "Los Angeles", "ha": "Los Angeles", "ta": "லாஸ் ஏஞ்சலஸ்", "ms": "Los Angeles", "id": "Los Angeles", "jv": "Los Angeles", "su": "Los Angeles", "hu": "Los Angeles", "cs": "Los Angeles", "el": "Λος Άντζελες", "ro": "Los Angeles", "fa": "لس‌آنجلس", "th": "ลอสแอนเจลิส", "sw": "Los Angeles", "az": "Los-Anceles", "kk": "Лос Анжелес", "uz": "Los Anjeles", "ky": "Лос-Анжелес шаары", "tk": "Los-Anjeles", "ko": "엘에이"} as Record<SupportedLanguage, string>,
    latitude: 34.0522,
    longitude: -118.2437
  },
    {
    id: "macau",
    defaultName: "Macau",
    names: {"en": "Macau", "tr": "Makao", "fr": "Macao", "es": "Macao", "de": "Macao", "ja": "マカオ", "zh": "澳门", "hi": "मकाउ", "ru": "Макао", "ar": "ماكاو", "it": "Macao", "pt": "Macau", "bn": "ম্যাকাউ", "ur": "مکاؤ", "tl": "Makaw", "vi": "Ma Cao", "uk": "Аоминь", "pl": "Makau", "nl": "Macau", "fi": "Macao", "da": "Macao", "no": "Macao", "sv": "Macao", "ha": "Macau", "ta": "மக்காவு", "ms": "Macau", "id": "Makau", "jv": "Makau", "su": "Makau", "hu": "Makaó", "cs": "Macau", "el": "Μακάου", "ro": "Macau", "fa": "ماکائو", "th": "เขตบริหารพิเศษมาเก๊า", "sw": "Macau", "az": "Makao", "kk": "Аумын", "uz": "Macau", "ky": "Macau", "tk": "Macau", "ko": "마카오"} as Record<SupportedLanguage, string>,
    latitude: 22.1987,
    longitude: 113.5439
  },
    {
    id: "antalya",
    defaultName: "Antalya, Turkiye",
    names: {"en": "Antalya", "tr": "Antalya", "fr": "Antalya", "es": "Antalya", "de": "Antalya", "ja": "アンタルヤ", "zh": "安塔利亚", "hi": "अंताल्या", "ru": "Анталия", "ar": "أنطاليا", "it": "Adalia", "pt": "Antália", "bn": "আন্তালিয়া", "ur": "انطالیہ", "tl": "Antalya", "vi": "Antalya", "uk": "Анталья", "pl": "Antalya", "nl": "Antalya", "fi": "Antalya", "da": "Antalya", "no": "Antalya", "sv": "Antalya", "ha": "Antalya", "ta": "அந்தால்யா", "ms": "Antalya", "id": "Antalya", "jv": "Antalya", "su": "Antalya", "hu": "Antalya", "cs": "Antalya", "el": "Αττάλεια", "ro": "Antalya", "fa": "آنتالیا", "th": "อันตัลยา", "sw": "Antalya", "az": "Antalya", "kk": "Анталия", "uz": "Antaliya", "ky": "Анталья", "tk": "Antalya", "ko": "안탈리아"} as Record<SupportedLanguage, string>,
    latitude: 36.8969,
    longitude: 30.7133
  },
    {
    id: "kualalumpur",
    defaultName: "Kuala Lumpur, Malaysia",
    names: {"en": "Kuala Lumpur", "tr": "Kuala Lumpur", "fr": "Kuala Lumpur", "es": "Kuala Lumpur", "de": "Kuala Lumpur", "ja": "クアラルンプール", "zh": "吉隆坡", "hi": "कुआलालम्पुर", "ru": "Куала-Лумпур", "ar": "كوالالمبور", "it": "Kuala Lumpur", "pt": "Kuala Lumpur", "bn": "কুয়ালালামপুর", "ur": "کوالالمپور", "tl": "Kuala Lumpur", "vi": "Kuala Lumpur", "uk": "Куала-Лумпур", "pl": "Kuala Lumpur", "nl": "Kuala Lumpur", "fi": "Kuala Lumpur", "da": "Kuala Lumpur", "no": "Kuala Lumpur", "sv": "Kuala Lumpur", "ha": "Kuala Lumpur", "ta": "கோலாலம்பூர்", "ms": "Kuala Lumpur", "id": "Kuala Lumpur", "jv": "Kuala Lumpur", "su": "Kuala Lumpur", "hu": "Kuala Lumpur", "cs": "Kuala Lumpur", "el": "Κουάλα Λουμπούρ", "ro": "Kuala Lumpur", "fa": "کوالالامپور", "th": "กัวลาลัมเปอร์", "sw": "Kuala Lumpur", "az": "Kuala Lumpur", "kk": "Куала Лумпур", "uz": "Kuala Lumpur", "ky": "Kuala Lumpur", "tk": "Kuala Lumpur", "ko": "쿠알라룸푸르"} as Record<SupportedLanguage, string>,
    latitude: 3.139,
    longitude: 101.6869
  },
    {
    id: "mumbai",
    defaultName: "Mumbai, India",
    names: {"en": "Mumbai", "tr": "Mumbai", "fr": "Bombay", "es": "Bombay", "de": "Mumbai", "ja": "ムンバイ", "zh": "孟买", "hi": "मुंबई", "ru": "Мумбаи", "ar": "بومباي", "it": "Mumbai", "pt": "Bombaim", "bn": "মুম্বই", "ur": "ممبئی", "tl": "Lungsod ng Mumbai", "vi": "Mumbai", "uk": "Мумбаї", "pl": "Mumbaj", "nl": "Bombay", "fi": "Mumbai", "da": "Mumbai", "no": "Mumbai", "sv": "Bombay", "ha": "Mumbai", "ta": "மும்பை", "ms": "Mumbai", "id": "Mumbai", "jv": "Mumbai", "su": "Mumbai", "hu": "Mumbai", "cs": "Bombaj", "el": "Βομβάη", "ro": "Mumbay", "fa": "بمبئی", "th": "มุมไบ", "sw": "Mumbai", "az": "Mumbay", "kk": "Мумбай", "uz": "Mumbay", "ky": "Мумбай", "tk": "Mumbay", "ko": "뭄바이"} as Record<SupportedLanguage, string>,
    latitude: 19.076,
    longitude: 72.8777
  },
    {
    id: "seoul",
    defaultName: "Seoul, South Korea",
    names: {"en": "Seoul", "tr": "Seul", "fr": "Séoul", "es": "Seúl", "de": "Seoul", "ja": "ソウル特別市", "zh": "首尔特别市", "hi": "सियोल", "ru": "Сеул", "ar": "سيول", "it": "Seul", "pt": "Seul", "bn": "সিউল", "ur": "سیول", "tl": "Seoul", "vi": "Seoul", "uk": "Сеул", "pl": "Seul", "nl": "Seoel", "fi": "Soul", "da": "Seoul", "no": "Seoul", "sv": "Seoul", "ha": "Seoul", "ta": "சியோல்", "ms": "Seoul", "id": "Seoul", "jv": "Seoul", "su": "Seoul", "hu": "Szöul", "cs": "Soul", "el": "Σεούλ", "ro": "Seul", "fa": "سئول", "th": "โซล", "sw": "Seoul", "az": "Seoul", "kk": "Сеул", "uz": "Seoul", "ky": "Сеул", "tk": "Seoul", "ko": "서울특별시"} as Record<SupportedLanguage, string>,
    latitude: 37.5665,
    longitude: 126.978
  },
    {
    id: "toronto",
    defaultName: "Toronto, Canada",
    names: {"en": "Toronto", "tr": "Toronto", "fr": "Toronto", "es": "Toronto", "de": "Toronto", "ja": "トロント", "zh": "多伦多", "hi": "टोरण्टो", "ru": "Торонто", "ar": "تورونتو", "it": "Toronto", "pt": "Toronto", "bn": "টরোন্টো", "ur": "ٹورانٹو", "tl": "Toronto", "vi": "Toronto", "uk": "Торонто", "pl": "Toronto", "nl": "Toronto", "fi": "Toronto", "da": "Toronto", "no": "Toronto", "sv": "Toronto", "ha": "Toronto", "ta": "ரொறன்ரோ", "ms": "Toronto", "id": "Toronto", "jv": "Toronto", "su": "Toronto", "hu": "Toronto", "cs": "Toronto", "el": "Τορόντο", "ro": "Toronto", "fa": "تورنتو", "th": "โทรอนโต", "sw": "Toronto", "az": "Toronto", "kk": "Toronto", "uz": "Toronto", "ky": "Toronto", "tk": "Toronto", "ko": "토론토"} as Record<SupportedLanguage, string>,
    latitude: 43.7001,
    longitude: -79.4163
  },
    {
    id: "sydney",
    defaultName: "Sydney, Australia",
    names: {"en": "Sydney", "tr": "Sidney", "fr": "Sydney", "es": "Sídney", "de": "Sydney", "ja": "シドニー", "zh": "悉尼", "hi": "सिडनी", "ru": "Сидней", "ar": "سيدني", "it": "Sydney", "pt": "Sydney", "bn": "সিডনি", "ur": "سڈنی", "tl": "Sydney", "vi": "Sydney", "uk": "Сідней", "pl": "Sydney", "nl": "Sydney", "fi": "Sydney", "da": "Sydney", "no": "Sydney", "sv": "Sydney", "ha": "Sydney", "ta": "சிட்னி", "ms": "Sydney", "id": "Sydney", "jv": "Sydney", "su": "Sydney", "hu": "Sydney", "cs": "Sydney", "el": "Σίδνεϋ", "ro": "Sydney", "fa": "سیدنی", "th": "ซิดนีย์", "sw": "Sydney", "az": "Sidney", "kk": "Сидней", "uz": "Sidney", "ky": "Сидней", "tk": "Sidneý", "ko": "시드니"} as Record<SupportedLanguage, string>,
    latitude: -33.8678,
    longitude: 151.2073
  },
    {
    id: "amsterdam",
    defaultName: "Amsterdam, Netherlands",
    names: {"en": "Amsterdam", "tr": "Amsterdam", "fr": "Amsterdam", "es": "Ámsterdam", "de": "Amsterdam", "ja": "アムステルダム", "zh": "阿姆斯特丹", "hi": "ऐम्स्टर्डैम", "ru": "Амстердам", "ar": "أمستردام", "it": "Amsterdam", "pt": "Amsterdã", "bn": "আমস্টারডাম", "ur": "ایمسٹرڈیم", "tl": "Amsterdam", "vi": "Amsterdam", "uk": "Амстердам", "pl": "Amsterdam", "nl": "Amsterdam", "fi": "Amsterdam", "da": "Amsterdam", "no": "Amsterdam", "sv": "Amsterdam", "ha": "Amsterdam", "ta": "ஆம்ஸ்டர்டம்", "ms": "Amsterdam", "id": "Amsterdam", "jv": "Amsterdam", "su": "Amsterdam", "hu": "Amszterdam", "cs": "Amsterodam", "el": "Άμστερνταμ", "ro": "Amsterdam", "fa": "آمستردام", "th": "อัมสเตอร์ดัม", "sw": "Amsterdam", "az": "Amsterdam", "kk": "Амстердам", "uz": "Amsterdam", "ky": "Амстердам", "tk": "Amsterdam", "ko": "암스테르담"} as Record<SupportedLanguage, string>,
    latitude: 52.3676,
    longitude: 4.9041
  },
    {
    id: "madrid",
    defaultName: "Madrid, Spain",
    names: {"en": "Madrid", "tr": "Madrid", "fr": "Madrid", "es": "Madrid", "de": "Madrid", "ja": "マドリード市", "zh": "馬德里", "hi": "मद्रिद", "ru": "Мадрид", "ar": "مدريد", "it": "Madrid", "pt": "Madrid", "bn": "মাদ্রিদ", "ur": "میدرد", "tl": "Lungsod ng Madrid", "vi": "Madrid", "uk": "Мадрид", "pl": "Madryt", "nl": "Madrid", "fi": "Madrid", "da": "Madrid", "no": "Madrid", "sv": "Madrid", "ha": "Madrid", "ta": "மத்ரித்", "ms": "Madrid", "id": "Madrid", "jv": "Madrid", "su": "Madrid", "hu": "Madrid", "cs": "Madrid", "el": "Μαδρίτη", "ro": "Madrid", "fa": "مادرید", "th": "มาดริด", "sw": "Madrid", "az": "Madrid", "kk": "Мадрид", "uz": "Madrid", "ky": "Мадрид", "tk": "Madrid", "ko": "마드리드"} as Record<SupportedLanguage, string>,
    latitude: 40.4168,
    longitude: -3.7038
  },
    {
    id: "berlin",
    defaultName: "Berlin, Germany",
    names: {"en": "Berlin", "tr": "Berlin", "fr": "Berlin", "es": "Berlín", "de": "Berlin", "ja": "ベルリン", "zh": "柏林", "hi": "Berlin", "ru": "Берлин", "ar": "برلين", "it": "Berlino", "pt": "Berlim", "bn": "বার্লিন", "ur": "برلن", "tl": "Berlin", "vi": "Berlin", "uk": "Берлін", "pl": "Berlin", "nl": "Berlijn", "fi": "Berliini", "da": "Berlin", "no": "Berlin", "sv": "Berlin", "ha": "Berlin", "ta": "பெர்லின்", "ms": "Berlin", "id": "Berlin", "jv": "Berlin", "su": "Berlin", "hu": "Berlin", "cs": "Berlín", "el": "Βερολίνο", "ro": "Berlin", "fa": "برلین", "th": "เบอร์ลิน", "sw": "Berlin", "az": "Berlin", "kk": "Berlin", "uz": "Berlin", "ky": "Berlin", "tk": "Berlin", "ko": "베를린"} as Record<SupportedLanguage, string>,
    latitude: 52.5244,
    longitude: 13.4105
  },
    {
    id: "mecca",
    defaultName: "Mecca, Saudi Arabia",
    names: {"en": "Mecca", "tr": "Mekke", "fr": "La Mecque", "es": "La Meca", "de": "Mekka", "ja": "メッカ", "zh": "麦加", "hi": "मक्का", "ru": "Мекка", "ar": "مكة", "it": "La Mecca", "pt": "Meca", "bn": "মক্কা", "ur": "مکہ", "tl": "Mecca", "vi": "Mecca", "uk": "Мекка", "pl": "Mekka", "nl": "Mekka", "fi": "Mekka", "da": "Mekka", "no": "Mekka", "sv": "Mekka", "ha": "Makka", "ta": "மக்கா", "ms": "Mekah", "id": "Mekah", "jv": "Mekah", "su": "Mekah", "hu": "Mekka", "cs": "Mekka", "el": "Μέκκα", "ro": "Mecca", "fa": "مکه", "th": "เมกกะ", "sw": "Makka", "az": "Məkkə", "kk": "Мекке", "uz": "Makka", "ky": "Мекка", "tk": "Mekge", "ko": "메카"} as Record<SupportedLanguage, string>,
    latitude: 21.3891,
    longitude: 39.8579
  },
    {
    id: "doha",
    defaultName: "Doha, Qatar",
    names: {"en": "Doha", "tr": "Doha", "fr": "Doha", "es": "Doha", "de": "Doha", "ja": "ドーハ", "zh": "多哈", "hi": "दोहा", "ru": "Доха", "ar": "الدوحة", "it": "Doha", "pt": "Doha", "bn": "দোহা", "ur": "دوحہ", "tl": "Doha", "vi": "Doha", "uk": "Доха", "pl": "Ad-Dauha", "nl": "Doha", "fi": "Doha", "da": "Doha", "no": "Doha", "sv": "Doha", "ha": "Doha", "ta": "தோகா", "ms": "Doha", "id": "Doha", "jv": "Doha", "su": "Doha", "hu": "Doha", "cs": "Dauhá", "el": "Ντόχα", "ro": "Doha", "fa": "دوحه", "th": "โดฮา", "sw": "Doha", "az": "Doha", "kk": "Доха", "uz": "Doʻha", "ky": "Доха", "tk": "Doha", "ko": "도하"} as Record<SupportedLanguage, string>,
    latitude: 25.2854,
    longitude: 51.531
  },
    {
    id: "frankfurt",
    defaultName: "Frankfurt, Germany",
    names: {"en": "Frankfurt", "tr": "Frankfurt", "fr": "Francfort-sur-le-Main", "es": "Francfort", "de": "Frankfurt am Main", "ja": "フランクフルト・アム・マイン", "zh": "法蘭克福", "hi": "फ़्रैंकफ़र्ट", "ru": "Франкфурт", "ar": "فرانكفورت", "it": "Francoforte sul Meno", "pt": "Frankfurt am Main", "bn": "ফ্রাংকফুর্ট", "ur": "فرینکفرٹ", "tl": "Frankfurt am Main", "vi": "Frankfurt am Main", "uk": "Франкфурт-на-Майні", "pl": "Frankfurt nad Menem", "nl": "Frankfurt am Main", "fi": "Frankfurt am Main", "da": "Frankfurt am Main", "no": "Frankfurt am Main", "sv": "Frankfurt am Main", "ha": "Frankfurt am Main", "ta": "பிராங்பேர்ட்", "ms": "Frankfurt", "id": "Frankfurt am Main", "jv": "Frankfurt am Main", "su": "Frankfurt am Main", "hu": "Frankfurt am Main", "cs": "Frankfurt nad Mohanem", "el": "Φρανκφούρτη", "ro": "Frankfurt", "fa": "فرانکفورت", "th": "แฟรงก์เฟิร์ต", "sw": "Frankfurt am Main", "az": "Frankfurt", "kk": "Франкфурт", "uz": "Frankfurt", "ky": "Франкфурт", "tk": "Frankfurt", "ko": "프랑크푸르트"} as Record<SupportedLanguage, string>,
    latitude: 50.1109,
    longitude: 8.6821
  },
    {
    id: "munich",
    defaultName: "Munich, Germany",
    names: {"en": "Munich", "tr": "Münih", "fr": "Munich", "es": "Múnich", "de": "München", "ja": "ミュンヘン", "zh": "慕尼黑", "hi": "म्यूनिख", "ru": "Мюнхен", "ar": "ميونخ", "it": "Monaco di Baviera", "pt": "Munique", "bn": "মিউনিখ", "ur": "میونخ", "tl": "Lungsod ng München", "vi": "München", "uk": "Мюнхен", "pl": "Monachium", "nl": "München", "fi": "München", "da": "München", "no": "München", "sv": "München", "ha": "Munich", "ta": "மியூனிக்", "ms": "Munich", "id": "München", "jv": "Munich", "su": "Munich", "hu": "München", "cs": "Mnichov", "el": "Μόναχο", "ro": "München", "fa": "مونیخ", "th": "มิวนิก", "sw": "Munich", "az": "Münhen", "kk": "Мюнхен", "uz": "Munhen", "ky": "Munich", "tk": "Munich", "ko": "뮌헨"} as Record<SupportedLanguage, string>,
    latitude: 48.1374,
    longitude: 11.5755
  },
    {
    id: "vienna",
    defaultName: "Wien, Austria",
    names: {"en": "Vienna", "tr": "Viyana", "fr": "Vienne", "es": "Viena", "de": "Wien", "ja": "ウィーン", "zh": "維也納", "hi": "वियना", "ru": "Вена", "ar": "فيينا", "it": "Vienna", "pt": "Viena", "bn": "ভিয়েনা", "ur": "ویانا", "tl": "Vienna", "vi": "Vienna", "uk": "Відень", "pl": "Wiedeń", "nl": "Wenen", "fi": "Wien", "da": "Wien", "no": "Wien", "sv": "Wien", "ha": "Vienna", "ta": "வியன்னா", "ms": "Vienna", "id": "Vienna", "jv": "Vienna", "su": "Vienna", "hu": "Bécs", "cs": "Vídeň", "el": "Βιέννη", "ro": "Viena", "fa": "وین", "th": "เวียนนา", "sw": "Vienna", "az": "Vyana", "kk": "Вена", "uz": "Vena", "ky": "Вена", "tk": "Wena", "ko": "빈"} as Record<SupportedLanguage, string>,
    latitude: 48.2082,
    longitude: 16.3738
  },
    {
    id: "cairo",
    defaultName: "Cairo, Egypt",
    names: {"en": "Cairo", "tr": "Kahire", "fr": "Le Caire", "es": "Cairo", "de": "Kairo", "ja": "カイロ", "zh": "开罗", "hi": "काहिरा", "ru": "Каир", "ar": "القاهرة", "it": "Il Cairo", "pt": "Cairo", "bn": "কায়রো", "ur": "قاہرہ", "tl": "Lungsod ng Cairo", "vi": "Cairo", "uk": "Каїр", "pl": "Kair", "nl": "Caïro", "fi": "Kairo", "da": "Kairo", "no": "Kairo", "sv": "Kairo", "ha": "Cairo", "ta": "கெய்ரோ", "ms": "Kaherah", "id": "Kairo", "jv": "Kairo", "su": "Cairo", "hu": "Kairó", "cs": "Káhira", "el": "Κάιρο", "ro": "Cairo", "fa": "قاهره", "th": "ไคโร", "sw": "Kairo", "az": "Qahirə", "kk": "Cairo", "uz": "Cairo", "ky": "Cairo", "tk": "Cairo", "ko": "카이로"} as Record<SupportedLanguage, string>,
    latitude: 30.0444,
    longitude: 31.2357
  },
    {
    id: "buenosaires",
    defaultName: "Buenos Aires, Argentina",
    names: {"en": "Buenos Aires", "tr": "Buenos Aires", "fr": "Buenos Aires", "es": "Buenos Aires", "de": "Buenos Aires", "ja": "ブエノスアイレス", "zh": "布宜诺斯艾利斯", "hi": "ब्युएनॉस एरीस", "ru": "Буэнос-Айрес", "ar": "بوينس آيرس", "it": "Buenos Aires", "pt": "Buenos Aires", "bn": "বুয়েনোস আইরেস", "ur": "بیونس آئرس", "tl": "Lungsod ng Buenos Aires", "vi": "Buenos Aires", "uk": "Буенос-Айрес", "pl": "Buenos Aires", "nl": "Buenos Aires", "fi": "Buenos Aires", "da": "Buenos Aires", "no": "Buenos Aires", "sv": "Buenos Aires", "ha": "Buenos Aires", "ta": "புவெனஸ் ஐரிஸ்", "ms": "Buenos Aires", "id": "Buenos Aires", "jv": "Buenos Aires", "su": "Buenos Aires", "hu": "Buenos Aires", "cs": "Buenos Aires", "el": "Μπουένος Άιρες", "ro": "Buenos Aires", "fa": "بوئنوس آیرس", "th": "บัวโนสไอเรส", "sw": "Buenos Aires", "az": "Buenos Ayres", "kk": "Buenos Aires", "uz": "Buenos Aires", "ky": "Буэнос-Айрес", "tk": "Buenos-Aýres", "ko": "부에노스아이레스"} as Record<SupportedLanguage, string>,
    latitude: -34.6037,
    longitude: -58.3816
  },
    {
    id: "mexicocity",
    defaultName: "Mexico City, Mexico",
    names: {"en": "Mexico City", "tr": "Meksiko", "fr": "Mexico", "es": "Ciudad de México", "de": "Mexiko-Stadt", "ja": "メキシコシティ", "zh": "墨西哥城", "hi": "मेक्सिको सिटी", "ru": "Мехико", "ar": "مدينة مكسيكو", "it": "Città del Messico", "pt": "Cidade do México", "bn": "মেক্সিকো সিটি", "ur": "میکسیکو شہر", "tl": "Lungsod ng México", "vi": "Thành phố Mexico", "uk": "Мехіко", "pl": "Meksyk", "nl": "Mexico-stad", "fi": "México", "da": "Mexico City", "no": "Mexico by", "sv": "Mexico City", "ha": "Mexico City", "ta": "மெக்சிகோ நகரம்", "ms": "Mexico City", "id": "Kota Meksiko", "jv": "Mexico City", "su": "Mexico City", "hu": "Mexikóváros", "cs": "Ciudad de México", "el": "Πόλη του Μεξικού", "ro": "Ciudad de México", "fa": "مکزیکو سیتی", "th": "เม็กซิโกซิตี", "sw": "Jiji la Meksiko", "az": "Meksika", "kk": "Мехико", "uz": "Mexiko", "ky": "Мехико", "tk": "Meksiko", "ko": "멕시코시티"} as Record<SupportedLanguage, string>,
    latitude: 19.4326,
    longitude: -99.1332
  },
    {
    id: "newdelhi",
    defaultName: "New Delhi, India",
    names: {"en": "New Delhi", "tr": "Yeni Delhi", "fr": "New Delhi", "es": "Nueva Delhi", "de": "Neu-Delhi", "ja": "ニューデリー", "zh": "新德里", "hi": "नई दिल्ली", "ru": "Нью-Дели", "ar": "دلهي الجديدة", "it": "Nuova Delhi", "pt": "Nova Deli", "bn": "নয়া দিল্লী", "ur": "نئی دہلی", "tl": "New Delhi", "vi": "New Delhi", "uk": "Нью-Делі", "pl": "Nowe Delhi", "nl": "New Delhi", "fi": "New Delhi", "da": "New Delhi", "no": "New Delhi", "sv": "New Delhi", "ha": "New Delhi", "ta": "புது தில்லி", "ms": "New Delhi", "id": "New Delhi", "jv": "New Delhi", "su": "New Delhi", "hu": "Újdelhi", "cs": "Nové Dillí", "el": "Νέο Δελχί", "ro": "New Delhi", "fa": "دهلی نو", "th": "นิวเดลี", "sw": "New Delhi", "az": "Yeni Dehli", "kk": "Жаңа Дели", "uz": "Yangi Dehli", "ky": "Жаңы Дели", "tk": "Nýu-Deli", "ko": "뉴델리"} as Record<SupportedLanguage, string>,
    latitude: 28.6139,
    longitude: 77.209
  },
    {
    id: "riodejaneiro",
    defaultName: "Rio de Janeiro, Brazil",
    names: {"en": "Rio de Janeiro", "tr": "Rio de Janeiro", "fr": "Rio de Janeiro", "es": "Río de Janeiro", "de": "Rio de Janeiro", "ja": "リオデジャネイロ", "zh": "里约热内卢", "hi": "रियो डि जेनेरो", "ru": "Рио-де-Жанейро", "ar": "ريو دي جانيرو", "it": "Rio de Janeiro", "pt": "Rio de Janeiro", "bn": "রিও দি জেনেরিও", "ur": "ریو دے جینیرو", "tl": "Rio de Janeiro", "vi": "Rio de Janeiro", "uk": "Ріо-де-Жанейро", "pl": "Rio de Janeiro", "nl": "Rio de Janeiro", "fi": "Rio de Janeiro", "da": "Rio de Janeiro", "no": "Rio de Janeiro", "sv": "Rio de Janeiro", "ha": "Rio de Janeiro", "ta": "இரியோ டி செனீரோ", "ms": "Rio de Janeiro", "id": "Rio de Janeiro", "jv": "Rio de Janeiro", "su": "Rio de Janeiro", "hu": "Rio de Janeiro", "cs": "Rio de Janeiro", "el": "Ρίο ντε Τζανέιρο", "ro": "Rio de Janeiro", "fa": "ریو دو ژانیرو", "th": "รัฐรีโอเดจาเนโร", "sw": "Rio de Janeiro", "az": "Rio-de-Janeyro", "kk": "Рио-де-Жанейро", "uz": "Rio-de-Janeyro", "ky": "Рио-де-Жанейро", "tk": "Rio-de-Žaneýro", "ko": "리우데자네이루"} as Record<SupportedLanguage, string>,
    latitude: -22.9068,
    longitude: -43.1729
  },
    {
    id: "capetown",
    defaultName: "Cape Town, South Africa",
    names: {"en": "Cape Town", "tr": "Cape Town", "fr": "Le Cap", "es": "Ciudad del Cabo", "de": "Kapstadt", "ja": "ケープタウン", "zh": "開普敦", "hi": "केपटाउन", "ru": "Кейптаун", "ar": "كيب تاون", "it": "Città del Capo", "pt": "Cidade do Cabo", "bn": "কেপ টাউন", "ur": "کیپ ٹاؤن", "tl": "Cape Town", "vi": "Cape Town", "uk": "Кейптаун", "pl": "Kapsztad", "nl": "Kaapstad", "fi": "Kapkaupunki", "da": "Kapstaden", "no": "Cape Town", "sv": "Kapstaden", "ha": "Cape Town", "ta": "கேப் டவுன்", "ms": "Cape Town", "id": "Cape Town", "jv": "Cape Town", "su": "Cape Town", "hu": "Fokváros", "cs": "Kapské Město", "el": "Κέιπ Τάουν", "ro": "Cape Town", "fa": "کیپ‌تاون", "th": "เคปทาวน์", "sw": "Cape Town", "az": "Keyptaun", "kk": "Кейптаун", "uz": "Keyptaun", "ky": "Кейптаун", "tk": "Keýptaun", "ko": "케이프타운"} as Record<SupportedLanguage, string>,
    latitude: -33.9249,
    longitude: 18.4241
  },
    {
    id: "lisbon",
    defaultName: "Lisbon, Portugal",
    names: {"en": "Lisbon", "tr": "Lizbon", "fr": "Lisbonne", "es": "Lisboa", "de": "Lissabon", "ja": "リスボン", "zh": "里斯本", "hi": "लिस्बन", "ru": "Лиссабон", "ar": "لشبونة", "it": "Lisbona", "pt": "Lisboa", "bn": "লিসবন", "ur": "لزبن", "tl": "Lisbon", "vi": "Lisboa", "uk": "Лісабон", "pl": "Lizbona", "nl": "Lissabon", "fi": "Lissabon", "da": "Lissabon", "no": "Lisboa", "sv": "Lissabon", "ha": "Lisbon", "ta": "லிஸ்பன்", "ms": "Lisbon", "id": "Lisboa", "jv": "Lisbon", "su": "Lisbon", "hu": "Lisszabon", "cs": "Lisabon", "el": "Λισαβώνα", "ro": "Lisabona", "fa": "لیسبون", "th": "ลิสบอน", "sw": "Lisbon", "az": "Lissabon", "kk": "Лиссабон", "uz": "Lissabon", "ky": "Лиссабон", "tk": "Lissabon", "ko": "리스본"} as Record<SupportedLanguage, string>,
    latitude: 38.7223,
    longitude: -9.1393
  },
    {
    id: "venice",
    defaultName: "Venezia, Italy",
    names: {"en": "Venice", "tr": "Venedik", "fr": "Venise", "es": "Venecia", "de": "Venedig", "ja": "ヴェネツィア", "zh": "威尼斯", "hi": "वेनिस", "ru": "Венеция", "ar": "البندقية", "it": "Venezia", "pt": "Veneza", "bn": "ভেনিস", "ur": "وینس", "tl": "Venecia", "vi": "Venezia", "uk": "Венеція", "pl": "Wenecja", "nl": "Venetië", "fi": "Venetsia", "da": "Venedig", "no": "Venezia", "sv": "Venedig", "ha": "Venezia", "ta": "வெனிஸ்", "ms": "Venice", "id": "Venesia", "jv": "Venesia", "su": "Venice", "hu": "Velence", "cs": "Benátky", "el": "Βενετία", "ro": "Veneția", "fa": "ونیز", "th": "เวนิส", "sw": "Venice", "az": "Venesiya", "kk": "Венеция", "uz": "Venetsiya", "ky": "Венеция", "tk": "Wenesiýa", "ko": "베니스"} as Record<SupportedLanguage, string>,
    latitude: 45.4408,
    longitude: 12.3155
  },
    {
    id: "edinburgh",
    defaultName: "Edinburgh, United Kingdom",
    names: {"en": "Edinburgh", "tr": "Edinburgh", "fr": "Édimbourg", "es": "Edimburgo", "de": "Edinburgh", "ja": "エディンバラ", "zh": "爱丁堡", "hi": "एडिनबरा", "ru": "Эдинбург", "ar": "إدنبرة", "it": "Edimburgo", "pt": "Edimburgo", "bn": "এডিনবরা", "ur": "ایڈنبرا", "tl": "Edinburgh", "vi": "Edinburgh", "uk": "Единбург", "pl": "Edynburg", "nl": "Edinburgh", "fi": "Edinburgh", "da": "Edinburgh", "no": "Edinburgh", "sv": "Edinburgh", "ha": "Edinburgh", "ta": "எடின்பரோ", "ms": "Edinburgh", "id": "Edinburgh", "jv": "Edinburgh", "su": "Edinburgh", "hu": "Edinburgh", "cs": "Edinburgh", "el": "Εδιμβούργο", "ro": "Edinburgh", "fa": "ادینبرو", "th": "เอดินบะระ", "sw": "Edinburgh", "az": "Edinburq", "kk": "Эдинбург", "uz": "Edinburgh", "ky": "Edinburgh", "tk": "Edinburgh", "ko": "에든버러"} as Record<SupportedLanguage, string>,
    latitude: 55.9533,
    longitude: -3.1883
  },
    {
    id: "budapest",
    defaultName: "Budapest, Hungary",
    names: {"en": "Budapest", "tr": "Budapeşte", "fr": "Budapest", "es": "Budapest", "de": "Ofen-Pest", "ja": "ブダペスト", "zh": "布达佩斯", "hi": "बुडापेस्ट", "ru": "Будапешт", "ar": "بودابست", "it": "Budapest", "pt": "Budapeste", "bn": "বুদাপেস্ট", "ur": "بوداپست", "tl": "Budapest", "vi": "Budapest", "uk": "Будапешт", "pl": "Budapeszt", "nl": "Boedapest", "fi": "Budapest", "da": "Budapest", "no": "Budapest", "sv": "Budapest", "ha": "Budapest", "ta": "புடாபெஸ்ட்", "ms": "Budapest", "id": "Budapest", "jv": "Budapest", "su": "Budapest", "hu": "Budapest", "cs": "Budapešť", "el": "Βουδαπέστη", "ro": "Budapesta", "fa": "بوداپست", "th": "บูดาเปสต์", "sw": "Budapest", "az": "Budapeşt", "kk": "Будапешт", "uz": "Budapesht", "ky": "Budapest", "tk": "Budapest", "ko": "부다페스트"} as Record<SupportedLanguage, string>,
    latitude: 47.4979,
    longitude: 19.0402
  },
    {
    id: "warsaw",
    defaultName: "Warsaw, Poland",
    names: {"en": "Warsaw", "tr": "Varşova", "fr": "Varsovie", "es": "Varsovia", "de": "Warschau", "ja": "ワルシャワ", "zh": "華沙", "hi": "वारसॉ", "ru": "Варшава", "ar": "وارسو", "it": "Varsavia", "pt": "Varsóvia", "bn": "ওয়ারশ", "ur": "وارسا", "tl": "Warsaw", "vi": "Warszawa", "uk": "Варшава", "pl": "Warszawa", "nl": "Warschau", "fi": "Varsova", "da": "Warszawa", "no": "Warszawa", "sv": "Warszawa", "ha": "Warsaw", "ta": "வார்சா", "ms": "Warsaw", "id": "Warsawa", "jv": "Warsawa", "su": "Warsaw", "hu": "Varsó", "cs": "Varšava", "el": "Βαρσοβία", "ro": "Varșovia", "fa": "ورشو", "th": "วอร์ซอ", "sw": "Warsaw", "az": "Varşava", "kk": "Варшава", "uz": "Varshava", "ky": "Варшава", "tk": "Warşawa", "ko": "바르샤바"} as Record<SupportedLanguage, string>,
    latitude: 52.2297,
    longitude: 21.0122
  },
    {
    id: "marrakesh",
    defaultName: "Marakesh, Morocco",
    names: {"en": "Marrakesh", "tr": "Marakeş", "fr": "Marrakech", "es": "Marrakech", "de": "Marrakesch", "ja": "マラケシュ", "zh": "马拉喀什", "hi": "मराकेश", "ru": "Марракеш", "ar": "مراكش", "it": "Marrakech", "pt": "Marraquexe", "bn": "মারাকেশ", "ur": "مراکش", "tl": "Marrakesh", "vi": "Marrakesh", "uk": "Марракеш", "pl": "Marrakesz", "nl": "Marrakesh", "fi": "Marrakech", "da": "Marrakesh", "no": "Marrakech", "sv": "Marrakech", "ha": "Marrakesh", "ta": "மராகேஷ்", "ms": "Marrakesh", "id": "Marrakesh", "jv": "Marrakesh", "su": "Marrakesh", "hu": "Marrákes", "cs": "Marrákeš", "el": "Μαρακές", "ro": "Marrakech", "fa": "مراکش", "th": "มาร์ราเกช", "sw": "Marrakesh", "az": "Marrakeş", "kk": "Марракеш", "uz": "Marrakesh", "ky": "Марракеш", "tk": "Marrakeş", "ko": "마라케시"} as Record<SupportedLanguage, string>,
    latitude: 31.6295,
    longitude: -7.9811
  },
    {
    id: "auckland",
    defaultName: "Auckland, New Zealand",
    names: {"en": "Auckland", "tr": "Auckland", "fr": "Auckland", "es": "Auckland", "de": "Auckland", "ja": "オークランド", "zh": "奧克蘭都會區", "hi": "ऑक्लैण्ड", "ru": "Окленд", "ar": "أوكلاند", "it": "Auckland", "pt": "Auckland", "bn": "অকল্যান্ড", "ur": "آکلینڈ", "tl": "Auckland", "vi": "Auckland", "uk": "Окленд", "pl": "Auckland", "nl": "Auckland", "fi": "Auckland", "da": "Auckland", "no": "Auckland", "sv": "Auckland", "ha": "Auckland", "ta": "ஆக்லன்ட்", "ms": "Auckland", "id": "Auckland", "jv": "Auckland", "su": "Auckland", "hu": "Auckland", "cs": "Auckland", "el": "Ώκλαντ", "ro": "Auckland", "fa": "آوکلند", "th": "โอคแลนด์", "sw": "Auckland", "az": "Auckland", "kk": "Auckland", "uz": "Auckland", "ky": "Auckland", "tk": "Auckland", "ko": "오클랜드"} as Record<SupportedLanguage, string>,
    latitude: -36.8485,
    longitude: 174.7633
  }
];
