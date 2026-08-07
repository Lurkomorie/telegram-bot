"""Scene evaluation harness for the image-prompt brain.

Runs a fixed suite of roleplay turns through the real Brain 3 + tag policy and
scores each result with deterministic rules (plus an optional LLM judge). Used
to find prompt defects by measurement instead of guesswork, and to prove a
prompt edit actually helped rather than moved the failure elsewhere.

Usage:  python eval_harness.py [--judge] [--repeat N] [--only substring]
"""
import os, sys, json, asyncio, argparse, statistics, collections

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
# Settings() forbids unknown keys and the repo .env carries some, so import it
# from a directory without a .env, then move to the repo root for config/*.yaml.
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import app.settings  # noqa: F401
os.chdir(REPO_ROOT)

from app.settings import load_configs, get_app_config
load_configs()
from app.core.brains.image_prompt_engineer import (
    generate_image_plan, assemble_final_prompt, prefetch_focus_tags,
)
from app.core.llm_openrouter import generate_text

PERSONA = {
    "id": "eval", "name": "Airi",
    "image_prompt": "1girl, cat_ears, long_hair, silver_hair, green_eyes, medium_breasts",
    "prompt": "playful catgirl companion, teasing and affectionate",
}

NEG_FACE = {"angry","frown","v-shaped_eyebrows","clenched_teeth","glaring","scowl","annoyed","pout",
            "cheek_puff","sad","downcast_eyes","crying","tears","teary_eyes","streaming_tears",
            "crying_with_eyes_open","scared","wide-eyed","trembling","nervous","disgust","grimace",
            "expressionless","serious","tired","sleepy","embarrassed"}
POS_FACE = {"smile","light_smile","slight_smile","grin","happy","seductive_smile",":d","laughing"}
GARMENTS = {"dress","sundress","shirt","blouse","skirt","miniskirt","jeans","shorts","bikini","lingerie",
            "bra","panties","negligee","swimsuit","underwear","robe","jacket","sweater","hoodie","coat",
            "kimono","apron","bodysuit","leotard","corset","camisole","nightgown","pajamas","pants",
            "trousers","leggings","uniform","tights","pantyhose","stockings"}
NUDE = {"nude","naked","topless","bottomless"}
PARTNER_ACTS = {"sex","vaginal","anal","oral","fellatio","cunnilingus","paizuri","handjob","penis",
                "cowgirl_position","girl_on_top","straddling","riding","penetration","deepthroat"}
BANNED = {"wide_shot","long_shot","multiple_views"}


def state(**kw):
    base = dict(relationshipStage="lover", emotions="neutral", moodNotes="evening, quiet",
                location="bedroom", description="talking", aiClothing="white cotton sundress",
                userClothing="unknown")
    base.update(kw)
    return " | ".join(f'{k}="{v}"' for k, v in base.items())


