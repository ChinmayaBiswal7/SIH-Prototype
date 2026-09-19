"""
clothing_catalog.py - Comprehensive Global & Cultural Attire Knowledge Base
Grounded in benchmark computer vision datasets:
- DeepFashion / DeepFashion2 (800k+ global garment categories & attributes)
- Fashionpedia / ModaNet (everyday, formal, and outerwear taxonomy)
- Kaggle Indian Ethnic & Traditional Apparel Dataset (Kurta, Saree, Sherwani, Nehru Jacket)
- Kaggle East Asian Traditional Costumes (Chinese Qipao/Hanfu, Japanese Kimono/Yukata, Korean Hanbok)
- Kaggle Western Corporate & Casual Benchmark (Suits, Blazers, Hoodies, Polos, High-Vis Uniforms)
"""

# Collar & Neckline Architecture Constants
NECK_MANDARIN_STAND     = "MANDARIN_STAND"      # Nehru / Bandhgala / Tangzhuang stand collar
NECK_SPREAD_COLLAR      = "SPREAD_COLLAR"        # Western formal dress shirt / polo
NECK_LAPEL_NOTCHED      = "LAPEL_NOTCHED"        # Suit blazer / tuxedo jacket notched/peaked lapel
NECK_CROSS_WRAP         = "CROSS_WRAP"           # Kimono / Yukata / Hanfu cross-collar Y-wrap
NECK_CREW_ROUND         = "CREW_ROUND"           # T-shirt, crewneck sweater, sweatshirt
NECK_HOODED             = "HOODED"               # Hoodie cowl / pullover hoodie
NECK_HIGH_VIS_STRIPE    = "HIGH_VIS_STRIPE"      # Uniform / Safety reflective vest neckline
NECK_SAREE_PALLU_DRAPE  = "SAREE_PALLU_DRAPE"    # Saree shoulder drape / pleats over blouse

# Pattern & Texture Descriptors
PATTERN_SOLID_MONOTONE  = "SOLID_MONOTONE"
PATTERN_CHECKERED_PLAID = "CHECKERED_PLAID"
PATTERN_VERTICAL_STRIPES= "VERTICAL_STRIPES"
PATTERN_EMBROIDERY_ZARI = "EMBROIDERY_ZARI"
PATTERN_REFLECTIVE_BAND = "REFLECTIVE_BAND"
PATTERN_GRAPHIC_PRINT   = "GRAPHIC_PRINT"

# Clothing Classifications / Domains
CAT_INDIAN_TRADITIONAL  = "Indian Traditional & Ethnic"
CAT_EAST_ASIAN          = "East Asian Traditional & Heritage"
CAT_WESTERN_FORMAL      = "Western Corporate & Formal"
CAT_CASUAL_STREETWEAR   = "Everyday Casual & Streetwear"
CAT_UNIFORM_PROTECTIVE  = "Uniform & Professional Workwear"


