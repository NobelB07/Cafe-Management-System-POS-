from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from cafe_app.models import MenuItem, USD_TO_NPR_RATE


MENU_ITEMS = [
    {
        "name": "Velvet Cappuccino",
        "price": "4.80",
        "category": "beverages",
        "description": "Espresso, steamed milk, and a soft cocoa finish.",
        "image": "velvet_cappuccino.png",
        "colors": ("#6b3f2a", "#e7c78d", "#f8efe0"),
    },
    {
        "name": "Iced Caramel Cloud",
        "price": "5.40",
        "category": "beverages",
        "description": "Cold brew, caramel, vanilla foam, and crystal ice.",
        "image": "iced_caramel_cloud.png",
        "colors": ("#8b5a35", "#d9a441", "#eef5f4"),
    },
    {
        "name": "Garden Toast",
        "price": "7.20",
        "category": "snacks",
        "description": "Sourdough with avocado, herbs, sesame, and lime.",
        "image": "garden_toast.png",
        "colors": ("#5f8a6b", "#d8b36a", "#f5eddc"),
    },
    {
        "name": "Truffle Fries",
        "price": "6.50",
        "category": "snacks",
        "description": "Crisp fries with parmesan, parsley, and truffle salt.",
        "image": "truffle_fries.png",
        "colors": ("#d9a441", "#f2d48a", "#fcf5e7"),
    },
    {
        "name": "Herb Grilled Panini",
        "price": "10.90",
        "category": "meals",
        "description": "Pressed ciabatta, roasted vegetables, pesto, and cheese.",
        "image": "herb_grilled_panini.png",
        "colors": ("#9b5d36", "#5f8a6b", "#f3dfb8"),
    },
    {
        "name": "Creamy Mushroom Pasta",
        "price": "12.40",
        "category": "meals",
        "description": "Silky cream sauce, mushrooms, cracked pepper, and herbs.",
        "image": "creamy_mushroom_pasta.png",
        "colors": ("#b99062", "#ead8b7", "#5a3522"),
    },
    {
        "name": "Midnight Chocolate Tart",
        "price": "6.80",
        "category": "desserts",
        "description": "Dark chocolate ganache with espresso cream.",
        "image": "midnight_chocolate_tart.png",
        "colors": ("#3d241c", "#b65f5f", "#f2d0bd"),
    },
    {
        "name": "Berry Mascarpone Waffle",
        "price": "7.60",
        "category": "desserts",
        "description": "Golden waffle, mascarpone, berries, and maple gloss.",
        "image": "berry_mascarpone_waffle.png",
        "colors": ("#c08b44", "#b65f5f", "#fff1d5"),
    },
]