# Each case: what the turn is, and what must / must not appear in the tags.
CASES = [
    # ---------- emotions ----------
    dict(id="emo_angry", state=state(emotions="angry, hurt, betrayed", description="confronting him"),
         dialogue="_Резко отдёргиваю руку, скрестив руки на груди_ *Ты серьёзно?! Я ждала весь вечер!*",
         user="не злись, покажи себя", expect_face="negative"),
    dict(id="emo_crying", state=state(emotions="sad, heartbroken", description="crying on the bed"),
         dialogue="_Слёзы катятся по щекам, прячу лицо в коленях_ *Не смотри на меня сейчас...*",
         user="что случилось", expect_face="negative"),
    dict(id="emo_jealous", state=state(emotions="annoyed, jealous", description="sulking"),
         dialogue="_Надуваю щёки и отворачиваюсь_ *Да не ревную я! Просто... кто она?*",
         user="покажи лицо", expect_face="negative"),
    dict(id="emo_scared", state=state(emotions="scared, anxious", description="hearing a noise outside"),
         dialogue="_Вздрагиваю и хватаю тебя за руку, глаза расширены_ *Там кто-то есть... мне страшно!*",
         user="что там", expect_face="negative"),
    dict(id="emo_shy", state=state(emotions="embarrassed, flustered", relationshipStage="crush"),
         dialogue="_Краснею и отвожу взгляд, теребя рукав_ *Н-не смотри так пристально...*",
         user="ты красивая", expect_face="negative"),
    dict(id="emo_cold", state=state(emotions="cold, distant", description="giving him the silent treatment"),
         dialogue="_Смотрю в окно, лицо ничего не выражает_ *Мне нечего сказать.*",
         user="ну поговори со мной", expect_face="negative"),
    dict(id="emo_happy", state=state(emotions="happy, affectionate", description="snuggling"),
         dialogue="_Прижимаюсь и довольно мурлычу_ *Мне так хорошо с тобой...*",
         user="как ты?", expect_face="positive"),
    dict(id="emo_excited", state=state(emotions="excited, playful", description="jumping around"),
         dialogue="_Подпрыгиваю от радости, хвост колышется_ *Правда?! Ты серьёзно?!*",
         user="я купил тебе подарок", expect_face="positive"),
    dict(id="emo_aroused", state=state(emotions="aroused, seductive", aiClothing="black lace lingerie"),
         dialogue="_Медленно провожу пальцами по бедру, дыхание сбивается_ *Иди сюда...*",
         user="ты меня заводишь", expect_face="any"),

    # ---------- clothing continuity ----------
    dict(id="cloth_keep", state=state(aiClothing="white cotton sundress", description="sitting in a cafe", location="cafe"),
         dialogue="_Помешиваю кофе ложечкой, улыбаюсь_ *Здесь уютно, правда?*",
         user="сфоткайся", prev="1girl, solo, pov, close-up, sitting, white_sundress, barefoot, cafe, indoors, sunlight",
         expect_keep_outfit="white_sundress"),
    dict(id="cloth_keep_bikini", state=state(aiClothing="blue bikini", location="beach", description="on the beach"),
         dialogue="_Потягиваюсь на песке под солнцем_ *Вода тёплая, пошли купаться!*",
         user="покажи себя", prev="1girl, solo, pov, close-up, standing, blue_bikini, beach, outdoors, sunlight",
         expect_keep_outfit="blue_bikini"),
    dict(id="cloth_undress", state=state(aiClothing="white cotton sundress", description="undressing"),
         dialogue="_Стягиваю платье через голову, оно падает на пол_ *Так лучше?*",
         user="раздевайся", prev="1girl, solo, pov, close-up, white_sundress, bedroom",
         expect_nude=True),
    dict(id="cloth_stay_nude", state=state(aiClothing="white blouse, black tights", description="in bed with him"),
         dialogue="_Лежу рядом, вожу пальцем по твоей груди_ *Мне так хорошо...*",
         user="иди ко мне", prev="1girl, solo, pov, close-up, nude, nipples, on_bed, bedroom",
         expect_nude=True),
    dict(id="cloth_redress", state=state(aiClothing="completely naked", description="getting dressed for work"),
         dialogue="_Натягиваю блузку и застёгиваю пуговицы_ *Всё, мне пора бежать.*",
         user="одевайся, опоздаешь", prev="1girl, solo, pov, close-up, nude, bedroom",
         expect_nude=False, expect_dressed=True),

    # ---------- partner / solo ----------
    dict(id="partner_sex", state=state(emotions="aroused", aiClothing="completely naked", description="having sex"),
         dialogue="_Насаживаюсь на тебя сверху, твои руки на моих бёдрах_ *Да, еби меня!*",
         user="трахни меня", prev="1girl, solo, pov, close-up, nude, on_bed",
         expect_partner=True),
    dict(id="partner_oral", state=state(emotions="aroused", aiClothing="completely naked", description="oral sex"),
         dialogue="_Опускаюсь и беру его в рот, глядя тебе в глаза_ *Ммм...*",
         user="отсоси", prev="1girl, solo, pov, close-up, nude, bedroom",
         expect_partner=True),
    dict(id="partner_kiss", state=state(emotions="loving", description="kissing him"),
         dialogue="_Обнимаю за шею и целую тебя в губы_ *Я скучала...*",
         user="поцелуй меня", expect_partner=True),
    dict(id="solo_selfie", state=state(emotions="playful", aiClothing="oversized shirt"),
         dialogue="_Кручусь перед зеркалом, показывая себя_ *Ну как тебе?*",
         user="пришли селфи", expect_partner=False),
    dict(id="solo_undress", state=state(emotions="seductive", aiClothing="black lace lingerie"),
         dialogue="_Медленно спускаю бретельку с плеча_ *Смотри внимательно...*",
         user="разденься для меня", expect_partner=False),

    # ---------- refusal / deflection ----------
    dict(id="refusal", state=state(emotions="uncomfortable", relationshipStage="friend", aiClothing="jeans, sweater"),
         dialogue="_Отшатываюсь и прикрываюсь руками_ *Не буду я этого делать! Мы же на людях!*",
         user="разденься прямо здесь", expect_face="negative", expect_nude=False),

    # ---------- explicit body focus ----------
    dict(id="focus_feet", state=state(emotions="playful", aiClothing="completely naked"),
         dialogue="_Вытягиваю ноги в твою сторону, шевеля пальчиками_ *Такие?*",
         user="покажи свои ножки", expect_tags={"feet"}),
    dict(id="focus_ass", state=state(emotions="seductive", aiClothing="completely naked"),
         dialogue="_Поворачиваюсь спиной и прогибаюсь_ *Нравится вид?*",
         user="покажи попку", expect_tags={"ass"}),

    # ---------- traps found in production ----------
    # "Ты серьёзно?!" is delight, not a serious face.
    dict(id="trap_seriously", state=state(emotions="excited, playful", description="reacting to good news"),
         dialogue="_Подпрыгиваю, хвост колышется_ *Ты серьёзно?! Не может быть!*",
         user="я взял отпуск", expect_face="positive"),
    # An angry scene where the model loves to add a smirk.
    dict(id="trap_angry_smirk", state=state(emotions="angry, furious", description="shouting at him"),
         dialogue="_Швыряю подушку в тебя_ *Убирайся! Видеть тебя не хочу!*",
         user="да ладно тебе", expect_face="negative"),
    # Sad text, warm mood value — mood must not override the words.
    dict(id="trap_sad_high_mood", state=state(emotions="sad, disappointed", description="he forgot her birthday"),
         dialogue="_Опускаю взгляд, губы дрожат_ *Ты... забыл. Опять.*",
         user="прости", mood=95, expect_face="negative"),
    # Sex right after a dressed frame: nudity must win over the outfit anchor.
    dict(id="trap_sex_from_dressed", state=state(emotions="aroused", location="office", aiClothing="white blouse, dark skirt", description="having sex"),
         dialogue="_Стягиваю с себя всё и притягиваю тебя_ *Возьми меня, сейчас же!*",
         user="иди сюда", prev="1girl, solo, pov, close-up, white_blouse, dark_skirt, office, indoors",
         expect_partner=True, expect_nude=True),
    # Getting dressed after sex releases the nude lock.
    dict(id="trap_dress_after_sex", state=state(emotions="content", aiClothing="completely naked", description="getting dressed"),
         dialogue="_Накидываю халат на плечи и завязываю пояс_ *Пойду сварю кофе.*",
         user="ты куда", prev="1girl, solo, pov, close-up, nude, on_bed, bedroom",
         expect_nude=False, expect_dressed=True),
    # Colour must survive a pose change in the same outfit.
    dict(id="trap_colour_survives", state=state(aiClothing="red silk dress", location="restaurant", description="leaning over the table"),
         dialogue="_Наклоняюсь через стол, платье натягивается_ *Смотришь на меня?*",
         user="сфоткай себя", prev="1girl, solo, pov, close-up, sitting, red_silk_dress, restaurant, indoors, candle",
         expect_keep_outfit="red_silk_dress"),
]