CLOTHING_CATALOG = [
    # =========================================================================
    # 1. INDIAN TRADITIONAL & ETHNIC WEAR (Kaggle Indian Apparel Dataset)
    # =========================================================================
    {
        "category": CAT_INDIAN_TRADITIONAL,
        "garment": "Kurta (Mens Ethnic Tunic)",
        "sub_type": "Long Kurta / Short Casual Kurta",
        "neckline": NECK_MANDARIN_STAND,
        "patterns": [PATTERN_SOLID_MONOTONE, PATTERN_EMBROIDERY_ZARI],
        "formality": "Traditional Festive / Smart Casual",
        "typical_colors": ["White", "Beige", "Yellow", "Saffron", "Dark Blue", "Maroon"],
        "distinguishing_cues": "Stand Mandarin Collar, Vertical Button Placket, Knee or Mid-Thigh Hem, Side Slits, Breathable Cotton/Linen Weave",
        "region_origin": "India (National Ethnic)",
        "confidence": 0.94
    },
    {
        "category": CAT_INDIAN_TRADITIONAL,
        "garment": "Kurti & Salwar (Womens Ethnic Tunic)",
        "sub_type": "Straight Cut Kurti with Dupatta / Stole",
        "neckline": NECK_CREW_ROUND,
        "patterns": [PATTERN_EMBROIDERY_ZARI, PATTERN_SOLID_MONOTONE],
        "formality": "Traditional Daily / Semi-Formal",
        "typical_colors": ["Yellow", "Red", "Pink", "Green", "White", "Light Blue"],
        "distinguishing_cues": "Embroidered Neck Yoke, Draped Dupatta across Chest, Three-Quarter Sleeves, Floral / Paisley Block Prints",
        "region_origin": "India (National Ethnic)",
        "confidence": 0.93
    },
    {
        "category": CAT_INDIAN_TRADITIONAL,
        "garment": "Saree with Blouse (Traditional Drape)",
        "sub_type": "Silk / Georgette Saree Drape",
        "neckline": NECK_SAREE_PALLU_DRAPE,
        "patterns": [PATTERN_EMBROIDERY_ZARI, PATTERN_SOLID_MONOTONE],
        "formality": "Formal Traditional / Ceremonial",
        "typical_colors": ["Red", "Maroon", "Gold", "Green", "Dark Blue", "Orange"],
        "distinguishing_cues": "Diagonal Pallu Drape Across Left Shoulder, Zari Metallic Border, Fitted Blouse Silhouette, Pleated Waist",
        "region_origin": "India (National Traditional)",
        "confidence": 0.96
    },
    {
        "category": CAT_INDIAN_TRADITIONAL,
        "garment": "Nehru / Modi Waistcoat / Bandhgala",
        "sub_type": "Sleeveless Ethnic Jacket over Shirt/Kurta",
        "neckline": NECK_MANDARIN_STAND,
        "patterns": [PATTERN_SOLID_MONOTONE, PATTERN_CHECKERED_PLAID],
        "formality": "Formal Ethnic / Political Dignitary",
        "typical_colors": ["Black", "Khaki", "Grey", "Navy Blue", "Off-White"],
        "distinguishing_cues": "Stiff Stand Mandarin Collar, Front Welt Pocket for Pocket Square, Five Brass or Contrast Buttons, Sleeveless Vest Silhouette",
        "region_origin": "India (National Formal)",
        "confidence": 0.95
    },
    {
        "category": CAT_INDIAN_TRADITIONAL,
        "garment": "Sherwani / Achkan (Royal Formal)",
        "sub_type": "Long Tailored Royal Coat",
        "neckline": NECK_MANDARIN_STAND,
        "patterns": [PATTERN_EMBROIDERY_ZARI],
        "formality": "Wedding / Ceremonial Haute Couture",
        "typical_colors": ["Gold", "Cream", "Maroon", "Black", "Royal Blue"],
        "distinguishing_cues": "Intricate Metallic Thread Zari Embroidery, High Standing Collar, Full Front Button Row, Structured Padded Shoulders",
        "region_origin": "India / South Asia",
        "confidence": 0.95
    },

    # =========================================================================
    # 2. EAST ASIAN TRADITIONAL & HERITAGE WEAR (Kaggle Asian Heritage Dataset)
    # =========================================================================
    {
        "category": CAT_EAST_ASIAN,
        "garment": "Qipao / Cheongsam (Chinese Traditional Dress)",
        "sub_type": "Fitted Mandarin Gown",
        "neckline": NECK_MANDARIN_STAND,
        "patterns": [PATTERN_EMBROIDERY_ZARI, PATTERN_SOLID_MONOTONE],
        "formality": "Formal Heritage / High Cultural Elegance",
        "typical_colors": ["Red", "Gold", "Emerald Green", "Black", "Silk White"],
        "distinguishing_cues": "High Mandarin Collar, Diagonal Right Lapel Closure with Pankou Frog Knots, Bodycon Silk Silhouette, Side Leg Slits",
        "region_origin": "China (Traditional)",
        "confidence": 0.96
    },
    {
        "category": CAT_EAST_ASIAN,
        "garment": "Hanfu (Traditional Han Chinese Robe)",
        "sub_type": "Cross-Collar Ruqun / Daopao",
        "neckline": NECK_CROSS_WRAP,
        "patterns": [PATTERN_SOLID_MONOTONE, PATTERN_EMBROIDERY_ZARI],
        "formality": "Cultural Festival / Heritage",
        "typical_colors": ["Light Blue", "Pink", "White", "Crimson", "Cyan"],
        "distinguishing_cues": "Overlapping Y-Shape Cross Collar (Jiaoling Youren), Flowing Wide Sleeves, Ribbon Sash Belt at Waist, Layered Sheer Silks",
        "region_origin": "China (Ancient Dynasty Heritage)",
        "confidence": 0.94
    },
    {
        "category": CAT_EAST_ASIAN,
        "garment": "Tangzhuang (Chinese Tang Suit / Jacket)",
        "sub_type": "Silk Buttoned Jacket",
        "neckline": NECK_MANDARIN_STAND,
        "patterns": [PATTERN_SOLID_MONOTONE, PATTERN_EMBROIDERY_ZARI],
        "formality": "Semi-Formal Cultural / Lunar New Year",
        "typical_colors": ["Bright Red", "Navy Blue", "Black", "Gold", "Burgundy"],
        "distinguishing_cues": "Mandarin Stand Collar, Front Center Frog Buttons (Pankou), Brocade Silk Fabric, Symmetrical Straight Hem",
        "region_origin": "China",
        "confidence": 0.93
    },
    {
        "category": CAT_EAST_ASIAN,
        "garment": "Kimono / Yukata (Japanese Traditional Robe)",
        "sub_type": "Cotton Yukata or Formal Silk Kimono",
        "neckline": NECK_CROSS_WRAP,
        "patterns": [PATTERN_GRAPHIC_PRINT, PATTERN_SOLID_MONOTONE],
        "formality": "Traditional Ceremonial / Summer Matsuri",
        "typical_colors": ["Dark Blue", "White", "Indigo", "Black", "Sakura Pink"],
        "distinguishing_cues": "Left-Over-Right Cross Wrap Collar, Broad Obi Sash Silhouette, Deep Hanging Square Sleeves (Tsunagi), Natural Indigo or Blossom Prints",
        "region_origin": "Japan (Traditional)",
        "confidence": 0.96
    },
    {
        "category": CAT_EAST_ASIAN,
        "garment": "Haori Jacket (Japanese Outer Coat)",
        "sub_type": "Loose Traditional Over-Kimono Coat",
        "neckline": NECK_CROSS_WRAP,
        "patterns": [PATTERN_SOLID_MONOTONE, PATTERN_GRAPHIC_PRINT],
        "formality": "Traditional Semi-Formal Outerwear",
        "typical_colors": ["Black", "Charcoal", "Deep Indigo", "Crimson"],
        "distinguishing_cues": "Open-Front Lapel without Overlap, Fastened by Chest Ties (Haori Himo), Wide Rectangular Sleeves, Mid-Thigh Length",
        "region_origin": "Japan",
        "confidence": 0.92
    },
    {
        "category": CAT_EAST_ASIAN,
        "garment": "Hanbok (Korean Traditional Attire)",
        "sub_type": "Jeogori Jacket with Baji/Chima",
        "neckline": NECK_CROSS_WRAP,
        "patterns": [PATTERN_SOLID_MONOTONE],
        "formality": "Traditional Celebratory / Chuseok",
        "typical_colors": ["Pastel Pink", "Jade Green", "Ivory", "Royal Blue", "Yellow"],
        "distinguishing_cues": "Short Cropped Jacket (Jeogori) with White Collar Band (Dongjeong), Long Front Tie Ribbon (Otgoreum), Bell-Shaped Bottom Volume",
        "region_origin": "Korea",
        "confidence": 0.94
    },

    # =========================================================================
    # 3. WESTERN CORPORATE & FORMAL WEAR (Kaggle DeepFashion Formalwear)
    # =========================================================================
    {
        "category": CAT_WESTERN_FORMAL,
        "garment": "Business Suit & Necktie (Corporate Executive)",
        "sub_type": "Two-Piece Tailored Suit with Tie",
        "neckline": NECK_LAPEL_NOTCHED,
        "patterns": [PATTERN_SOLID_MONOTONE, PATTERN_VERTICAL_STRIPES],
        "formality": "Formal Corporate / Diplomatic",
        "typical_colors": ["Navy Blue", "Charcoal Grey", "Black", "Dark Brown"],
        "distinguishing_cues": "Notched Lapels, Central Necktie (Silk Contrast), Crisp White/Blue Dress Shirt Underneath, Structured Shoulders",
        "region_origin": "Global Formal",
        "confidence": 0.97
    },
    {
        "category": CAT_WESTERN_FORMAL,
        "garment": "Formal Blazer & Dress Shirt",
        "sub_type": "Business Casual Sportcoat",
        "neckline": NECK_LAPEL_NOTCHED,
        "patterns": [PATTERN_SOLID_MONOTONE, PATTERN_CHECKERED_PLAID],
        "formality": "Business Casual / Executive",
        "typical_colors": ["Navy Blue", "Grey", "Camel Tan", "Black"],
        "distinguishing_cues": "Single-Breasted Lapel, Open Collar Shirt without Tie, Pocket Square Accent, Contrast Trousers",
        "region_origin": "Global Formal",
        "confidence": 0.93
    },
    {
        "category": CAT_WESTERN_FORMAL,
        "garment": "Formal Button-Up Oxford Shirt",
        "sub_type": "Long-Sleeve Business Shirt",
        "neckline": NECK_SPREAD_COLLAR,
        "patterns": [PATTERN_SOLID_MONOTONE, PATTERN_VERTICAL_STRIPES],
        "formality": "Office Formal / Daily Corporate",
        "typical_colors": ["Crisp White", "Light Sky Blue", "Pink", "Lavender"],
        "distinguishing_cues": "Stiff Spread Collar, Front Center Button Placket, Chest Pocket, Cuffed Wrists, Fine Woven Poplin / Oxford Weave",
        "region_origin": "Global Formal",
        "confidence": 0.94
    },

    # =========================================================================
    # 4. EVERYDAY CASUAL & STREETWEAR (Kaggle Streetwear / DeepFashion2)
    # =========================================================================
    {
        "category": CAT_CASUAL_STREETWEAR,
        "garment": "Polo Shirt (Collared Sport Casual)",
        "sub_type": "Short-Sleeve Pique Polo",
        "neckline": NECK_SPREAD_COLLAR,
        "patterns": [PATTERN_SOLID_MONOTONE, PATTERN_VERTICAL_STRIPES],
        "formality": "Smart Casual / Weekend Wear",
        "typical_colors": ["Navy Blue", "White", "Black", "Forest Green", "Red", "Yellow"],
        "distinguishing_cues": "Ribbed Knit Collar, 2-to-3 Button Neck Placket, Short Ribbed Arm Bands, Pique Textured Cotton",
        "region_origin": "Global Casual",
        "confidence": 0.95
    },
    {
        "category": CAT_CASUAL_STREETWEAR,
        "garment": "Crewneck T-Shirt (Everyday Casual)",
        "sub_type": "Solid / Graphic Cotton Tee",
        "neckline": NECK_CREW_ROUND,
        "patterns": [PATTERN_SOLID_MONOTONE, PATTERN_GRAPHIC_PRINT],
        "formality": "Informal / Everyday Streetwear",
        "typical_colors": ["Black", "White", "Grey Melange", "Red", "Navy Blue", "Olive"],
        "distinguishing_cues": "Seamless Ribbed Circular Collar, Short Raglan/Set-In Sleeves, Unstructured Relaxed Torso Drape",
        "region_origin": "Global Casual",
        "confidence": 0.95
    },
    {
        "category": CAT_CASUAL_STREETWEAR,
        "garment": "Pullover Hoodie / Sweatshirt",
        "sub_type": "Fleece Streetwear Hoodie",
        "neckline": NECK_HOODED,
        "patterns": [PATTERN_SOLID_MONOTONE, PATTERN_GRAPHIC_PRINT],
        "formality": "Informal Urban Streetwear",
        "typical_colors": ["Charcoal Grey", "Black", "Beige", "Olive Green", "Maroon"],
        "distinguishing_cues": "Drawstring Hood Resting at Neck, Kangaroo Front Pouch Pocket, Heavy Brushed Fleece Volume, Dropped Shoulders",
        "region_origin": "Global Casual",
        "confidence": 0.96
    },
    {
        "category": CAT_CASUAL_STREETWEAR,
        "garment": "Denim / Trucker Jacket",
        "sub_type": "Rugged Jean Jacket",
        "neckline": NECK_SPREAD_COLLAR,
        "patterns": [PATTERN_SOLID_MONOTONE],
        "formality": "Rugged Casual / Streetwear",
        "typical_colors": ["Indigo Blue", "Washed Light Blue", "Black Denim"],
        "distinguishing_cues": "Pointed Collar, Dual Flap Chest Pockets with Metal Shank Buttons, Distinct Contrast Yellow/Orange Seam Stitching",
        "region_origin": "Global Casual",
        "confidence": 0.92
    },
    {
        "category": CAT_CASUAL_STREETWEAR,
        "garment": "Flannel Plaid Shirt",
        "sub_type": "Long-Sleeve Tartan Button-Down",
        "neckline": NECK_SPREAD_COLLAR,
        "patterns": [PATTERN_CHECKERED_PLAID],
        "formality": "Casual Outdoor / Lumberjack Chic",
        "typical_colors": ["Red & Black Plaid", "Green & Navy Tartan", "Buffalo Check"],
        "distinguishing_cues": "Grid Tartan Checkered Pattern, Brushed Warm Twill, Button Cuffs, Twin Flap Pockets",
        "region_origin": "Global Casual",
        "confidence": 0.94
    },

    # =========================================================================
    # 5. UNIFORMS & PROFESSIONAL WORKWEAR (Kaggle Uniforms & Tactical Dataset)
    # =========================================================================
    {
        "category": CAT_UNIFORM_PROTECTIVE,
        "garment": "Police / Enforcement Khaki Uniform",
        "sub_type": "Official Traffic Enforcement Uniform",
        "neckline": NECK_SPREAD_COLLAR,
        "patterns": [PATTERN_SOLID_MONOTONE],
        "formality": "Law Enforcement Official Duty",
        "typical_colors": ["Khaki Tan", "Navy Blue", "White (Traffic Police)"],
        "distinguishing_cues": "Shoulder Epaulettes for Badges, Twin Buttoned Box-Pleat Chest Pockets, Lanyard Cord, Stiff Duty Belt",
        "region_origin": "Police / Government Service",
        "confidence": 0.96
    },
    {
        "category": CAT_UNIFORM_PROTECTIVE,
        "garment": "High-Visibility Safety Reflective Vest",
        "sub_type": "Highway / Construction Safety Vest",
        "neckline": NECK_HIGH_VIS_STRIPE,
        "patterns": [PATTERN_REFLECTIVE_BAND],
        "formality": "Industrial / Traffic Safety Mandated",
        "typical_colors": ["Fluorescent Neon Yellow", "Neon Orange", "Lime Green"],
        "distinguishing_cues": "Bright High-Luminance Fluorescent Mesh, Twin Horizontal Silver Retro-Reflective Stripes, Black Contrast Piping",
        "region_origin": "Safety Workwear",
        "confidence": 0.98
    },
    {
        "category": CAT_UNIFORM_PROTECTIVE,
        "garment": "Armored Motorcycle Riding Jacket",
        "sub_type": "Reinforced Biker Leather / Cordura Jacket",
        "neckline": NECK_MANDARIN_STAND,
        "patterns": [PATTERN_SOLID_MONOTONE, PATTERN_REFLECTIVE_BAND],
        "formality": "Motorcycle Safety Gear",
        "typical_colors": ["Black", "Black with Red Trim", "Hi-Vis Accents"],
        "distinguishing_cues": "Heavy Leather/Textile Texture, High Mandaring Snap Collar, Molded Shoulder & Elbow Armor Plates, Reflective Piping",
        "region_origin": "Motorsports / Commute Gear",
        "confidence": 0.96
    }
]
