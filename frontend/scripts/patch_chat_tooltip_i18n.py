#!/usr/bin/env python3
"""One-off patch: add chat.tooltipWear + chat.tooltipRainTomorrow to all locale JSON files."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "public" / "locales"

# Tailored short prompts: (what to wear today, will it rain tomorrow)
TRANSLATIONS: dict[str, tuple[str, str]] = {
    "en": ("What should I wear today?", "Will it rain tomorrow?"),
    "tr": ("Bugün ne giymeliyim?", "Yarın yağmur yağacak mı?"),
    "de": ("Was soll ich heute anziehen?", "Wird es morgen regnen?"),
    "fr": ("Que dois-je porter aujourd'hui ?", "Est-ce qu'il pleuvra demain ?"),
    "es": ("¿Qué debería ponerme hoy?", "¿Lloverá mañana?"),
    "it": ("Cosa mi metto oggi?", "Pioverà domani?"),
    "pt": ("O que devo vestir hoje?", "Vai chover amanhã?"),
    "nl": ("Wat moet ik vandaag aantrekken?", "Gaat het morgen regenen?"),
    "pl": ("Co powinienem dziś założyć?", "Czy jutro będzie padać?"),
    "ru": ("Что мне надеть сегодня?", "Завтра будет дождь?"),
    "uk": ("Що вдягнути сьогодні?", "Чи буде завтра дощ?"),
    "ar": ("ماذا أرتدي اليوم؟", "هل ستمطر غدًا؟"),
    "hi": ("आज मुझे क्या पहनना चाहिए?", "कल बारिश होगी?"),
    "bn": ("আজ আমার কী পরা উচিত?", "কাল বৃষ্টি হবে?"),
    "ur": ("آج میں کیا پہنوں؟", "کل بارش ہوگی؟"),
    "fa": ("امروز چه بپوشم؟", "فردا باران می‌بارد؟"),
    "zh": ("今天穿什么？", "明天会下雨吗？"),
    "ja": ("今日は何を着ればいい？", "明日は雨が降りますか？"),
    "ko": ("오늘 뭐 입을까요?", "내일 비 올까요?"),
    "vi": ("Hôm nay tôi nên mặc gì?", "Ngày mai có mưa không?"),
    "th": ("วันนี้ควรใส่อะไรดี?", "พรุ่งนี้จะฝนตกไหม?"),
    "id": ("Apa yang harus saya pakai hari ini?", "Apakah besok akan hujan?"),
    "ms": ("Apa yang patut saya pakai hari ini?", "Adakah hujan esok?"),
    "tl": ("Ano ang dapat kong suotin ngayon?", "Uulan ba bukas?"),
    "sv": ("Vad ska jag ha på mig idag?", "Kommer det regna imorgon?"),
    "no": ("Hva skal jeg ha på meg i dag?", "Blir det regn i morgen?"),
    "da": ("Hvad skal jeg have på i dag?", "Regner det i morgen?"),
    "fi": ("Mitä minun kannattaa pitää tänään?", "Sataako huomenna?"),
    "cs": ("Co si mám dnes obléknout?", "Bude zítra pršet?"),
    "el": ("Τι να φορέσω σήμερα;", "Θα βρέξει αύριο;"),
    "ro": ("Ce să port azi?", "Va ploua mâine?"),
    "hu": ("Mit vegyek fel ma?", "Holnap esni fog?"),
    "az": ("Bu gün nə geyinim?", "Sabah yağış olacaq?"),
    "kk": ("Бүгін не кию керек?", "Ертең жаңбыр жауады ма?"),
    "ky": ("Бүгүн эмне кийсем?", "Эртең жамгыр жаайбы?"),
    "uz": ("Bugun nima kiyishim kerak?", "Ertaga yomg‘ir yog‘adimi?"),
    "tk": ("Bu gün näme geýmeli?", "Ertir ýagajakmy?"),
    "sw": ("Nivae nini leo?", "Kesho mvua itanyesha?"),
    "ha": ("Me zan sa da kyau yau?", "Gobe zai yi ruwan sama?"),
    "jv": ("Apa sing kudu tak paké dina iki?", "Apa besok udan?"),
    "su": ("Naon anu kudu dipaké ayeuna?", "Naha énjing hujan?"),
    "ta": ("இன்று என்ன உடுப்பது?", "நாளை மழை பெய்யுமா?"),
}


def main() -> None:
    for path in sorted(ROOT.glob("*/translation.json")):
        code = path.parent.name
        wear, rain = TRANSLATIONS.get(
            code,
            TRANSLATIONS["en"],
        )
        data = json.loads(path.read_text(encoding="utf-8"))
        chat = data.setdefault("chat", {})
        chat.pop("tooltipAskWeather", None)
        chat.pop("tooltipWhatToWear", None)
        chat["tooltipWear"] = wear
        chat["tooltipRainTomorrow"] = rain
        text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        path.write_text(text, encoding="utf-8")
        print(f"updated {code}")


if __name__ == "__main__":
    main()