def check(case, tags: set, neg: str) -> list:
    """Deterministic rules. Returns a list of failure strings (empty = pass)."""
    fails = []
    if not {"1girl"} & tags:
        fails.append("нет 1girl")
    if tags & BANNED:
        fails.append(f"запрещённые теги: {sorted(tags & BANNED)}")

    face = case.get("expect_face")
    if face == "negative":
        if not tags & NEG_FACE:
            fails.append("нет негативных тегов лица")
        if tags & POS_FACE:
            fails.append(f"улыбка в негативной сцене: {sorted(tags & POS_FACE)}")
    elif face == "positive":
        if not tags & POS_FACE:
            fails.append("нет позитивных тегов лица")
        if tags & (NEG_FACE - {"embarrassed", "blush", "nervous"}):
            fails.append(f"негативное лицо в позитивной сцене: {sorted(tags & NEG_FACE)}")

    if case.get("expect_keep_outfit"):
        want = case["expect_keep_outfit"]
        if want not in tags:
            worn = sorted(t for t in tags if any(p in GARMENTS for p in t.split("_")))
            fails.append(f"наряд не сохранён (ждали {want}, есть {worn or 'ничего'})")

    if case.get("expect_nude") is True:
        if not any(any(p in NUDE for p in t.split("_")) for t in tags):
            fails.append("нет nude")
        worn = [t for t in tags if any(p in GARMENTS for p in t.split("_"))]
        if worn:
            fails.append(f"одежда в голой сцене: {sorted(worn)}")
    if case.get("expect_nude") is False and case.get("expect_dressed"):
        if not any(any(p in GARMENTS for p in t.split("_")) for t in tags):
            fails.append("персонаж не одет, хотя одевается")
        if any(any(p in NUDE for p in t.split("_")) for t in tags):
            fails.append("nude, хотя одевается")

    if case.get("expect_partner") is True:
        if "1boy" not in tags:
            fails.append("нет 1boy в сцене с партнёром")
        if "solo" in tags:
            fails.append("solo вместе с партнёром")
        if "futanari" not in neg:
            fails.append("нет анти-феминизации в negative")
    if case.get("expect_partner") is False:
        if "1boy" in tags:
            fails.append("1boy в соло-сцене")
        if "solo" not in tags:
            fails.append("нет solo в соло-сцене")

    for want in case.get("expect_tags", set()):
        if not any(want in t for t in tags):
            fails.append(f"нет тега про '{want}'")
    return fails