class Command(BaseCommand):
    help = "Seed XML Cafe System menu items with local images."

    def handle(self, *args, **options):
        image_dir = Path(settings.MEDIA_ROOT) / "menu_images"
        image_dir.mkdir(parents=True, exist_ok=True)

        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            self.stderr.write("Pillow is required. Install requirements.txt first.")
            return

        self._create_hero(image_dir, Image, ImageDraw, ImageFont)

        for item in MENU_ITEMS:
            self._create_menu_image(image_dir / item["image"], item, Image, ImageDraw, ImageFont)
            MenuItem.objects.update_or_create(
                name=item["name"],
                defaults={
                    "price": self._npr_price(item),
                    "category": item["category"],
                    "description": item["description"],
                    "image": f"menu_images/{item['image']}",
                    "is_available": True,
                },
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(MENU_ITEMS)} XML Cafe menu items."))

    def _font(self, ImageFont, size, bold=False):
        names = [
            "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        ]
        for name in names:
            if Path(name).exists():
                return ImageFont.truetype(name, size)
        return ImageFont.load_default()

    def _create_menu_image(self, path, item, Image, ImageDraw, ImageFont):
        width, height = 1200, 800
        primary, accent, cream = item["colors"]
        image = Image.new("RGB", (width, height), cream)
        draw = ImageDraw.Draw(image)

        for y in range(height):
            ratio = y / height
            shade = int(18 * ratio)
            draw.line((0, y, width, y), fill=self._shift_hex(cream, -shade))

        draw.rounded_rectangle((80, 70, 1120, 710), radius=56, fill="#fffaf2", outline="#ead9bf", width=4)
        draw.ellipse((715, 70, 1125, 480), fill=self._with_alpha_mix(accent, "#fffaf2", 0.18))
        draw.ellipse((45, 430, 430, 815), fill=self._with_alpha_mix(primary, "#fffaf2", 0.14))

        if item["category"] == "beverages":
            self._draw_cup(draw, primary, accent)
        elif item["category"] == "snacks":
            self._draw_plate(draw, primary, accent, snack=True)
        elif item["category"] == "meals":
            self._draw_plate(draw, primary, accent, snack=False)
        else:
            self._draw_dessert(draw, primary, accent)

        title_font = self._font(ImageFont, 58, bold=True)
        category_font = self._font(ImageFont, 24, bold=True)
        text_font = self._font(ImageFont, 32)

        draw.text((92, 92), "XML CAFE SYSTEM", fill=primary, font=category_font)
        draw.text((92, 610), item["name"], fill="#17211c", font=title_font)
        draw.text((92, 680), item["category"].upper(), fill="#67736d", font=category_font)
        draw.text((800, 630), f"Rs. {self._npr_price(item)}", fill=primary, font=text_font)
        image.save(path, quality=95)

    def _create_hero(self, image_dir, Image, ImageDraw, ImageFont):
        path = image_dir / "xml_cafe_hero.png"
        image = Image.new("RGB", (1600, 700), "#1b241f")
        draw = ImageDraw.Draw(image)
        for x in range(1600):
            ratio = x / 1600
            r = int(27 + 68 * ratio)
            g = int(36 + 36 * ratio)
            b = int(31 + 11 * ratio)
            draw.line((x, 0, x, 700), fill=(r, g, b))

        draw.rounded_rectangle((1030, 120, 1390, 500), radius=70, fill="#f2d5a0")
        draw.rounded_rectangle((1110, 225, 1305, 485), radius=36, fill="#6b3f2a")
        draw.ellipse((1070, 160, 1345, 270), fill="#fff3db")
        draw.arc((1285, 260, 1430, 420), 275, 90, fill="#f2d5a0", width=28)
        draw.ellipse((870, 420, 1500, 570), fill="#101815")
        draw.text((110, 145), "XML Cafe System", fill="#fff8e8", font=self._font(ImageFont, 88, bold=True))
        draw.text((116, 255), "Cafe billing and orders", fill="#e5c988", font=self._font(ImageFont, 34, bold=True))
        image.save(path, quality=95)

    def _npr_price(self, item):
        return (Decimal(item["price"]) * USD_TO_NPR_RATE).quantize(Decimal('0.01'))

    def _draw_cup(self, draw, primary, accent):
        draw.ellipse((420, 250, 780, 380), fill="#fff7ea", outline="#e5cfad", width=5)
        draw.rounded_rectangle((460, 300, 740, 565), radius=42, fill=primary)
        draw.ellipse((485, 270, 715, 345), fill=accent)
        draw.arc((725, 350, 860, 500), 275, 90, fill=primary, width=26)
        draw.ellipse((395, 540, 805, 620), fill="#241711")

    def _draw_plate(self, draw, primary, accent, snack):
        draw.ellipse((330, 260, 875, 630), fill="#fdf7eb", outline="#e4d4bd", width=8)
        draw.ellipse((410, 335, 795, 580), fill="#efe0ca")
        if snack:
            for i in range(9):
                x = 435 + i * 36
                draw.rounded_rectangle((x, 330, x + 44, 555), radius=18, fill=accent, outline="#b87431", width=3)
            draw.ellipse((620, 365, 735, 480), fill=primary)
        else:
            draw.rounded_rectangle((410, 330, 790, 500), radius=38, fill=accent)
            draw.line((430, 360, 770, 455), fill=primary, width=18)
            draw.line((450, 455, 760, 360), fill=primary, width=18)
            draw.ellipse((510, 470, 705, 575), fill="#fff4d7")

    def _draw_dessert(self, draw, primary, accent):
        draw.ellipse((365, 520, 850, 620), fill="#2a1a14")
        draw.rounded_rectangle((430, 300, 785, 535), radius=40, fill=primary)
        draw.rounded_rectangle((455, 275, 760, 360), radius=36, fill=accent)
        for x in (500, 600, 700):
            draw.ellipse((x, 235, x + 72, 307), fill="#fff7ea")
        draw.line((455, 385, 760, 385), fill="#f0d4b8", width=8)

    def _shift_hex(self, color, amount):
        color = color.lstrip("#")
        values = [max(0, min(255, int(color[i:i + 2], 16) + amount)) for i in (0, 2, 4)]
        return tuple(values)

    def _with_alpha_mix(self, foreground, background, alpha):
        fg = foreground.lstrip("#")
        bg = background.lstrip("#")
        values = []
        for i in (0, 2, 4):
            mixed = int(int(fg[i:i + 2], 16) * alpha + int(bg[i:i + 2], 16) * (1 - alpha))
            values.append(mixed)
        return tuple(values)
