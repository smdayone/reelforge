#!/usr/bin/env python3
"""
ReelForge — AI Product Video Pipeline
Generates short-form marketing clips using fal.ai video models.

Usage: python3 main.py
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
import fal_client

import config
from utils.downloader import download_product_images, upload_to_fal
from utils.image_processor import process_all_references

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
PRODUCTS_DIR = BASE_DIR / "products"
LOGS_DIR = BASE_DIR / "logs"
LOG_FILE = LOGS_DIR / "generations.json"

# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def hr(char="─", width=62):
    print(char * width)

def header(title: str):
    hr("═")
    print(f"  {title}")
    hr("═")

def section(title: str):
    print(f"\n  ┌─ {title}")

def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"  › {prompt}{suffix}: ").strip()
    return val if val else default

def confirm(prompt: str) -> bool:
    ans = input(f"  › {prompt} (s/N): ").strip().lower()
    return ans in ("s", "si", "y", "yes")

def pause():
    input("\n  [Premi INVIO per continuare...]")

# ---------------------------------------------------------------------------
# API key
# ---------------------------------------------------------------------------

def load_api_key() -> str:
    load_dotenv(BASE_DIR / ".env")
    key = os.getenv("FAL_KEY", "").strip()
    if not key or key == "your_key_here":
        header("⚠  API KEY NON CONFIGURATA")
        print("  1. Apri il file .env nella cartella del progetto")
        print("  2. Sostituisci 'your_key_here' con la tua chiave fal.ai")
        print("  3. Ottieni la chiave su: https://fal.ai/dashboard/keys\n")
        sys.exit(1)
    os.environ["FAL_KEY"] = key
    return key

# ---------------------------------------------------------------------------
# Product management
# ---------------------------------------------------------------------------

def load_product(product_dir: Path) -> dict | None:
    meta = product_dir / "product.json"
    if not meta.exists():
        return None
    return json.loads(meta.read_text(encoding="utf-8"))


def select_product() -> tuple[dict, Path]:
    """List all products in /products and let user select one."""
    products = [
        (d, load_product(d))
        for d in sorted(PRODUCTS_DIR.iterdir())
        if d.is_dir() and (d / "product.json").exists()
    ]

    if not products:
        print("\n  [WARN] Nessun prodotto trovato in products/")
        print("  Crea una cartella products/<id>/ con un product.json al suo interno.\n")
        sys.exit(1)

    if len(products) == 1:
        d, p = products[0]
        print(f"\n  Prodotto caricato: {p['name']}")
        return p, d

    section("Seleziona prodotto")
    for i, (d, p) in enumerate(products, start=1):
        print(f"    {i}. {p['name']}")
        print(f"       {d.name} — {p.get('category', '')} — {p.get('created_at', '')}")

    while True:
        choice = ask("Prodotto (numero)")
        if choice.isdigit() and 1 <= int(choice) <= len(products):
            d, p = products[int(choice) - 1]
            return p, d
        print("    Scelta non valida.")


def add_new_product():
    """Interactive wizard to add a new product to the pipeline."""
    section("Nuovo prodotto")
    pid = ask("ID prodotto (es. sneakers-nike)").replace(" ", "-").lower()
    name = ask("Nome prodotto")
    category = ask("Categoria (es. audio/footwear)")
    style = ask("Stile / target audience")

    print("\n  Inserisci le URL delle immagini (una per riga, riga vuota per terminare):")
    urls = []
    while True:
        u = input("    URL: ").strip()
        if not u:
            break
        urls.append(u)

    product_dir = PRODUCTS_DIR / pid
    product_dir.mkdir(parents=True, exist_ok=True)
    for sub in ["inputs", "references", "outputs"]:
        (product_dir / sub).mkdir(exist_ok=True)

    meta = {
        "id": pid,
        "name": name,
        "style": style,
        "category": category,
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "image_urls": urls,
        "notes": "",
    }
    (product_dir / "product.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n  [OK] Prodotto '{name}' salvato in products/{pid}/")
    return meta, product_dir

# ---------------------------------------------------------------------------
# Image preparation
# ---------------------------------------------------------------------------

def menu_process_images(product: dict, product_dir: Path):
    """Download input images and generate processed references."""
    inputs_dir = product_dir / "inputs"
    refs_dir = product_dir / "references"
    inputs_dir.mkdir(exist_ok=True)
    refs_dir.mkdir(exist_ok=True)

    section("Preparazione immagini")
    print()

    # 1. Download
    print("  [1/2] Download immagini input...")
    saved = download_product_images(product, inputs_dir)
    if not saved:
        print("  [WARN] Nessuna immagine scaricata.")
        return

    # 2. Processing options
    print()
    remove_bg = confirm("Rimuovere background dalle immagini? (raccomandato)")
    remove_txt = confirm("Tentare rimozione testi/watermark?")
    white_bg = False
    if remove_bg:
        white_bg = confirm("Usare sfondo bianco (invece di trasparente)?")

    # 3. Process
    print("\n  [2/2] Processing immagini → references/...")
    refs = process_all_references(
        inputs_dir, refs_dir,
        remove_bg=remove_bg,
        remove_text=remove_txt,
        white_bg=white_bg,
    )
    print(f"\n  [OK] {len(refs)} reference immagini pronte in: {refs_dir.resolve()}")
    pause()

# ---------------------------------------------------------------------------
# Engine selection
# ---------------------------------------------------------------------------

def select_engine() -> dict:
    section("Seleziona motore video")
    print()
    for idx, eng in config.VIDEO_ENGINES.items():
        cost_str = f"${eng['cost_5s']:.2f}/5s"
        if "10" in eng["durations"]:
            cost_str += f" · ${eng['cost_10s']:.2f}/10s"
        print(f"  {idx}. {eng['label']:30s} {eng['quality']}  {cost_str}")
        print(f"     {eng['description']}")
        print()

    while True:
        choice = ask("Motore (1-6)", default="1")
        if choice in config.VIDEO_ENGINES:
            return config.VIDEO_ENGINES[choice]
        print("    Scelta non valida.")


def select_duration(engine: dict) -> str:
    durations = engine["durations"]
    if len(durations) == 1:
        print(f"  Durata fissa per questo motore: {durations[0]}s")
        return durations[0]

    section("Durata clip")
    for i, d in enumerate(durations, start=1):
        print(f"    {i}. {d} secondi")

    while True:
        choice = ask("Durata", default="1")
        if choice.isdigit() and 1 <= int(choice) <= len(durations):
            return durations[int(choice) - 1]
        # Allow direct input of seconds
        if choice in durations:
            return choice
        print("    Scelta non valida.")


def select_aspect_ratio(engine: dict) -> str:
    ratios = engine["aspect_ratios"]
    if len(ratios) == 1:
        return ratios[0]

    section("Aspect ratio")
    for i, r in enumerate(ratios, start=1):
        label = {"9:16": "Verticale (TikTok/Reels)", "16:9": "Orizzontale", "1:1": "Quadrato"}.get(r, r)
        print(f"    {i}. {r:6s} — {label}")

    while True:
        choice = ask("Ratio", default="1")
        if choice.isdigit() and 1 <= int(choice) <= len(ratios):
            return ratios[int(choice) - 1]
        if choice in ratios:
            return choice
        print("    Scelta non valida.")

# ---------------------------------------------------------------------------
# Image source selection
# ---------------------------------------------------------------------------

def select_image_source(product: dict, product_dir: Path) -> list[str]:
    """
    Returns list of image URLs (remote CJ URLs or uploaded fal.ai URLs
    from processed reference images).
    """
    refs_dir = product_dir / "references"
    refs = sorted([
        p for p in refs_dir.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    ]) if refs_dir.exists() else []

    section("Sorgente immagini")
    print(f"    1. URL originali CJ ({len(product['image_urls'])} immagini)")
    if refs:
        print(f"    2. Reference processed ({len(refs)} immagini — bg rimosso)")
    else:
        print(f"    2. Reference processed  [nessuna trovata — elabora prima con opzione 1]")

    print(f"    3. Entrambe (tutte le sorgenti disponibili)")

    choice = ask("Sorgente", default="1")

    if choice == "2" and refs:
        # Upload references to fal.ai CDN
        print("\n  Caricamento reference su fal.ai CDN...")
        urls = []
        for ref in refs:
            print(f"    Upload: {ref.name} ...", end=" ", flush=True)
            try:
                url = upload_to_fal(ref)
                print(f"OK → {url[:60]}...")
                urls.append(url)
            except Exception as e:
                print(f"ERR: {e}")
        return urls if urls else product["image_urls"]

    elif choice == "3":
        urls = list(product["image_urls"])
        if refs:
            for ref in refs:
                try:
                    url = upload_to_fal(ref)
                    urls.append(url)
                except Exception:
                    pass
        return urls

    return list(product["image_urls"])

# ---------------------------------------------------------------------------
# Template selection
# ---------------------------------------------------------------------------

def select_templates() -> list[tuple[str, dict]]:
    section("Motion template")
    print()
    for idx, name in config.TEMPLATE_INDEX.items():
        t = config.MOTION_TEMPLATES[name]
        print(f"  {idx}. {t['label']:20s} — {t['description']}")

    print(f"\n  all — Tutti i template")

    while True:
        choice = ask("Template (1-5 / all)")
        if choice.lower() == "all":
            return list(config.MOTION_TEMPLATES.items())
        if choice in config.TEMPLATE_INDEX:
            name = config.TEMPLATE_INDEX[choice]
            return [(name, config.MOTION_TEMPLATES[name])]
        print("    Scelta non valida.")

# ---------------------------------------------------------------------------
# Cost estimate
# ---------------------------------------------------------------------------

def compute_cost(engine: dict, duration: str, n_clips: int) -> float:
    key = f"cost_{duration}s"
    cost_per = engine.get(key, engine["cost_5s"])
    return round(n_clips * cost_per, 2)


def show_cost_summary(engine: dict, duration: str, n_clips: int) -> bool:
    total = compute_cost(engine, duration, n_clips)
    print()
    hr()
    print(f"  Motore    : {engine['label']}")
    print(f"  Durata    : {duration}s per clip")
    print(f"  Clip      : {n_clips}")
    print(f"  Costo/clip: ${engine.get(f'cost_{duration}s', engine['cost_5s']):.2f}")
    print(f"  TOTALE    : ${total:.2f} (stima)")
    hr()
    return confirm("Confermi la generazione?")

# ---------------------------------------------------------------------------
# fal.ai argument builder
# ---------------------------------------------------------------------------

def build_arguments(engine: dict, image_url: str, prompt: str,
                    negative_prompt: str, duration: str, aspect_ratio: str) -> dict:
    """Build the arguments dict for a fal.ai endpoint based on engine type."""
    eid = engine["id"]

    # Kling models
    if eid.startswith("kling"):
        args = {
            "image_url": image_url,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
        }
        if engine.get("cfg_scale") is not None:
            args["cfg_scale"] = engine["cfg_scale"]
        return args

    # Luma Dream Machine
    if eid == "luma-dream-machine":
        return {
            "image_url": image_url,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "loop": False,
        }

    # MiniMax Hailuo
    if eid == "minimax-hailuo":
        return {
            "image_url": image_url,
            "prompt": prompt,
        }

    # Wan 2.1
    if eid == "wan-2.1":
        return {
            "image_url": image_url,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
        }

    # Generic fallback
    return {
        "image_url": image_url,
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
    }


def extract_video_url(result: dict) -> str:
    """Extract video URL from fal.ai response (handles different engine formats)."""
    # Most common: result.video.url
    video = result.get("video", {})
    if isinstance(video, dict):
        url = video.get("url", "")
        if url:
            return url

    # Direct url key
    if result.get("url"):
        return result["url"]

    # Nested output
    output = result.get("output", {})
    if isinstance(output, dict):
        video = output.get("video", {})
        if isinstance(video, dict) and video.get("url"):
            return video["url"]

    raise ValueError(f"Impossibile estrarre URL video dalla risposta: {list(result.keys())}")

# ---------------------------------------------------------------------------
# Log management
# ---------------------------------------------------------------------------

def load_log() -> list:
    if LOG_FILE.exists():
        try:
            return json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def append_log(entry: dict):
    LOGS_DIR.mkdir(exist_ok=True)
    log = load_log()
    log.append(entry)
    LOG_FILE.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")


def view_history(product_id: str | None = None):
    """Display generation history, optionally filtered by product."""
    log = load_log()
    if product_id:
        log = [e for e in log if e.get("product_id") == product_id]

    if not log:
        print("\n  Nessuna generazione registrata.")
        pause()
        return

    section("Storico generazioni")
    print()
    total_cost = 0.0
    for e in reversed(log[-20:]):  # show last 20
        status_icon = "✓" if e.get("status") == "success" else "✗"
        print(f"  {status_icon} [{e.get('timestamp','')}] {e.get('motion_type','?'):10s}  "
              f"{e.get('engine','?'):20s}  ${e.get('cost', 0):.2f}")
        if e.get("output_filename"):
            print(f"    → {e['output_filename']}")
        if e.get("error"):
            print(f"    ERR: {e['error']}")
        total_cost += e.get("cost", 0)

    print()
    hr()
    print(f"  Generazioni mostrate: {min(20, len(log))} / {len(log)}")
    print(f"  Costo totale storico: ${total_cost:.2f}")
    hr()
    pause()

# ---------------------------------------------------------------------------
# Single generation
# ---------------------------------------------------------------------------

def generate_one(
    product: dict,
    product_dir: Path,
    engine: dict,
    image_url: str,
    motion_name: str,
    template: dict,
    duration: str,
    aspect_ratio: str,
    outputs_dir: Path,
) -> dict:
    """Generate a single video clip and return a log entry dict."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    img_label = image_url.split("/")[-1].split("?")[0][:20]
    output_filename = f"{timestamp}_{motion_name}_{engine['id']}.mp4"
    output_path = outputs_dir / output_filename

    log_entry = {
        "timestamp": timestamp,
        "product_id": product["id"],
        "motion_type": motion_name,
        "engine": engine["id"],
        "image_url": image_url,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "cost": engine.get(f"cost_{duration}s", engine["cost_5s"]),
        "output_filename": output_filename,
        "status": "pending",
        "error": None,
    }

    print(f"\n  ► {motion_name:10s} | {engine['label']:25s} | {img_label}")

    try:
        args = build_arguments(engine, image_url, template["prompt"],
                               template.get("negative_prompt", ""), duration, aspect_ratio)

        def on_update(update):
            if hasattr(update, "status"):
                print(f"    status: {update.status}", end="\r", flush=True)

        result = fal_client.subscribe(
            engine["endpoint"],
            arguments=args,
            with_logs=False,
            on_queue_update=on_update,
            timeout=config.GENERATION_TIMEOUT,
        )
        print()  # newline after \r

        video_url = extract_video_url(result)

        # Download MP4
        print(f"    Downloading video ...", end=" ", flush=True)
        resp = requests.get(video_url, timeout=120)
        resp.raise_for_status()
        output_path.write_bytes(resp.content)
        print(f"OK → {output_filename}")

        log_entry["status"] = "success"
        log_entry["video_url"] = video_url

    except Exception as e:
        print(f"\n    [ERR] {e}")
        log_entry["status"] = "error"
        log_entry["error"] = str(e)

    append_log(log_entry)
    return log_entry