JUDGE_PROMPT = """You grade danbooru tag lists for an anime image generator.
You get the roleplay turn the image must depict, and the tags produced.
Answer with JSON only: {"score": 1-5, "problem": "<one short phrase, or empty>"}
5 = the tags depict this exact moment (pose, mood, clothing state, who is in frame).
3 = broadly right but a detail contradicts the text.
1 = depicts something else entirely.

Judge fidelity to what the character SAYS AND DOES. Two caveats:
- The aiClothing field can be stale; the actions win. If she was undressed earlier
  or is having sex, nude tags are correct even when aiClothing still lists garments.
- The camera is the user's own eyes. A partner only needs 1boy/hetero when his body
  is genuinely in frame (sex, oral, kissing, an embrace) — not for a touch or a
  held hand. Nothing is missing merely because the user is not drawn.
Explicit content is expected and is never itself a problem."""


async def judge(case, plan: str) -> dict:
    try:
        out = await generate_text(
            messages=[{"role": "system", "content": JUDGE_PROMPT},
                      {"role": "user", "content":
                       f"SCENE STATE:\n{case['state']}\n\nCHARACTER SAYS/DOES:\n{case['dialogue']}\n\n"
                       f"USER ASKED:\n{case['user']}\n\nTAGS:\n{plan}"}],
            model="deepseek/deepseek-v3.2", temperature=0.0, max_tokens=120)
        txt = out[out.find("{"): out.rfind("}") + 1]
        return json.loads(txt)
    except Exception as e:
        return {"score": None, "problem": f"judge error: {e}"}


async def run_case(case, use_judge: bool):
    task = prefetch_focus_tags(case["user"])
    plan = await generate_image_plan(
        state=case["state"], dialogue_response=case["dialogue"], user_message=case["user"],
        persona=PERSONA, chat_history=[], previous_image_prompt=case.get("prev"),
        previous_image_meta={"source": "chat"}, context_summary=None,
        mood=case.get("mood", 60), purchases=[], precomputed_focus_tags=await task)
    pos, neg = assemble_final_prompt(plan, PERSONA["image_prompt"])
    tags = {t.strip().lower() for t in pos.split(",")}
    fails = check(case, tags, neg.lower())
    verdict = await judge(case, plan) if use_judge else {}
    return dict(id=case["id"], fails=fails, plan=plan, score=verdict.get("score"),
                problem=verdict.get("problem", ""))


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    cases = [c for c in CASES if args.only in c["id"]]
    jobs = [c for c in cases for _ in range(args.repeat)]
    sem = asyncio.Semaphore(6)

    async def guarded(c):
        async with sem:
            try:
                return await run_case(c, args.judge)
            except Exception as e:
                return dict(id=c["id"], fails=[f"ИСКЛЮЧЕНИЕ: {type(e).__name__}: {e}"], plan="", score=None, problem="")

    results = await asyncio.gather(*[guarded(c) for c in jobs])

    by_case = collections.defaultdict(list)
    for r in results:
        by_case[r["id"]].append(r)

    print(f"\n{'='*74}\nРЕЗУЛЬТАТЫ ({len(cases)} сцен × {args.repeat})\n{'='*74}")
    total_runs = 0
    total_ok = 0
    all_fails = collections.Counter()
    for cid, runs in by_case.items():
        ok = sum(1 for r in runs if not r["fails"])
        total_runs += len(runs); total_ok += ok
        scores = [r["score"] for r in runs if r["score"]]
        mark = "OK " if ok == len(runs) else "!! "
        s = f" судья {statistics.mean(scores):.1f}" if scores else ""
        print(f"{mark}{cid:18s} {ok}/{len(runs)}{s}")
        for r in runs:
            for f in r["fails"]:
                all_fails[f"{cid}: {f}"] += 1
            if r["problem"]:
                all_fails[f"{cid}: судья — {r['problem']}"] += 1
    print(f"\nИТОГО: {total_ok}/{total_runs} прогонов без нарушений "
          f"({100*total_ok/max(1,total_runs):.0f}%)")
    if all_fails:
        print("\nНАРУШЕНИЯ (по частоте):")
        for f, n in all_fails.most_common(40):
            print(f"  {n}×  {f}")
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_last.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)

asyncio.run(main())
