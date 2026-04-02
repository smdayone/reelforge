# config.py — Central configuration for ReelForge

# ---------------------------------------------------------------------------
# Video engines available on fal.ai
# ---------------------------------------------------------------------------
# Each engine defines: endpoint, quality tier, pricing, supported params.
# Costs are approximate — verify at https://fal.ai/pricing

VIDEO_ENGINES = {
    "1": {
        "id": "kling-2.6-pro",
        "label": "Kling 2.6 Pro",
        "endpoint": "fal-ai/kling-video/v2.6/pro/image-to-video",
        "quality": "★★★★★",
        "tier": "Premium",
        "cost_5s": 0.35,
        "cost_10s": 0.70,
        "durations": ["5", "10"],
        "aspect_ratios": ["9:16", "16:9", "1:1"],
        "default_aspect": "9:16",
        "cfg_scale": 0.5,
        "description": "Best-in-class cinematic motion, top product shots",
    },
    "2": {
        "id": "kling-2.1-pro",
        "label": "Kling 2.1 Pro",
        "endpoint": "fal-ai/kling-video/v2.1/pro/image-to-video",
        "quality": "★★★★☆",
        "tier": "High",
        "cost_5s": 0.28,
        "cost_10s": 0.56,
        "durations": ["5", "10"],
        "aspect_ratios": ["9:16", "16:9", "1:1"],
        "default_aspect": "9:16",
        "cfg_scale": 0.5,
        "description": "High quality, good price/quality ratio",
    },
    "3": {
        "id": "kling-2.1-standard",
        "label": "Kling 2.1 Standard",
        "endpoint": "fal-ai/kling-video/v2.1/standard/image-to-video",
        "quality": "★★★☆☆",
        "tier": "Medium",
        "cost_5s": 0.14,
        "cost_10s": 0.28,
        "durations": ["5", "10"],
        "aspect_ratios": ["9:16", "16:9", "1:1"],
        "default_aspect": "9:16",
        "cfg_scale": 0.5,
        "description": "Standard quality, ideal for rapid testing",
    },
    "4": {
        "id": "luma-dream-machine",
        "label": "Luma Dream Machine 1.6",
        "endpoint": "fal-ai/luma-dream-machine/image-to-video",
        "quality": "★★★★☆",
        "tier": "High",
        "cost_5s": 0.30,
        "cost_10s": 0.30,   # fixed ~5s generation
        "durations": ["5"],
        "aspect_ratios": ["9:16", "16:9", "1:1", "4:3", "3:4", "21:9"],
        "default_aspect": "9:16",
        "cfg_scale": None,
        "description": "Photorealistic motion, excellent scene coherence",
    },
    "5": {
        "id": "minimax-hailuo",
        "label": "MiniMax Hailuo-02",
        "endpoint": "fal-ai/minimax/video-01/image-to-video",
        "quality": "★★★★☆",
        "tier": "Medium-High",
        "cost_5s": 0.20,
        "cost_10s": 0.20,   # fixed ~6s generation
        "durations": ["6"],
        "aspect_ratios": ["9:16", "16:9"],
        "default_aspect": "9:16",
        "cfg_scale": None,
        "description": "Natural movements, strong motion consistency",
    },
    "6": {
        "id": "wan-2.1",
        "label": "Wan 2.1 I2V",
        "endpoint": "fal-ai/wan-i2v",
        "quality": "★★★☆☆",
        "tier": "Budget",
        "cost_5s": 0.09,
        "cost_10s": 0.09,
        "durations": ["5"],
        "aspect_ratios": ["9:16", "16:9"],
        "default_aspect": "9:16",
        "cfg_scale": None,
        "description": "Open source, fast & affordable for bulk testing",
    },
}

# ---------------------------------------------------------------------------
# Motion templates — professional cinematography prompts
# ---------------------------------------------------------------------------
# Prompts crafted with: camera body, lens specs, lighting setup, color grade.

