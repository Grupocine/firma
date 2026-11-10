"""Genera la línea animada «EN CARTEL» de la firma y el enlace semanal.

Lee semana.json y escribe en la carpeta sitio/:
  - en-cartel.gif      la animación que muestran todas las firmas
  - estreno/index.html redirige al enlace de la semana
  - logo-grupocine.png el logo de la firma
"""
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).parent
SALIDA = BASE / "sitio"
ROJO, TINTA, FONDO, PUNTO = (219, 50, 47), (17, 17, 17), (255, 255, 255), (200, 200, 200)
ANCHO, ALTO, ESCALA = 300, 22, 2  # se muestra a 300x22, se dibuja al doble para pantallas Retina


def mezclar(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def cuadro(titulo, alfa, f_etiqueta, f_titulo):
    im = Image.new("RGB", (ANCHO * ESCALA, ALTO * ESCALA), FONDO)
    d = ImageDraw.Draw(im)
    medio = ALTO * ESCALA / 2
    d.text((0, medio), "EN CARTEL", font=f_etiqueta, fill=ROJO, anchor="lm")
    x = d.textlength("EN CARTEL", font=f_etiqueta) + 10 * ESCALA
    d.ellipse([x - 6 * ESCALA, medio - 1.5 * ESCALA, x - 3 * ESCALA, medio + 1.5 * ESCALA], fill=PUNTO)
    d.text((x + 2 * ESCALA, medio + (1 - alfa) * 5 * ESCALA), titulo,
           font=f_titulo, fill=mezclar(FONDO, TINTA, alfa), anchor="lm")
    return im


def generar_gif(titulos, destino):
    f_etiqueta = ImageFont.truetype(str(BASE / "fuentes/Poppins-Bold.ttf"), 10 * ESCALA)
    f_titulo = ImageFont.truetype(str(BASE / "fuentes/Poppins-Medium.ttf"), 12 * ESCALA)
    cuadros, tiempos = [], []
    for t in titulos:
        # El primer cuadro de cada título ya se ve completo: Outlook viejo muestra solo ese.
        cuadros.append(cuadro(t, 1, f_etiqueta, f_titulo)); tiempos.append(2400)
        for a in (0.6, 0.25):
            cuadros.append(cuadro(t, a, f_etiqueta, f_titulo)); tiempos.append(60)
        siguiente = titulos[(titulos.index(t) + 1) % len(titulos)]
        for a in (0.35, 0.7):
            cuadros.append(cuadro(siguiente, a, f_etiqueta, f_titulo)); tiempos.append(60)
    paleta = [c.convert("P", palette=Image.ADAPTIVE, colors=64) for c in cuadros]
    paleta[0].save(destino, save_all=True, append_images=paleta[1:], duration=tiempos,
                   loop=0, optimize=True, disposal=1)


def main():
    datos = json.loads((BASE / "semana.json").read_text(encoding="utf-8"))
    titulos = [t.strip() for t in datos["titulos"] if t.strip()]
    if not titulos:
        raise SystemExit("semana.json no tiene títulos")
    enlace = datos.get("enlace", "https://www.grupocine.com.uy")

    if SALIDA.exists():
        shutil.rmtree(SALIDA)
    (SALIDA / "estreno").mkdir(parents=True)
    generar_gif(titulos, SALIDA / "en-cartel.gif")
    shutil.copy(BASE / "logo-grupocine.png", SALIDA / "logo-grupocine.png")
    (SALIDA / "estreno/index.html").write_text(
        f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={enlace}">'
        f'<title>Grupocine</title><a href="{enlace}">Ir a Grupocine</a>', encoding="utf-8")
    (SALIDA / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Firma Grupocine</title>'
        '<body style="font-family:Arial;padding:24px"><h1>Firma Grupocine</h1>'
        '<p>Archivos que usan las firmas de mail del equipo.</p>'
        '<p><img src="logo-grupocine.png" width="84"></p><p><img src="en-cartel.gif" width="300"></p>',
        encoding="utf-8")
    (SALIDA / ".nojekyll").write_text("")
    print("Listo:", ", ".join(titulos))


if __name__ == "__main__":
    main()
