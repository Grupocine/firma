"""Genera la línea animada «EN CARTELERA» de la firma y el enlace semanal.

Lee semana.json, elige la semana vigente (jueves a miércoles, hora de Montevideo)
y escribe en la carpeta sitio/:
  - en-cartel.gif      la animación que muestran todas las firmas
  - estreno/index.html redirige al enlace de la semana
  - logo-grupocine.png el logo de la firma
"""
import json
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).parent
SALIDA = BASE / "sitio"
ROJO, TINTA, FONDO, PUNTO = (219, 50, 47), (17, 17, 17), (255, 255, 255), (200, 200, 200)
ANCHO, ALTO, ESCALA = 300, 22, 2  # se muestra a 300x22, se dibuja al doble para pantallas Retina
MONTEVIDEO = timezone(timedelta(hours=-3))


def mezclar(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def fuente(nombre, puntos):
    return ImageFont.truetype(str(BASE / "fuentes" / nombre), round(puntos * ESCALA))


def ajustar(titulo, d, espacio):
    """Devuelve (texto, fuente) que entra en el espacio: achica la letra y, si no alcanza,
    deja solo la parte antes de los dos puntos o corta con puntos suspensivos."""
    for texto in (titulo, titulo.split(":")[0].strip()):
        for pts in (12, 11.5, 11, 10.5):
            f = fuente("Poppins-Medium.ttf", pts)
            if d.textlength(texto, font=f) <= espacio:
                return texto, f
    f = fuente("Poppins-Medium.ttf", 10.5)
    texto = titulo
    while texto and d.textlength(texto + "…", font=f) > espacio:
        texto = texto[:-1]
    return texto.rstrip() + "…", f


def etiqueta(d, sello, f_etiqueta, medio):
    """Dibuja la etiqueta de la izquierda y devuelve dónde empieza el título.
    Estreno: píldora roja llena · Pre-estreno: píldora con borde rojo · resto: «EN CARTELERA»."""
    if sello in ("estreno", "pre-estreno"):
        texto = "ESTRENO" if sello == "estreno" else "PRE-ESTRENO"
        f = fuente("Poppins-Bold.ttf", 9)
        ancho = d.textlength(texto, font=f) + 12 * ESCALA
        caja = [0, medio - 8 * ESCALA, ancho, medio + 8 * ESCALA]
        if sello == "estreno":
            d.rounded_rectangle(caja, radius=8 * ESCALA, fill=ROJO)
            d.text((ancho / 2, medio), texto, font=f, fill=FONDO, anchor="mm")
        else:
            d.rounded_rectangle(caja, radius=8 * ESCALA, outline=ROJO, width=round(1.5 * ESCALA))
            d.text((ancho / 2, medio), texto, font=f, fill=ROJO, anchor="mm")
        return ancho + 8 * ESCALA
    d.text((0, medio), "EN CARTELERA", font=f_etiqueta, fill=ROJO, anchor="lm")
    x = d.textlength("EN CARTELERA", font=f_etiqueta) + 10 * ESCALA
    d.ellipse([x - 6 * ESCALA, medio - 1.5 * ESCALA, x - 3 * ESCALA, medio + 1.5 * ESCALA], fill=PUNTO)
    return x


def cuadro(pelicula, alfa, f_etiqueta):
    titulo, sello = pelicula
    im = Image.new("RGB", (ANCHO * ESCALA, ALTO * ESCALA), FONDO)
    d = ImageDraw.Draw(im)
    medio = ALTO * ESCALA / 2
    x = etiqueta(d, sello, f_etiqueta, medio)
    texto, f = ajustar(titulo, d, ANCHO * ESCALA - x - 4 * ESCALA)
    d.text((x + 2 * ESCALA, medio + (1 - alfa) * 5 * ESCALA), texto,
           font=f, fill=mezclar(FONDO, TINTA, alfa), anchor="lm")
    return im


def generar_gif(titulos, destino):
    f_etiqueta = fuente("Poppins-Bold.ttf", 10)
    cuadros, tiempos = [], []
    for i, t in enumerate(titulos):
        # El primer cuadro de cada título ya se ve completo: Outlook viejo muestra solo ese.
        cuadros.append(cuadro(t, 1, f_etiqueta)); tiempos.append(2400)
        if len(titulos) > 1:
            for a in (0.6, 0.25):
                cuadros.append(cuadro(t, a, f_etiqueta)); tiempos.append(60)
            siguiente = titulos[(i + 1) % len(titulos)]
            for a in (0.35, 0.7):
                cuadros.append(cuadro(siguiente, a, f_etiqueta)); tiempos.append(60)
    paleta = [c.convert("P", palette=Image.ADAPTIVE, colors=64) for c in cuadros]
    paleta[0].save(destino, save_all=True, append_images=paleta[1:], duration=tiempos,
                   loop=0, optimize=True, disposal=1)


def semana_vigente(datos, hoy):
    """Acepta el formato nuevo {"semanas": [{desde, hasta, titulos, enlace?}]}
    y el viejo {"titulos": [...]}. Elige la semana que incluye hoy; si no hay,
    la última que ya empezó; si tampoco, la primera."""
    if "semanas" not in datos:
        return datos
    semanas = sorted(datos["semanas"], key=lambda s: s["desde"])
    for s in semanas:
        if date.fromisoformat(s["desde"]) <= hoy <= date.fromisoformat(s["hasta"]):
            return s
    empezadas = [s for s in semanas if date.fromisoformat(s["desde"]) <= hoy]
    return empezadas[-1] if empezadas else semanas[0]


def main():
    datos = json.loads((BASE / "semana.json").read_text(encoding="utf-8"))
    hoy = datetime.now(MONTEVIDEO).date()
    semana = semana_vigente(datos, hoy)
    # Cada entrada puede ser "Título" o {"titulo": "...", "sello": "estreno" | "pre-estreno"}.
    titulos = []
    for t in semana["titulos"]:
        titulo, sello = (t, "") if isinstance(t, str) else (t.get("titulo", ""), t.get("sello", ""))
        if titulo.strip():
            titulos.append((titulo.strip(), sello.strip().lower()))
    if not titulos:
        raise SystemExit("semana.json no tiene títulos")
    # Los estrenos siempre primero, después los pre-estrenos y el resto (respetando el orden cargado).
    orden = {"estreno": 0, "pre-estreno": 1}
    titulos.sort(key=lambda p: orden.get(p[1], 2))
    enlace = semana.get("enlace") or datos.get("enlace", "https://www.grupocine.com.uy")

    if SALIDA.exists():
        shutil.rmtree(SALIDA)
    (SALIDA / "estreno").mkdir(parents=True)
    generar_gif(titulos, SALIDA / "en-cartel.gif")
    shutil.copy(BASE / "logo-grupocine.png", SALIDA / "logo-grupocine.png")
    (SALIDA / "estreno/index.html").write_text(
        f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={enlace}">'
        f'<title>Grupocine</title><a href="{enlace}">Ir a Grupocine</a>', encoding="utf-8")
    rango = f'{semana.get("desde", "")} al {semana.get("hasta", "")}' if "desde" in semana else ""
    (SALIDA / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Firma Grupocine</title>'
        '<body style="font-family:Arial;padding:24px"><h1>Firma Grupocine</h1>'
        f'<p>Semana vigente: {rango} · actualizado {hoy.isoformat()}</p>'
        '<p><img src="logo-grupocine.png" width="84"></p><p><img src="en-cartel.gif" width="300"></p>',
        encoding="utf-8")
    (SALIDA / ".nojekyll").write_text("")
    print(f"Hoy {hoy} · semana {rango or 'única'}:", ", ".join(f"{t} [{s}]" if s else t for t, s in titulos))


if __name__ == "__main__":
    main()