# ---------------------------------------------------------------------------
# Generation session
# ---------------------------------------------------------------------------

def menu_generate(product: dict, product_dir: Path):
    """Full interactive generation flow."""
    outputs_dir = product_dir / "outputs"
    outputs_dir.mkdir(exist_ok=True)

    header(f"GENERA VIDEO — {product['name']}")

    engine = select_engine()
    duration = select_duration(engine)
    aspect_ratio = select_aspect_ratio(engine)
    image_urls = select_image_source(product, product_dir)
    templates = select_templates()

    n_clips = len(templates) * len(image_urls)

    if not show_cost_summary(engine, duration, n_clips):
        print("\n  Generazione annullata.")
        pause()
        return

    print(f"\n{'═' * 62}")
    print(f"  Avvio — {n_clips} clip in coda")
    print(f"{'═' * 62}")

    results = []
    total = len(templates) * len(image_urls)
    counter = 0

    for motion_name, template in templates:
        for img_url in image_urls:
            counter += 1
            print(f"\n[{counter}/{total}]", end="")
            entry = generate_one(
                product, product_dir, engine, img_url,
                motion_name, template, duration, aspect_ratio, outputs_dir,
            )
            results.append(entry)
            if counter < total:
                time.sleep(1)

    # Final summary
    ok = [r for r in results if r["status"] == "success"]
    err = [r for r in results if r["status"] == "error"]
    total_cost = sum(r.get("cost", 0) for r in ok)

    print(f"\n{'═' * 62}")
    print("  RIEPILOGO")
    print(f"{'═' * 62}")
    print(f"  Successi : {len(ok)}/{total}")
    print(f"  Errori   : {len(err)}")
    print(f"  Costo    : ${total_cost:.2f} (stimato)")
    print(f"  Output   : {outputs_dir.resolve()}")

    if ok:
        print("\n  File generati:")
        for r in ok:
            print(f"    • {r['output_filename']}")
    if err:
        print("\n  Errori:")
        for r in err:
            print(f"    ✗ {r['motion_type']} — {r['error']}")

    print(f"{'═' * 62}\n")
    pause()

# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def main_menu(product: dict, product_dir: Path):
    while True:
        header(f"REELFORGE  ·  {product['name']}")
        print(f"  Prodotto : {product['id']}")
        print(f"  Categoria: {product.get('category', '—')}")
        print()
        print("  1. Prepara immagini     (download + bg removal + cleanup)")
        print("  2. Genera clip video    (scegli motore, durata, template)")
        print("  3. Storico generazioni")
        print("  4. Cambia prodotto")
        print("  5. Aggiungi nuovo prodotto")
        print("  0. Esci")
        print()

        choice = ask("Scelta", default="2")

        if choice == "1":
            menu_process_images(product, product_dir)
        elif choice == "2":
            menu_generate(product, product_dir)
        elif choice == "3":
            view_history(product["id"])
        elif choice == "4":
            product, product_dir = select_product()
        elif choice == "5":
            result = add_new_product()
            if result:
                product, product_dir = result
        elif choice == "0":
            print("\n  Arrivederci.\n")
            sys.exit(0)
        else:
            print("  Scelta non valida.")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║              R E E L F O R G E  ·  AI Video Pipeline        ║")
    print("║              fal.ai · Kling · Luma · MiniMax · Wan          ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    load_api_key()

    product, product_dir = select_product()
    main_menu(product, product_dir)


if __name__ == "__main__":
    main()