MOTION_TEMPLATES = {
    "HERO": {
        "label": "Hero Shot",
        "description": "Cinematic dolly zoom on dark reflective surface",
        "prompt": (
            "Commercial product shot of wireless sport ear-clip earbuds, centered on a dark carbon-fiber textured surface. "
            "Slow cinematic push-in: wide establishing frame to tight medium close-up. "
            "Camera: ARRI Alexa 35. Lens: 85mm Zeiss Master Prime T1.3 at T4. "
            "Three-point lighting rig: 1200W HMI key light with 4×4ft Chimera Pro softbox at 45°, "
            "negative fill flag on shadow side creating dramatic chiaroscuro contrast, "
            "single LED tube rim light at 135° generating sharp specular highlight along the glossy ear-hook housing. "
            "DCI-P3 color space, deep black levels, cool neutral grade with slight blue shadow tint. "
            "4K ProRes 4444, 24fps, 180° shutter angle, no motion blur on product surface."
        ),
        "negative_prompt": (
            "blurry, low quality, distorted product shape, wobble, watermark, text overlay, "
            "shaky motion, overexposed, washed out colors, lens distortion"
        ),
    },
    "FLOAT": {
        "label": "Float & Rotate",
        "description": "360° levitation in void black space",
        "prompt": (
            "Wireless sport ear-clip earbuds levitating and slowly rotating full 360° in pure void black space. "
            "Camera: RED MONSTRO 8K VV. Lens: 50mm Sigma Cine T1.5 at T2.8, racked to infinity. "
            "Volumetric soft-box rim lighting from below — large diffused source at 270° creating a floating halo. "
            "Secondary small accent light at 30° top-left catching micro-details on the silicone housing. "
            "No visible shadows — pure black surround. "
            "Ultra-sharp focus maintained throughout full rotation via servo follow-focus. "
            "Post: subtle chromatic aberration on product edges, slight lens vignette, "
            "Kodak 2383 print emulation LUT. 8K, 24fps."
        ),
        "negative_prompt": (
            "background elements, floor, table surface, hands, shadows, motion blur, "
            "low resolution, clipping highlights, unrealistic physics"
        ),
    },
    "DETAIL": {
        "label": "Macro Detail",
        "description": "Extreme close-up with light sweep across textures",
        "prompt": (
            "Extreme macro close-up of wireless sport earbuds surface. "
            "Camera: Canon EOS R5 with Canon MP-E 65mm f/2.8 1-5× macro lens at 3:1 magnification. "
            "Precision traveling light sweep: a single 1×2ft LED panel rakes slowly across "
            "the product surface from left to right, revealing texture topology in detail — "
            "silicone ear-hook micro-texture, button engravings, metallic mesh grille pattern, "
            "plastic injection mold seam lines, and glossy housing sheen. "
            "Near-black background, no ambient fill. "
            "Cinematic tilt-shift focus plane slowly shifts across the product. "
            "Color grade: tungsten-warm key light, cool blue fill, maximum micro-contrast. "
            "4K, 60fps for slow motion replay."
        ),
        "negative_prompt": (
            "wide angle, full product visible, shallow background, bright ambient light, "
            "flat lighting, soft shadows, overexposed highlights, noise"
        ),
    },
    "ENERGY": {
        "label": "Energy Burst",
        "description": "Dynamic light streaks with sports brand aesthetic",
        "prompt": (
            "Wireless sport earbuds on a dark polished acrylic plinth with mirror reflection. "
            "Camera: Sony Venice 2 with 35mm Cooke S8/i T1.4 cine prime at T2.0. "
            "Dynamic high-speed light painting: 3–4 thin LED wand streaks pass diagonally "
            "across the product from different vectors at varying speeds, "
            "creating energetic bokeh trails, chromatic neon light paint, and directional motion blur lines. "
            "Product remains tack-sharp in center frame throughout. "
            "Background depth with out-of-focus dark-teal and electric-blue accent gradients. "
            "Color grade: crushed blacks, boosted vibrance on blues, complementary orange-teal split tone. "
            "Sports brand commercial aesthetic. 4K, 120fps capture, delivered at 24fps."
        ),
        "negative_prompt": (
            "static lighting, flat look, product blur, dull colors, overexposed streaks, "
            "visible studio equipment, amateur composition"
        ),
    },
    "LIFESTYLE": {
        "label": "Lifestyle Sport",
        "description": "Athletic runner at golden hour, rack focus on earbuds",
        "prompt": (
            "Shallow depth-of-field B-roll: side profile of athletic person running on an "
            "outdoor trail at golden hour. "
            "Camera: Sony FX6. Lens: Sony 135mm f/1.8 GM at f/2.0. "
            "Rack focus from blurred bokeh background — trailing trail trees and golden sky — "
            "to tack-sharp ear-clip wireless earbuds sitting on the ear. "
            "Backlit rim light from low sun at 5° above horizon, creating warm orange halo around "
            "the athlete's head and specular glint on the earbuds housing. "
            "Natural perspiration on skin under rim light. "
            "Color grade: lifted warm shadows, orange-teal complementary split tone, "
            "Kodak 5219 film emulsion, 2.39:1 anamorphic crop with natural horizontal lens flares. "
            "4K, 120fps captured at 1/250s for clean slow motion."
        ),
        "negative_prompt": (
            "static shot, no motion, indoor, artificial backgrounds, cold lighting, "
            "earbuds out of focus, amateur framing, saturated colors"
        ),
    },
}

# Index for menu display: "1" -> "HERO", etc.
TEMPLATE_INDEX = {str(i + 1): k for i, k in enumerate(MOTION_TEMPLATES)}

# Timeout for a single video generation (seconds)
GENERATION_TIMEOUT = 600
